"""
HexaHealth IoT Integration - Simplified Production Version
Real-time sensor data integration for healthcare products
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HexaHealthIoTClient:
    """
    Simple IoT client for HexaHealth product integration
    Supports real-time sensor data processing for healthcare applications
    """
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config = self._get_config()
        self.mqtt_client = None
        self.sensor_data = {}
        self.health_alerts = []
        
    def _get_config(self) -> Dict:
        """Environment-specific configuration"""
        configs = {
            "development": {
                "mqtt_host": "gaugescylladb.duckdns.org",
                "mqtt_port": 1883,
                "api_base": "http://gaugescylladb.duckdns.org:8001"
            },
            "production": {
                "mqtt_host": "iot.hexahealth.com",
                "mqtt_port": 8883,
                "api_base": "https://iot-api.hexahealth.com"
            }
        }
        return configs.get(self.environment, configs["development"])
    
    def connect_realtime(self) -> bool:
        """Connect to real-time MQTT stream"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_message = self._on_message
            
            logger.info(f"Connecting to: {self.config['mqtt_host']}:{self.config['mqtt_port']}")
            self.mqtt_client.connect(self.config["mqtt_host"], self.config["mqtt_port"], 60)
            self.mqtt_client.loop_start()
            
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            logger.info("✅ Connected to IoT data stream")
            # Subscribe to all sensor data
            client.subscribe("ha/statestream/+/+/state")
        else:
            logger.error(f"❌ Connection failed. Code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Process real-time sensor data for HexaHealth"""
        try:
            # Parse MQTT message
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 4:
                domain = topic_parts[2]
                entity_name = topic_parts[3]
                entity_id = f"{domain}.{entity_name}"
                value = msg.payload.decode()
                
                # Process sensor data
                sensor_info = self._process_sensor_data(entity_id, value, domain)
                
                if sensor_info:
                    # Store latest data
                    self.sensor_data[entity_id] = sensor_info
                    
                    # Check for health alerts
                    self._check_health_alerts(sensor_info)
                    
                    # Log for HexaHealth integration
                    logger.info(f"📊 {sensor_info['type']}: {sensor_info['value']} {sensor_info['unit']} | Location: {sensor_info['location']}")
                    
        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
    
    def _process_sensor_data(self, entity_id: str, value: str, domain: str) -> Optional[Dict]:
        """Process and structure sensor data for HexaHealth"""
        try:
            # Determine sensor type
            sensor_type = self._identify_sensor_type(entity_id)
            
            # Parse value
            try:
                numeric_value = float(value)
            except ValueError:
                # Binary sensors (doors, motion)
                numeric_value = 1.0 if value.lower() in ['on', 'open', 'detected'] else 0.0
            
            # Get metadata
            unit = self._get_unit(entity_id, sensor_type)
            location = self._extract_location(entity_id)
            
            return {
                "entity_id": entity_id,
                "type": sensor_type,
                "value": numeric_value,
                "unit": unit,
                "location": location,
                "timestamp": datetime.now().isoformat(),
                "health_impact": self._assess_health_impact(sensor_type, numeric_value)
            }
            
        except Exception as e:
            logger.error(f"Error processing {entity_id}: {e}")
            return None
    
    def _identify_sensor_type(self, entity_id: str) -> str:
        """Identify sensor type for healthcare categorization"""
        entity_lower = entity_id.lower()
        
        if "temperature" in entity_lower or "temp" in entity_lower:
            return "temperature"
        elif "humidity" in entity_lower or "umidade" in entity_lower:
            return "humidity" 
        elif "voltage" in entity_lower or "tensao" in entity_lower:
            return "electrical"
        elif "door" in entity_lower or "porta" in entity_lower:
            return "access_control"
        elif "motion" in entity_lower or "movimento" in entity_lower:
            return "activity_monitoring"
        else:
            return "environmental"
    
    def _get_unit(self, entity_id: str, sensor_type: str) -> str:
        """Get appropriate unit for display"""
        units = {
            "temperature": "°C",
            "humidity": "%",
            "electrical": "V",
            "access_control": "",
            "activity_monitoring": "",
            "environmental": ""
        }
        return units.get(sensor_type, "")
    
    def _extract_location(self, entity_id: str) -> str:
        """Extract room/location information"""
        entity_lower = entity_id.lower()
        
        locations = {
            "frigobar": "Kitchen/Refrigerator",
            "externos": "Outdoor Environment", 
            "sala": "Living Room",
            "quarto": "Bedroom",
            "cozinha": "Kitchen",
            "banheiro": "Bathroom"
        }
        
        for key, location in locations.items():
            if key in entity_lower:
                return location
                
        return "Indoor Environment"
    
    def _assess_health_impact(self, sensor_type: str, value: float) -> str:
        """Assess health impact for HexaHealth monitoring"""
        
        # Temperature health assessment
        if sensor_type == "temperature":
            if value < 16 or value > 28:
                return "high_impact"  # Risk to health/comfort
            elif value < 18 or value > 26:
                return "moderate_impact"  # Suboptimal conditions
            else:
                return "low_impact"  # Healthy range
        
        # Humidity health assessment  
        elif sensor_type == "humidity":
            if value < 30 or value > 70:
                return "high_impact"  # Risk of respiratory issues
            elif value < 40 or value > 60:
                return "moderate_impact"  # Comfort issues
            else:
                return "low_impact"  # Optimal range
        
        # Electrical safety
        elif sensor_type == "electrical":
            if value < 200 or value > 240:
                return "high_impact"  # Safety concern
            else:
                return "low_impact"
        
        return "low_impact"
    
    def _check_health_alerts(self, sensor_info: Dict):
        """Check for health-related alerts"""
        if sensor_info["health_impact"] == "high_impact":
            alert = {
                "timestamp": sensor_info["timestamp"],
                "type": sensor_info["type"],
                "location": sensor_info["location"],
                "value": sensor_info["value"],
                "message": self._generate_health_message(sensor_info),
                "severity": "high"
            }
            
            self.health_alerts.append(alert)
            logger.warning(f"🚨 Health Alert: {alert['message']}")
    
    def _generate_health_message(self, sensor_info: Dict) -> str:
        """Generate health-focused alert messages"""
        sensor_type = sensor_info["type"]
        value = sensor_info["value"]
        location = sensor_info["location"]
        
        messages = {
            "temperature": f"Temperature {value}°C in {location} may affect health and comfort",
            "humidity": f"Humidity {value}% in {location} may impact air quality and respiratory health",
            "electrical": f"Electrical reading {value}V indicates potential safety concern"
        }
        
        return messages.get(sensor_type, f"Environmental concern detected in {location}")
    
    # Public methods for HexaHealth product integration
    
    def get_current_environment_status(self) -> Dict:
        """Get current environment health status for HexaHealth dashboard"""
        if not self.sensor_data:
            return {"status": "no_data", "message": "No sensor data available"}
        
        environment_summary = {
            "overall_health_score": self._calculate_overall_health_score(),
            "active_alerts": len([a for a in self.health_alerts if a["severity"] == "high"]),
            "sensors_active": len(self.sensor_data),
            "last_update": max([s["timestamp"] for s in self.sensor_data.values()]),
            "locations": list(set([s["location"] for s in self.sensor_data.values()])),
            "temperature_zones": self._get_temperature_summary(),
            "humidity_levels": self._get_humidity_summary(),
            "activity_detected": self._get_activity_summary()
        }
        
        return environment_summary
    
    def get_health_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent health alerts for HexaHealth monitoring"""
        # Filter alerts from last N hours
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent_alerts = [
            alert for alert in self.health_alerts 
            if datetime.fromisoformat(alert["timestamp"]).timestamp() > cutoff_time
        ]
        
        return recent_alerts
    
    def get_sensor_data_for_location(self, location: str) -> Dict:
        """Get all sensor data for a specific location"""
        location_data = {
            sensor_id: data for sensor_id, data in self.sensor_data.items()
            if location.lower() in data["location"].lower()
        }
        
        return location_data
    
    def _calculate_overall_health_score(self) -> float:
        """Calculate overall environment health score (0-100)"""
        if not self.sensor_data:
            return 0.0
        
        total_score = 0
        sensor_count = 0
        
        for sensor_data in self.sensor_data.values():
            if sensor_data["type"] in ["temperature", "humidity"]:
                impact = sensor_data["health_impact"]
                if impact == "low_impact":
                    score = 90
                elif impact == "moderate_impact":
                    score = 70
                else:  # high_impact
                    score = 40
                
                total_score += score
                sensor_count += 1
        
        return round(total_score / sensor_count if sensor_count > 0 else 85.0, 1)
    
    def _get_temperature_summary(self) -> Dict:
        """Get temperature summary for all locations"""
        temp_sensors = {
            sensor_id: data for sensor_id, data in self.sensor_data.items()
            if data["type"] == "temperature"
        }
        
        if not temp_sensors:
            return {}
        
        temps = [data["value"] for data in temp_sensors.values()]
        return {
            "average": round(sum(temps) / len(temps), 1),
            "min": min(temps),
            "max": max(temps),
            "zones": {data["location"]: data["value"] for data in temp_sensors.values()}
        }
    
    def _get_humidity_summary(self) -> Dict:
        """Get humidity summary for health monitoring"""
        humidity_sensors = {
            sensor_id: data for sensor_id, data in self.sensor_data.items()
            if data["type"] == "humidity"
        }
        
        if not humidity_sensors:
            return {}
        
        humidity_values = [data["value"] for data in humidity_sensors.values()]
        return {
            "average": round(sum(humidity_values) / len(humidity_values), 1),
            "zones": {data["location"]: data["value"] for data in humidity_sensors.values()}
        }
    
    def _get_activity_summary(self) -> Dict:
        """Get activity/motion summary for patient monitoring"""
        activity_sensors = {
            sensor_id: data for sensor_id, data in self.sensor_data.items()
            if data["type"] in ["access_control", "activity_monitoring"]
        }
        
        recent_activity = []
        for data in activity_sensors.values():
            if data["value"] > 0:  # Active/detected
                recent_activity.append({
                    "location": data["location"],
                    "time": data["timestamp"],
                    "type": data["type"]
                })
        
        return {
            "active_zones": len(recent_activity),
            "recent_activity": recent_activity[-10:]  # Last 10 activities
        }

# Example usage for HexaHealth product
def main():
    """Example integration with HexaHealth product"""
    
    # Initialize IoT client
    print("🏥 Starting HexaHealth IoT Integration...")
    iot_client = HexaHealthIoTClient(environment="development")
    
    # Connect to real-time data
    if iot_client.connect_realtime():
        print("✅ Connected to real-time IoT data stream")
        print("📊 Monitoring patient environment data...")
        
        try:
            # Monitor for 60 seconds as example
            for i in range(60):
                time.sleep(1)
                
                # Every 10 seconds, show health summary
                if i % 10 == 0 and i > 0:
                    status = iot_client.get_current_environment_status()
                    print(f"\n🏥 Health Status Update:")
                    print(f"   Overall Health Score: {status.get('overall_health_score', 'N/A')}/100")
                    print(f"   Active Sensors: {status.get('sensors_active', 0)}")
                    print(f"   Health Alerts: {status.get('active_alerts', 0)}")
                    
                    # Show temperature zones
                    temp_summary = status.get('temperature_zones', {})
                    if temp_summary:
                        print(f"   Temperature Zones:")
                        for zone, temp in temp_summary.get('zones', {}).items():
                            print(f"     • {zone}: {temp}°C")
                    
                    # Show any health alerts
                    alerts = iot_client.get_health_alerts(hours=1)
                    if alerts:
                        print(f"   Recent Health Alerts:")
                        for alert in alerts[-3:]:  # Show last 3
                            print(f"     ⚠️  {alert['message']}")
        
        except KeyboardInterrupt:
            print("\n👋 Stopping HexaHealth IoT monitoring...")
    else:
        print("❌ Failed to connect to IoT data stream")
        print("💡 Make sure your IoT infrastructure is running:")
        print("   docker-compose up -d")

if __name__ == "__main__":
    main()