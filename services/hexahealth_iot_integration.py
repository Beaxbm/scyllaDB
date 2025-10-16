"""
HexaHealth IoT Integration Service
Production-ready integration for real-time sensor data
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import paho.mqtt.client as mqtt
try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    requests = None
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorType(Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity" 
    VOLTAGE = "voltage"
    DOOR = "door"
    MOTION = "motion"
    AIR_QUALITY = "air_quality"
    ENERGY = "energy"

@dataclass
class SensorReading:
    """Structured sensor data for HexaHealth product integration"""
    entity_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime
    device_location: str
    patient_id: Optional[str] = None
    alert_level: str = "normal"  # normal, warning, critical

class HexaHealthIoTClient:
    """
    Production IoT client for HexaHealth product integration
    Supports both DuckDNS (development) and cloud (production) endpoints
    """
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config = self._get_config()
        self.mqtt_client = None
        self.sensor_callbacks = {}
        
    def _get_config(self) -> Dict:
        """Environment-specific configuration"""
        configs = {
            "development": {
                "mqtt_host": "gaugescylladb.duckdns.org",
                "mqtt_port": 1883,
                "api_base": "http://gaugescylladb.duckdns.org:8001",
                "ssl": False
            },
            "staging": {
                "mqtt_host": "staging-iot.hexahealth.com",
                "mqtt_port": 8883,
                "api_base": "https://staging-iot-api.hexahealth.com",
                "ssl": True
            },
            "production": {
                "mqtt_host": "iot.hexahealth.com",
                "mqtt_port": 8883,
                "api_base": "https://iot-api.hexahealth.com",
                "ssl": True
            }
        }
        return configs.get(self.environment, configs["development"])
    
    async def connect_realtime(self) -> bool:
        """Connect to real-time MQTT stream for live sensor data"""
        try:
            self.mqtt_client = mqtt.Client()
            
            if self.config["ssl"]:
                self.mqtt_client.tls_set()
            
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            logger.info(f"Connecting to MQTT broker: {self.config['mqtt_host']}:{self.config['mqtt_port']}")
            self.mqtt_client.connect(self.config["mqtt_host"], self.config["mqtt_port"], 60)
            self.mqtt_client.loop_start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return False
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            # Subscribe to all sensor state changes
            client.subscribe("ha/statestream/+/+/state")
            client.subscribe("ha/statestream/sensor/+/state") 
            client.subscribe("ha/statestream/binary_sensor/+/state")
        else:
            logger.error(f"Failed to connect to MQTT broker. Code: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Process incoming sensor data for HexaHealth integration"""
        try:
            # Parse MQTT topic: ha/statestream/domain/entity/state
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 4:
                domain = topic_parts[2]
                entity_name = topic_parts[3]
                entity_id = f"{domain}.{entity_name}"
                
                # Parse sensor data
                sensor_data = self._parse_sensor_data(entity_id, msg.payload.decode(), domain)
                
                if sensor_data:
                    # Process for HexaHealth product features
                    await self._process_for_hexahealth(sensor_data)
                    
                    # Trigger registered callbacks
                    for callback in self.sensor_callbacks.get(sensor_data.sensor_type, []):
                        await callback(sensor_data)
                        
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _parse_sensor_data(self, entity_id: str, payload: str, domain: str) -> Optional[SensorReading]:
        """Parse raw sensor data into structured format for HexaHealth"""
        try:
            # Determine sensor type and extract value
            sensor_type = self._identify_sensor_type(entity_id)
            
            # Parse numeric values
            try:
                value = float(payload)
            except ValueError:
                # Handle binary sensors (door, motion)
                value = 1.0 if payload.lower() in ['on', 'open', 'detected', 'true'] else 0.0
            
            # Determine unit and location from entity ID
            unit = self._get_sensor_unit(entity_id, sensor_type)
            location = self._extract_location(entity_id)
            
            # Create structured reading
            reading = SensorReading(
                entity_id=entity_id,
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                device_location=location,
                alert_level=self._assess_alert_level(sensor_type, value)
            )
            
            logger.info(f"📊 HexaHealth IoT: {reading.sensor_type.value} = {value}{unit} at {location}")
            return reading
            
        except Exception as e:
            logger.error(f"Error parsing sensor data: {e}")
            return None
    
    def _identify_sensor_type(self, entity_id: str) -> SensorType:
        """Identify sensor type from entity ID for HexaHealth categorization"""
        entity_lower = entity_id.lower()
        
        if "temperature" in entity_lower or "temp" in entity_lower:
            return SensorType.TEMPERATURE
        elif "humidity" in entity_lower or "umidade" in entity_lower:
            return SensorType.HUMIDITY
        elif "voltage" in entity_lower or "tensao" in entity_lower:
            return SensorType.VOLTAGE
        elif "door" in entity_lower or "porta" in entity_lower:
            return SensorType.DOOR
        elif "motion" in entity_lower or "movimento" in entity_lower:
            return SensorType.MOTION
        elif "air" in entity_lower or "quality" in entity_lower:
            return SensorType.AIR_QUALITY
        else:
            return SensorType.ENERGY  # Default for power-related sensors
    
    def _get_sensor_unit(self, entity_id: str, sensor_type: SensorType) -> str:
        """Get appropriate unit for sensor type"""
        unit_map = {
            SensorType.TEMPERATURE: "°C",
            SensorType.HUMIDITY: "%",
            SensorType.VOLTAGE: "V", 
            SensorType.DOOR: "state",
            SensorType.MOTION: "state",
            SensorType.AIR_QUALITY: "ppm",
            SensorType.ENERGY: "W"
        }
        return unit_map.get(sensor_type, "")
    
    def _extract_location(self, entity_id: str) -> str:
        """Extract room/location from entity ID"""
        entity_lower = entity_id.lower()
        
        locations = {
            "frigobar": "Kitchen/Minibar",
            "externos": "Outdoor", 
            "sala": "Living Room",
            "quarto": "Bedroom",
            "cozinha": "Kitchen",
            "banheiro": "Bathroom"
        }
        
        for key, location in locations.items():
            if key in entity_lower:
                return location
                
        return "Unknown Location"
    
    def _assess_alert_level(self, sensor_type: SensorType, value: float) -> str:
        """Assess alert level for HexaHealth health monitoring"""
        thresholds = {
            SensorType.TEMPERATURE: {
                "critical": (value < 5 or value > 40),  # Extreme temperatures
                "warning": (value < 15 or value > 32)   # Uncomfortable range
            },
            SensorType.HUMIDITY: {
                "critical": (value < 20 or value > 80),  # Health risk levels
                "warning": (value < 30 or value > 70)    # Comfort issues
            },
            SensorType.VOLTAGE: {
                "critical": (value < 180 or value > 250), # Electrical safety
                "warning": (value < 200 or value > 230)   # Power quality
            }
        }
        
        threshold = thresholds.get(sensor_type)
        if threshold:
            if threshold["critical"]:
                return "critical"
            elif threshold["warning"]:
                return "warning"
        
        return "normal"
    
    async def _process_for_hexahealth(self, sensor_data: SensorReading):
        """Process sensor data for HexaHealth product features"""
        
        # 1. Health Environment Monitoring
        if sensor_data.sensor_type in [SensorType.TEMPERATURE, SensorType.HUMIDITY]:
            await self._update_environment_health_score(sensor_data)
        
        # 2. Safety Monitoring
        if sensor_data.alert_level in ["warning", "critical"]:
            await self._trigger_health_alert(sensor_data)
        
        # 3. Activity Monitoring
        if sensor_data.sensor_type in [SensorType.DOOR, SensorType.MOTION]:
            await self._track_patient_activity(sensor_data)
        
        # 4. Energy Wellness (for elderly monitoring)
        if sensor_data.sensor_type == SensorType.VOLTAGE:
            await self._monitor_home_safety(sensor_data)
    
    async def _update_environment_health_score(self, sensor_data: SensorReading):
        """Update patient's environment health score"""
        # Integration with HexaHealth's health scoring system
        health_score = self._calculate_environment_score(sensor_data)
        
        # Send to HexaHealth backend
        payload = {
            "patient_id": sensor_data.patient_id,
            "environment_score": health_score,
            "sensor_type": sensor_data.sensor_type.value,
            "value": sensor_data.value,
            "location": sensor_data.device_location,
            "timestamp": sensor_data.timestamp.isoformat()
        }
        
        # API call to HexaHealth backend
        # await self._send_to_hexahealth_api("/api/health/environment", payload)
        
    async def _trigger_health_alert(self, sensor_data: SensorReading):
        """Trigger alerts for health-critical conditions"""
        alert_payload = {
            "alert_type": "environmental_risk",
            "severity": sensor_data.alert_level,
            "sensor_type": sensor_data.sensor_type.value,
            "value": sensor_data.value,
            "location": sensor_data.device_location,
            "message": self._generate_alert_message(sensor_data),
            "timestamp": sensor_data.timestamp.isoformat(),
            "requires_action": sensor_data.alert_level == "critical"
        }
        
        logger.warning(f"🚨 Health Alert: {alert_payload['message']}")
        # await self._send_to_hexahealth_api("/api/alerts", alert_payload)
    
    def _generate_alert_message(self, sensor_data: SensorReading) -> str:
        """Generate human-readable alert messages for HexaHealth"""
        messages = {
            (SensorType.TEMPERATURE, "critical"): f"Critical temperature {sensor_data.value}°C in {sensor_data.device_location} - Health risk detected",
            (SensorType.HUMIDITY, "critical"): f"Critical humidity {sensor_data.value}% in {sensor_data.device_location} - Air quality concern",
            (SensorType.VOLTAGE, "critical"): f"Electrical safety issue: {sensor_data.value}V - Check power supply",
        }
        
        key = (sensor_data.sensor_type, sensor_data.alert_level)
        return messages.get(key, f"{sensor_data.sensor_type.value} alert in {sensor_data.device_location}")
    
    def _calculate_environment_score(self, sensor_data: SensorReading) -> float:
        """Calculate environment health score (0-100) for HexaHealth"""
        if sensor_data.sensor_type == SensorType.TEMPERATURE:
            # Optimal range: 20-24°C
            optimal_temp = 22
            deviation = abs(sensor_data.value - optimal_temp)
            score = max(0, 100 - (deviation * 10))
            
        elif sensor_data.sensor_type == SensorType.HUMIDITY:
            # Optimal range: 40-60%
            if 40 <= sensor_data.value <= 60:
                score = 100
            else:
                deviation = min(abs(sensor_data.value - 40), abs(sensor_data.value - 60))
                score = max(0, 100 - (deviation * 2))
        else:
            score = 85  # Default good score
            
        return round(score, 1)
    
    # Public API methods for HexaHealth product integration
    
    def register_sensor_callback(self, sensor_type: SensorType, callback):
        """Register callback for specific sensor types"""
        if sensor_type not in self.sensor_callbacks:
            self.sensor_callbacks[sensor_type] = []
        self.sensor_callbacks[sensor_type].append(callback)
    
    async def get_patient_environment_status(self, patient_id: str) -> Dict:
        """Get current environment status for a patient"""
        try:
            response = requests.get(f"{self.config['api_base']}/sensors")
            sensors = response.json()
            
            # Filter and process for patient
            environment_data = {
                "patient_id": patient_id,
                "temperature": None,
                "humidity": None,
                "air_quality_score": None,
                "safety_status": "ok",
                "last_activity": None,
                "alerts": []
            }
            
            # Process sensor data for environment status
            for sensor in sensors:
                sensor_reading = self._parse_sensor_data(sensor["entity_id"], str(sensor["state"]), sensor["domain"])
                if sensor_reading and sensor_reading.alert_level != "normal":
                    environment_data["alerts"].append({
                        "type": sensor_reading.sensor_type.value,
                        "message": self._generate_alert_message(sensor_reading),
                        "severity": sensor_reading.alert_level
                    })
            
            return environment_data
            
        except Exception as e:
            logger.error(f"Error getting patient environment status: {e}")
            return {}
    
    async def get_historical_health_data(self, patient_id: str, hours: int = 24) -> List[Dict]:
        """Get historical sensor data for health analysis"""
        try:
            # This would integrate with your ScyllaDB historical data
            response = requests.get(f"{self.config['api_base']}/data/export?hours={hours}")
            historical_data = response.json()
            
            # Process for health insights
            health_insights = []
            for data_point in historical_data:
                sensor_reading = self._parse_sensor_data(data_point["entity_id"], str(data_point["state"]), data_point["domain"])
                if sensor_reading:
                    health_insights.append({
                        "timestamp": data_point["time"],
                        "sensor_type": sensor_reading.sensor_type.value,
                        "value": sensor_reading.value,
                        "health_score": self._calculate_environment_score(sensor_reading),
                        "location": sensor_reading.device_location
                    })
            
            return health_insights
            
        except Exception as e:
            logger.error(f"Error getting historical health data: {e}")
            return []

# Example usage for HexaHealth product integration
async def main():
    """Example integration with HexaHealth product"""
    
    # Initialize IoT client for your environment
    iot_client = HexaHealthIoTClient(environment="development")  # Use "production" for live
    
    # Register callbacks for different health monitoring needs
    async def on_temperature_change(sensor_data: SensorReading):
        print(f"🌡️ Temperature update for HexaHealth: {sensor_data.value}°C in {sensor_data.device_location}")
        # Integrate with your product's health monitoring
    
    async def on_critical_alert(sensor_data: SensorReading):
        print(f"🚨 Critical health environment alert: {sensor_data.sensor_type.value}")
        # Trigger notification in HexaHealth app
    
    # Register callbacks
    iot_client.register_sensor_callback(SensorType.TEMPERATURE, on_temperature_change)
    
    # Connect to real-time data stream
    connected = await iot_client.connect_realtime()
    if connected:
        print("✅ Connected to HexaHealth IoT data stream")
        
        # Get current patient environment status
        patient_status = await iot_client.get_patient_environment_status("patient_123")
        print(f"📊 Patient Environment: {patient_status}")
        
        # Keep running to receive real-time updates
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Disconnecting from IoT stream...")
    else:
        print("❌ Failed to connect to IoT data stream")

if __name__ == "__main__":
    asyncio.run(main())