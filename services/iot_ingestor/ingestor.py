"""
Unified IoT Ingestor: Home Assistant MQTT Statestream → ScyllaDB

Transforms Home Assistant sensor data into unified ScyllaDB schema:
- Converts entity_id format to sensor_id
- Maps different sensor types (numeric, binary, text) to unified columns
- Handles Home Assistant state changes and unavailable states
- Generates events for significant changes
- Computes real-time aggregates
"""

import asyncio
import json
import logging
import os
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, Union
from uuid import uuid1, UUID
from dataclasses import dataclass
import zoneinfo

import paho.mqtt.client as mqtt
from cassandra.cluster import Cluster
from cassandra.policies import TokenAwarePolicy, DCAwareRoundRobinPolicy
from cassandra.query import PreparedStatement
from cassandra import ConsistencyLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SensorReading:
    """Unified sensor reading structure"""
    sensor_id: str
    domain: str
    timestamp: datetime
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    value_binary: Optional[bool] = None
    unit: Optional[str] = None
    quality: str = 'good'
    attributes: Dict[str, str] = None
    friendly_name: Optional[str] = None
    device_class: Optional[str] = None

class HomeAssistantIngestor:
    def __init__(self):
        # Configuration from environment
        self.mqtt_host = os.getenv('MQTT_HOST', 'mosquitto')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.scylla_hosts = os.getenv('SCYLLA_HOSTS', 'scylla-node1').split(',')
        self.keyspace = os.getenv('SCYLLA_KEYSPACE', 'iot')
        self.tenant = os.getenv('TENANT_ID', 'gauge')
        self.site = os.getenv('SITE_ID', 'recife')
        
        # Timezone configuration
        self.local_timezone = zoneinfo.ZoneInfo('America/Recife')
        
        # State tracking
        self.sensor_cache: Dict[str, Dict] = {}
        self.last_values: Dict[str, Any] = {}
        
        # ScyllaDB setup
        self.cluster = None
        self.session = None
        self.prepared_statements = {}
        
        # MQTT setup
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

    async def initialize(self):
        """Initialize connections"""
        await self._connect_scylla()
        await self._prepare_statements()
        self._connect_mqtt()

    async def _connect_scylla(self):
        """Connect to ScyllaDB cluster"""
        try:
            self.cluster = Cluster(
                contact_points=self.scylla_hosts,
                load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
                protocol_version=4
            )
            self.session = self.cluster.connect(self.keyspace)
            self.session.default_consistency_level = ConsistencyLevel.LOCAL_QUORUM
            logger.info(f"Connected to ScyllaDB: {self.scylla_hosts}")
        except Exception as e:
            logger.error(f"Failed to connect to ScyllaDB: {e}")
            raise

    async def _prepare_statements(self):
        """Prepare CQL statements for better performance"""
        
        # Sensor metadata upsert
        self.prepared_statements['upsert_sensor'] = self.session.prepare("""
            INSERT INTO sensors 
            (tenant, site, sensor_id, domain, device_id, friendly_name, 
             unit_of_measurement, device_class, state_class, last_seen, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        
        # Unified sensor reading insert
        self.prepared_statements['insert_reading'] = self.session.prepare("""
            INSERT INTO sensor_readings
            (tenant, site, day_bucket, sensor_id, ts, ts_uuid,
             value_numeric, value_text, value_binary, domain, unit, quality, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        
        # Event insert
        self.prepared_statements['insert_event'] = self.session.prepare("""
            INSERT INTO sensor_events
            (tenant, site, day_bucket, sensor_id, ts, ts_uuid,
             event_type, old_value, new_value, severity, message, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

    def _connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker: {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            raise

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("MQTT connected successfully")
            # Subscribe to Home Assistant statestream state messages
            client.subscribe("ha/statestream/+/+/state")
            logger.info("Subscribed to ha/statestream/+/+/state")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning(f"MQTT disconnected with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Process incoming MQTT message from Home Assistant statestream"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            # Parse topic: ha/statestream/sensor/sensor_name/state
            topic_parts = topic.split('/')
            if len(topic_parts) != 5 or topic_parts[4] != 'state':
                return  # Skip non-state messages
                
            domain = topic_parts[2]  # 'sensor' or 'binary_sensor'
            sensor_name = topic_parts[3]  # sensor name
            entity_id = f"{domain}.{sensor_name}"
            
            logger.info(f"Processing MQTT message from {topic}: {payload[:100]}...")
            
            # For statestream, the payload is just the state value, not JSON
            # But we need to construct the full message format
            state_data = {
                'state': payload,
                'entity_id': entity_id,
                'domain': domain
            }
            
            # Parse Home Assistant data
            reading = self._parse_ha_statestream(entity_id, state_data)
            if reading:
                self._store_reading(reading)
                
        except Exception as e:
            logger.error(f"Error processing message from {msg.topic}: {e}")

    def _parse_ha_statestream(self, entity_id: str, payload: Dict) -> Optional[SensorReading]:
        """Convert Home Assistant statestream to unified SensorReading"""
        
        # Extract domain and sensor_id from entity_id (e.g., 'sensor.temperature_01')
        if '.' not in entity_id:
            logger.warning(f"Invalid entity_id format: {entity_id}")
            return None
            
        domain, sensor_name = entity_id.split('.', 1)
        
        # Only process configured domains
        if domain not in ['sensor', 'binary_sensor']:
            return None

        state = payload.get('state')
        attributes = payload.get('attributes', {})
        
        # Handle timestamp - convert to local timezone (Recife)
        timestamp_str = payload.get('last_changed')
        if timestamp_str:
            # Parse Home Assistant ISO timestamp (UTC) and convert to local timezone
            utc_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            timestamp = utc_timestamp.astimezone(self.local_timezone)
        else:
            # Use current time in local timezone
            timestamp = datetime.now(self.local_timezone)

        # Determine quality
        quality = 'unavailable' if state == 'unavailable' else 'good'
        
        reading = SensorReading(
            sensor_id=sensor_name,
            domain=domain,
            timestamp=timestamp,
            quality=quality,
            attributes={k: str(v) for k, v in attributes.items()},
            friendly_name=attributes.get('friendly_name'),
            device_class=attributes.get('device_class'),
            unit=attributes.get('unit_of_measurement')
        )

        # Parse value based on domain and state
        if quality == 'unavailable':
            # Keep values as None for unavailable sensors
            pass
        elif domain == 'binary_sensor':
            # Binary sensors: on/off, true/false, open/closed
            if state in ('on', 'true', 'open', '1'):
                reading.value_binary = True
                reading.value_text = state
            elif state in ('off', 'false', 'closed', '0'):
                reading.value_binary = False
                reading.value_text = state
            else:
                reading.value_text = str(state)
        elif domain == 'sensor':
            # Try to parse as numeric first
            try:
                reading.value_numeric = float(state)
            except (ValueError, TypeError):
                # Store as text if not numeric
                reading.value_text = str(state) if state is not None else None

        return reading

    def _store_reading(self, reading: SensorReading):
        """Store sensor reading in ScyllaDB"""
        try:
            # Update sensor metadata
            self._upsert_sensor_metadata(reading)
            
            # Store the reading
            day_bucket = reading.timestamp.date()
            ts_uuid = uuid1()
            
            self.session.execute(
                self.prepared_statements['insert_reading'],
                (
                    self.tenant,
                    self.site,
                    day_bucket,
                    reading.sensor_id,
                    reading.timestamp,
                    ts_uuid,
                    reading.value_numeric,
                    reading.value_text,
                    reading.value_binary,
                    reading.domain,
                    reading.unit,
                    reading.quality,
                    reading.attributes
                )
            )
            
            # Generate events for significant changes
            self._check_for_events(reading, ts_uuid, day_bucket)
            
            logger.debug(f"Stored reading: {reading.sensor_id} = {reading.value_numeric or reading.value_text or reading.value_binary}")
            
        except Exception as e:
            logger.error(f"Failed to store reading for {reading.sensor_id}: {e}")

    def _upsert_sensor_metadata(self, reading: SensorReading):
        """Update sensor metadata"""
        try:
            self.session.execute(
                self.prepared_statements['upsert_sensor'],
                (
                    self.tenant,
                    self.site,
                    reading.sensor_id,
                    reading.domain,
                    None,  # device_id - not available in statestream
                    reading.friendly_name,
                    reading.unit,
                    reading.device_class,
                    reading.attributes.get('state_class') if reading.attributes else None,
                    reading.timestamp,
                    reading.attributes
                )
            )
        except Exception as e:
            logger.error(f"Failed to upsert sensor metadata for {reading.sensor_id}: {e}")

    def _check_for_events(self, reading: SensorReading, ts_uuid: UUID, day_bucket: date):
        """Generate events for significant state changes"""
        sensor_key = reading.sensor_id
        current_value = reading.value_numeric or reading.value_text or reading.value_binary
        
        if sensor_key in self.last_values:
            old_value = self.last_values[sensor_key]
            
            # Check for state changes
            if old_value != current_value:
                event_type = 'state_change'
                severity = 'info'
                
                # Special handling for binary sensors and availability
                if reading.domain == 'binary_sensor':
                    event_type = 'binary_change'
                    severity = 'warning' if reading.value_binary else 'info'
                elif reading.quality == 'unavailable':
                    event_type = 'offline'
                    severity = 'warning'
                elif self.last_values.get(f"{sensor_key}_quality") == 'unavailable':
                    event_type = 'online'
                    severity = 'info'
                
                try:
                    self.session.execute(
                        self.prepared_statements['insert_event'],
                        (
                            self.tenant,
                            self.site,
                            day_bucket,
                            reading.sensor_id,
                            reading.timestamp,
                            ts_uuid,
                            event_type,
                            str(old_value) if old_value is not None else None,
                            str(current_value) if current_value is not None else None,
                            severity,
                            f"Sensor {reading.friendly_name or reading.sensor_id} changed from {old_value} to {current_value}",
                            {'domain': reading.domain, 'unit': reading.unit or ''}
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to store event for {reading.sensor_id}: {e}")
        
        # Update cache
        self.last_values[sensor_key] = current_value
        self.last_values[f"{sensor_key}_quality"] = reading.quality

    def run(self):
        """Main execution loop"""
        logger.info("Starting Home Assistant IoT Ingestor")
        
        # Initialize connections
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.initialize())
        
        try:
            # Keep the main thread alive
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down ingestor")
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            if self.cluster:
                self.cluster.shutdown()

if __name__ == "__main__":
    ingestor = HomeAssistantIngestor()
    ingestor.run()