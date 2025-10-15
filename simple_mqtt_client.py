#!/usr/bin/env python3
"""
Simple MQTT Real-time Data Access - Working Version

This script connects to the MQTT broker and displays real-time sensor data.
"""

import json
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
    print("✅ MQTT library loaded successfully")
except ImportError:
    print("❌ paho-mqtt not installed. Installing...")
    import subprocess
    subprocess.check_call(["pip3", "install", "paho-mqtt==1.6.1"])
    import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        print("📡 Subscribing to sensor data...")
        
        # Subscribe to sensor state updates
        client.subscribe("ha/statestream/sensor/+/state")
        client.subscribe("ha/statestream/binary_sensor/+/state")
        
        print("🔄 Listening for real-time data... (Press Ctrl+C to stop)")
        print("-" * 60)
    else:
        print(f"❌ Failed to connect to MQTT broker (code: {rc})")

def on_message(client, userdata, msg):
    try:
        # Parse topic: ha/statestream/sensor/sensor_name/state
        topic = msg.topic
        topic_parts = topic.split('/')
        
        if len(topic_parts) >= 4:
            domain = topic_parts[2]      # sensor or binary_sensor
            sensor_name = topic_parts[3] # sensor identifier
            value = msg.payload.decode() # sensor value
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Choose emoji based on sensor type
            emoji = "🌡️" if "temperature" in sensor_name else \
                   "💧" if "humidity" in sensor_name else \
                   "🚪" if domain == "binary_sensor" else \
                   "📊"
            
            # Display real-time data
            print(f"{emoji} {timestamp} | {sensor_name} = {value}")
            
            # Create JSON structure for your data manager
            sensor_data = {
                "timestamp": datetime.now().isoformat(),
                "sensor_id": sensor_name,
                "domain": domain,
                "value": value,
                "mqtt_topic": topic
            }
            
            # HERE IS WHERE YOU INTEGRATE WITH YOUR DATA MANAGER:
            # your_data_manager.process(sensor_data)
            # database.insert(sensor_data)
            # api.send(sensor_data)
            
    except Exception as e:
        print(f"❌ Error processing message: {e}")

def main():
    print("🏠 Gauge IoT - Simple MQTT Real-time Access")
    print("=" * 50)
    
    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("🔌 Connecting to MQTT broker...")
        client.connect("localhost", 1883, 60)
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n⏹️  Stopping...")
        client.disconnect()
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("\n💡 Make sure Docker containers are running:")
        print("   docker ps")

if __name__ == "__main__":
    main()