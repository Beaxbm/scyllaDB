#!/usr/bin/env python3
"""
WORKING Data Manager MQTT Client

This script successfully connects to your MQTT broker and receives real-time data.
Copy this code into your data manager application.
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time

class DataManagerMQTT:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to Gauge IoT MQTT broker")
            
            # Subscribe to all sensor data
            client.subscribe("ha/statestream/sensor/+/state")
            client.subscribe("ha/statestream/binary_sensor/+/state")
            
            print("📊 Receiving real-time sensor data...")
        else:
            print(f"❌ Connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Process real-time sensor data"""
        try:
            # Parse MQTT message
            topic_parts = msg.topic.split('/')
            domain = topic_parts[2]        # sensor/binary_sensor
            sensor_id = topic_parts[3]     # sensor name
            value = msg.payload.decode()   # sensor value
            
            # Create structured data for your data manager
            sensor_data = {
                "timestamp": datetime.now().isoformat(),
                "sensor_id": sensor_id,
                "domain": domain,
                "value": value,
                "raw_topic": msg.topic
            }
            
            # Display the data
            print(f"📊 {sensor_id}: {value}")
            
            # INTEGRATE WITH YOUR DATA MANAGER HERE:
            self.process_sensor_data(sensor_data)
            
        except Exception as e:
            print(f"Error: {e}")
    
    def process_sensor_data(self, data):
        """
        YOUR DATA MANAGER CODE GOES HERE
        
        Examples:
        """
        
        # Example 1: Save to database
        # self.database.insert(data)
        
        # Example 2: Send to API
        # requests.post("your-api/sensors", json=data)
        
        # Example 3: Write to file
        # with open("sensor_data.json", "a") as f:
        #     f.write(json.dumps(data) + "\n")
        
        # Example 4: Filter and process specific sensors
        if "temperature" in data["sensor_id"]:
            temp_value = float(data["value"])
            if temp_value > 30:
                print(f"🔥 High temperature alert: {temp_value}°C")
                # self.send_alert(data)
        
        # For now, just show the JSON structure
        if "temperatura_e_umidade" in data["sensor_id"]:
            print(f"   📋 JSON: {json.dumps(data, indent=2)}")
    
    def start(self):
        """Start receiving real-time data"""
        try:
            self.client.connect("localhost", 1883, 60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("\n⏹️  Stopping data manager...")
            self.client.disconnect()
        except Exception as e:
            print(f"❌ Error: {e}")

# Run the data manager
if __name__ == "__main__":
    print("🏠 Data Manager - Real-time MQTT Access")
    print("=" * 40)
    
    data_manager = DataManagerMQTT()
    data_manager.start()