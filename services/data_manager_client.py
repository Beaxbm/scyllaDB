#!/usr/bin/env python3
"""
Data Manager Client Examples - Real-time IoT Data Access

Multiple ways to access real-time sensor data for your data management system.
"""

import asyncio
import websockets
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8001"
WEBSOCKET_URL = "ws://localhost:8001/ws/realtime"
MQTT_HOST = "localhost"
MQTT_PORT = 1883

class DataManagerClient:
    """Main client class for accessing real-time IoT data"""
    
    def __init__(self):
        self.mqtt_client = None
        self.websocket = None
        
    # Option 1: Direct MQTT Access (Fastest, Raw Data)
    def setup_mqtt_client(self, on_sensor_data_callback):
        """Connect directly to MQTT broker for real-time data"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("✅ Connected to MQTT broker")
                client.subscribe("ha/statestream/+/+/state")
            else:
                print(f"❌ MQTT connection failed: {rc}")
        
        def on_message(client, userdata, msg):
            try:
                # Parse topic: ha/statestream/sensor/sensor_name/state
                topic_parts = msg.topic.split('/')
                if len(topic_parts) >= 5:
                    domain = topic_parts[2]
                    sensor_name = topic_parts[3]
                    value = msg.payload.decode()
                    
                    sensor_data = {
                        "timestamp": datetime.now().isoformat(),
                        "sensor_id": sensor_name,
                        "domain": domain,
                        "value": value,
                        "topic": msg.topic
                    }
                    
                    # Call your callback function
                    on_sensor_data_callback(sensor_data)
                    
            except Exception as e:
                print(f"Error processing MQTT message: {e}")
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        
        try:
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT connection error: {e}")
            return False
    
    # Option 2: WebSocket API (Structured, with DB correlation)
    async def stream_websocket_data(self, on_sensor_data_callback):
        """Connect to WebSocket API for structured real-time data"""
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                print("✅ Connected to WebSocket API")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "sensor_update":
                            # Call your callback function
                            on_sensor_data_callback(data)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing WebSocket message: {e}")
                        
        except Exception as e:
            print(f"WebSocket connection error: {e}")
    
    # Option 3: REST API Polling (For historical and batch data)
    def get_all_sensors(self):
        """Get list of all available sensors"""
        try:
            response = requests.get(f"{API_BASE_URL}/sensors")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request error: {e}")
            return []
    
    def get_sensor_latest(self, sensor_id):
        """Get latest reading for specific sensor"""
        try:
            response = requests.get(f"{API_BASE_URL}/sensors/{sensor_id}/latest")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request error: {e}")
            return None
    
    def get_sensor_history(self, sensor_id, hours=24, limit=1000):
        """Get historical data for sensor"""
        try:
            params = {"hours": hours, "limit": limit}
            response = requests.get(f"{API_BASE_URL}/sensors/{sensor_id}/history", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request error: {e}")
            return []

# Example Usage Patterns for Data Managers

def example_1_mqtt_realtime():
    """Example 1: Direct MQTT access for fastest real-time data"""
    print("🚀 Example 1: Direct MQTT Real-time Access")
    
    client = DataManagerClient()
    
    def handle_sensor_data(sensor_data):
        # Your data processing logic here
        print(f"📊 New sensor data: {sensor_data['sensor_id']} = {sensor_data['value']}")
        
        # Example: Store in your database
        # your_database.insert(sensor_data)
        
        # Example: Trigger alerts
        # if sensor_data['sensor_id'] == 'temperatura_e_umidade_externos_temperature':
        #     if float(sensor_data['value']) > 35.0:
        #         send_temperature_alert(sensor_data)
    
    if client.setup_mqtt_client(handle_sensor_data):
        print("🔄 Listening for real-time sensor data... (Press Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopping MQTT client")
            client.mqtt_client.loop_stop()
            client.mqtt_client.disconnect()

async def example_2_websocket_structured():
    """Example 2: WebSocket API for structured real-time data"""
    print("🚀 Example 2: WebSocket API Structured Data")
    
    client = DataManagerClient()
    
    def handle_sensor_data(message_data):
        if message_data.get("type") == "sensor_update":
            sensor_info = message_data["data"]
            timestamp = message_data["timestamp"]
            
            print(f"📊 {timestamp}: {sensor_info['sensor_id']} = {sensor_info['value']}")
            
            # Your data processing logic here
            # structured_data = {
            #     "timestamp": timestamp,
            #     "sensor_id": sensor_info['sensor_id'],
            #     "domain": sensor_info['domain'],
            #     "value": sensor_info['value']
            # }
            # your_database.insert(structured_data)
    
    try:
        await client.stream_websocket_data(handle_sensor_data)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping WebSocket client")

def example_3_rest_api_batch():
    """Example 3: REST API for historical and batch processing"""
    print("🚀 Example 3: REST API Batch Processing")
    
    client = DataManagerClient()
    
    # Get all available sensors
    sensors = client.get_all_sensors()
    print(f"📋 Found {len(sensors)} sensors")
    
    # Process each sensor
    for sensor in sensors[:5]:  # Limit to first 5 for demo
        sensor_id = sensor['sensor_id']
        domain = sensor['domain']
        
        print(f"\n🔍 Processing {sensor_id} ({domain})")
        
        # Get latest reading
        latest = client.get_sensor_latest(sensor_id)
        if latest:
            print(f"  📊 Latest: {latest['value_numeric'] or latest['value_text']} at {latest['timestamp']}")
        
        # Get historical data (last 1 hour)
        history = client.get_sensor_history(sensor_id, hours=1, limit=10)
        print(f"  📈 History: {len(history)} readings in last hour")
        
        # Your batch processing logic here
        # for reading in history:
        #     process_historical_data(reading)

def example_4_hybrid_approach():
    """Example 4: Hybrid approach - real-time + historical correlation"""
    print("🚀 Example 4: Hybrid Real-time + Historical Analysis")
    
    client = DataManagerClient()
    
    def handle_realtime_data(sensor_data):
        sensor_id = sensor_data['sensor_id']
        current_value = sensor_data['value']
        
        print(f"📊 Real-time: {sensor_id} = {current_value}")
        
        # Get historical context for analysis
        history = client.get_sensor_history(sensor_id, hours=1, limit=20)
        if history:
            values = [r['value_numeric'] for r in history if r['value_numeric'] is not None]
            if values:
                avg = sum(values) / len(values)
                print(f"  📈 1-hour average: {avg:.2f}")
                
                # Example: Detect anomalies
                try:
                    current_num = float(current_value)
                    if abs(current_num - avg) > (avg * 0.2):  # 20% deviation
                        print(f"  ⚠️  ANOMALY DETECTED: {current_num} vs avg {avg:.2f}")
                except ValueError:
                    pass
    
    # Start real-time monitoring with historical context
    if client.setup_mqtt_client(handle_realtime_data):
        print("🔄 Hybrid monitoring active... (Press Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopping hybrid client")
            client.mqtt_client.loop_stop()
            client.mqtt_client.disconnect()

if __name__ == "__main__":
    print("🏠 Gauge IoT Data Manager Client Examples")
    print("==========================================")
    
    # Check API availability
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ API Health: {health['status']}")
            print(f"📊 Active WebSocket clients: {health['services']['websocket_clients']}")
        else:
            print("❌ API not available")
            exit(1)
    except:
        print("❌ API not reachable - make sure containers are running")
        exit(1)
    
    print("\nChoose an example:")
    print("1. Direct MQTT real-time access")
    print("2. WebSocket structured data")
    print("3. REST API batch processing")
    print("4. Hybrid real-time + historical")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        example_1_mqtt_realtime()
    elif choice == "2":
        asyncio.run(example_2_websocket_structured())
    elif choice == "3":
        example_3_rest_api_batch()
    elif choice == "4":
        example_4_hybrid_approach()
    else:
        print("Invalid choice")