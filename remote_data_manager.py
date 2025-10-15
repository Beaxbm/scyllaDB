#!/usr/bin/env python3
"""
Remote Data Manager Client - Access IoT Data from Anywhere

This script allows your data manager to access real-time IoT sensor data
from their home or office using your DuckDNS domain.
"""

import paho.mqtt.client as mqtt
import requests
import json
import time
from datetime import datetime
import sys

class RemoteIoTDataManager:
    def __init__(self, domain_name):
        """
        Initialize remote IoT data access
        
        Args:
            domain_name: Your DuckDNS domain (e.g., "your-iot-hub.duckdns.org")
        """
        self.domain = domain_name
        self.mqtt_host = domain_name
        self.mqtt_port = 1883  # Use 8883 for SSL
        self.api_base_url = f"http://{domain_name}:8001"
        
        self.mqtt_client = None
        
    def test_connection(self):
        """Test if the remote IoT hub is accessible"""
        print(f"🔍 Testing connection to {self.domain}...")
        
        try:
            # Test REST API
            response = requests.get(f"{self.api_base_url}/health", timeout=10)
            if response.status_code == 200:
                health = response.json()
                print(f"✅ REST API: {health['status']}")
                print(f"📊 Services: {health.get('services', {})}")
            else:
                print(f"⚠️  REST API returned status: {response.status_code}")
        except Exception as e:
            print(f"❌ REST API connection failed: {e}")
        
        try:
            # Test MQTT connection
            test_client = mqtt.Client()
            test_client.connect(self.mqtt_host, self.mqtt_port, 10)
            test_client.disconnect()
            print("✅ MQTT broker accessible")
        except Exception as e:
            print(f"❌ MQTT connection failed: {e}")
    
    def get_available_sensors(self):
        """Get list of all available sensors via REST API"""
        try:
            response = requests.get(f"{self.api_base_url}/sensors", timeout=10)
            if response.status_code == 200:
                sensors = response.json()
                print(f"📋 Found {len(sensors)} sensors")
                return sensors
            else:
                print(f"❌ Error fetching sensors: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching sensors: {e}")
            return []
    
    def get_sensor_latest(self, sensor_id):
        """Get latest reading for a specific sensor"""
        try:
            url = f"{self.api_base_url}/sensors/{sensor_id}/latest"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error fetching {sensor_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error fetching {sensor_id}: {e}")
            return None
    
    def start_realtime_monitoring(self):
        """Start real-time MQTT monitoring"""
        print(f"🚀 Starting real-time monitoring from {self.mqtt_host}")
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("✅ Connected to remote IoT MQTT broker")
                print("📡 Subscribing to real-time sensor data...")
                client.subscribe("ha/statestream/+/+/state")
                print("🔄 Receiving real-time data... (Press Ctrl+C to stop)\n")
            else:
                print(f"❌ MQTT connection failed with code: {rc}")
        
        def on_message(client, userdata, msg):
            try:
                # Parse remote sensor data
                topic_parts = msg.topic.split('/')
                if len(topic_parts) >= 4:
                    domain = topic_parts[2]
                    sensor_id = topic_parts[3] 
                    value = msg.payload.decode()
                    
                    # Create data structure for your data manager
                    sensor_data = {
                        "timestamp": datetime.now().isoformat(),
                        "sensor_id": sensor_id,
                        "domain": domain,
                        "value": value,
                        "source": "remote_iot_hub",
                        "mqtt_topic": msg.topic
                    }
                    
                    # Display and process the data
                    self.process_remote_sensor_data(sensor_data)
                    
            except Exception as e:
                print(f"❌ Error processing remote message: {e}")
        
        def on_disconnect(client, userdata, rc):
            print(f"\n🔴 Disconnected from remote IoT hub (code: {rc})")
        
        # Setup MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.on_disconnect = on_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            print("\n⏹️  Stopping remote monitoring...")
            if self.mqtt_client:
                self.mqtt_client.disconnect()
        except Exception as e:
            print(f"❌ Remote MQTT error: {e}")
    
    def process_remote_sensor_data(self, data):
        """
        Process sensor data received from remote IoT hub
        
        YOUR DATA MANAGER INTEGRATION GOES HERE
        """
        
        # Choose emoji based on sensor type
        emoji = "🌡️" if "temperature" in data["sensor_id"] else \
               "💧" if "humidity" in data["sensor_id"] else \
               "🚪" if data["domain"] == "binary_sensor" else \
               "⚡" if "voltage" in data["sensor_id"] or "current" in data["sensor_id"] else \
               "📊"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{emoji} {timestamp} | REMOTE: {data['sensor_id']} = {data['value']}")
        
        # YOUR DATA MANAGER PROCESSING:
        
        # Example 1: Store in database
        # your_database.insert_remote_sensor_data(data)
        
        # Example 2: Send to your API  
        # requests.post("your-company-api/remote-sensors", json=data)
        
        # Example 3: Write to file
        # with open("remote_iot_data.jsonl", "a") as f:
        #     f.write(json.dumps(data) + "\n")
        
        # Example 4: Temperature alerts
        if "temperature" in data["sensor_id"]:
            try:
                temp = float(data["value"])
                if temp > 35.0:
                    print(f"🔥 REMOTE ALERT: High temperature {temp}°C at {data['sensor_id']}")
                    # self.send_temperature_alert(data)
                elif temp < 0.0:
                    print(f"🧊 REMOTE ALERT: Freezing temperature {temp}°C at {data['sensor_id']}")
            except ValueError:
                pass  # Non-numeric temperature value
        
        # Example 5: Door monitoring
        if data["domain"] == "binary_sensor" and "door" in data["sensor_id"]:
            status = "OPEN" if data["value"] in ["on", "true", "1"] else "CLOSED"
            print(f"🚪 REMOTE: Door {data['sensor_id']} is {status}")
            # self.log_door_event(data)

def main():
    print("🌍 Remote IoT Data Manager - DuckDNS Access")
    print("=" * 50)
    
    # Configure your DuckDNS domain here
    domain = "gaugescylladb.duckdns.org"  # Your DuckDNS domain
    print(f"🌍 Connecting to: {domain}")
    
    # Allow override for testing
    custom_domain = input(f"Press Enter to use {domain} or enter different domain: ").strip()
    if custom_domain:
        domain = custom_domain
    
    # Create remote data manager
    remote_manager = RemoteIoTDataManager(domain)
    
    print("\nChoose an option:")
    print("1. Test connection to remote IoT hub")
    print("2. Get list of available sensors")
    print("3. Get latest readings from key sensors")
    print("4. Start real-time monitoring")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        remote_manager.test_connection()
        
    elif choice == "2":
        sensors = remote_manager.get_available_sensors()
        for i, sensor in enumerate(sensors[:10], 1):
            print(f"  {i}. {sensor.get('sensor_id', 'unknown')} ({sensor.get('domain', 'unknown')})")
        
    elif choice == "3":
        print("🔍 Getting latest readings from key sensors...")
        key_sensors = [
            "temperatura_e_umidade_externos_temperature",
            "temperatura_e_umidade_externos_humidity", 
            "temperatura_e_umidade_frigobar_temperature",
            "tomada_20a_voltage"
        ]
        
        for sensor_id in key_sensors:
            data = remote_manager.get_sensor_latest(sensor_id)
            if data:
                print(f"📊 {sensor_id}: {data.get('value_numeric') or data.get('value_text', 'N/A')}")
        
    elif choice == "4":
        remote_manager.start_realtime_monitoring()
        
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()