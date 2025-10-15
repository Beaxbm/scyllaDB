#!/usr/bin/env python3
"""
Direct MQTT Access - Real-time Sensor Data

Simple script to access live IoT sensor data via MQTT.
Run this to start receiving real-time sensor updates in JSON format.
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
import sys

# MQTT Configuration
MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "ha/statestream/+/+/state",           # All sensor state updates
    "ha/statestream/+/+/last_updated",    # Timestamp updates
]

class RealtimeDataAccess:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT broker!")
            print("📡 Subscribing to real-time sensor data...")
            
            # Subscribe to all sensor state updates
            client.subscribe("ha/statestream/+/+/state")
            print("🔄 Listening for sensor data... (Press Ctrl+C to stop)\n")
        else:
            print(f"❌ Connection failed with code {rc}")
            
    def on_disconnect(self, client, userdata, rc):
        print(f"\n🔴 Disconnected from MQTT broker (code: {rc})")
        
    def on_message(self, client, userdata, msg):
        """Process incoming sensor data"""
        try:
            # Parse MQTT topic: ha/statestream/domain/sensor_name/state
            topic_parts = msg.topic.split('/')
            
            if len(topic_parts) >= 5 and topic_parts[4] == 'state':
                domain = topic_parts[2]        # sensor, binary_sensor, etc.
                sensor_name = topic_parts[3]   # actual sensor identifier
                value = msg.payload.decode()    # sensor value
                
                # Create structured JSON data for your data manager
                sensor_data = {
                    "timestamp": datetime.now().isoformat(),
                    "sensor_id": sensor_name,
                    "domain": domain,
                    "value": value,
                    "mqtt_topic": msg.topic,
                    "local_time": datetime.now().strftime("%H:%M:%S")
                }
                
                # Display the data
                self.display_sensor_data(sensor_data)
                
                # THIS IS WHERE YOU INTEGRATE WITH YOUR DATA MANAGER
                # self.send_to_data_manager(sensor_data)
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            
    def display_sensor_data(self, data):
        """Display sensor data in a readable format"""
        sensor_type = "🌡️" if "temperature" in data["sensor_id"] else \
                     "💧" if "humidity" in data["sensor_id"] else \
                     "🚪" if data["domain"] == "binary_sensor" else \
                     "📊"
        
        print(f"{sensor_type} {data['local_time']} | {data['sensor_id']} = {data['value']}")
        
        # Uncomment to see full JSON structure
        # print(f"   📋 Full JSON: {json.dumps(data, indent=2)}\n")
        
    def send_to_data_manager(self, sensor_data):
        """
        YOUR DATA MANAGER INTEGRATION GOES HERE
        
        Examples:
        - Send to database: database.insert(sensor_data)
        - Send to API: requests.post("your-api/sensors", json=sensor_data)
        - Write to file: json.dump(sensor_data, file)
        - Send to Kafka: producer.send("sensors", sensor_data)
        """
        pass
        
    def start_listening(self):
        """Start the MQTT client and listen for data"""
        try:
            print("🚀 Starting Real-time Data Access...")
            print(f"🔌 Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
            
            self.client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            print("\n⏹️  Stopping real-time data access...")
            self.client.disconnect()
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

def main():
    print("🏠 Gauge IoT - Direct MQTT Real-time Access")
    print("=" * 50)
    
    # Create and start the real-time data access
    mqtt_client = RealtimeDataAccess()
    mqtt_client.start_listening()

if __name__ == "__main__":
    main()