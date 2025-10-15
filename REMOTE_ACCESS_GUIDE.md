# Remote Access Setup Guide - DuckDNS + IoT Data

## 🌐 DuckDNS Setup for Remote Access

Your data manager can access real-time IoT data from anywhere using DuckDNS domain.

### Step 1: Configure DuckDNS

1. **Get DuckDNS domain**: 
   - Go to https://www.duckdns.org
   - Create account and get domain like: `your-iot-hub.duckdns.org`
   - Get your DuckDNS token

2. **Router Port Forwarding**:
   ```
   External Port → Internal Port → Service
   1883         → 1883         → MQTT (Real-time data)
   8883         → 8883         → MQTT SSL (Secure)  
   8001         → 8001         → REST API
   8123         → 8123         → Home Assistant UI
   ```

3. **Update DuckDNS IP** (script to run on your home server):
   ```bash
   #!/bin/bash
   # Save as update_duckdns.sh
   DOMAIN="your-iot-hub"  # Replace with your domain
   TOKEN="your-token"     # Replace with your DuckDNS token
   
   curl "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip="
   ```

### Step 2: Data Manager Remote Connection

Your data manager can now connect from anywhere:

**MQTT Connection (Real-time):**
```python
import paho.mqtt.client as mqtt

# Remote connection to your IoT hub
REMOTE_HOST = "your-iot-hub.duckdns.org"  # Your DuckDNS domain
MQTT_PORT = 1883  # or 8883 for SSL

def connect_remote_iot():
    client = mqtt.Client()
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to remote IoT hub: {REMOTE_HOST}")
            client.subscribe("ha/statestream/+/+/state")
        else:
            print(f"❌ Connection failed: {rc}")
    
    def on_message(client, userdata, msg):
        # Process real-time sensor data from anywhere
        topic_parts = msg.topic.split('/')
        sensor_data = {
            "timestamp": datetime.now().isoformat(),
            "sensor_id": topic_parts[3],
            "domain": topic_parts[2],
            "value": msg.payload.decode(),
            "source": "remote_iot_hub"
        }
        
        # Your data manager processes remote data
        your_data_manager.process_remote_sensor(sensor_data)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to your remote IoT hub
    client.connect(REMOTE_HOST, MQTT_PORT, 60)
    client.loop_forever()
```

**REST API Access (Historical data):**
```python
import requests

API_BASE = "http://your-iot-hub.duckdns.org:8001"

# Access from anywhere
def get_remote_sensor_data():
    # Health check
    health = requests.get(f"{API_BASE}/health").json()
    
    # Get all sensors
    sensors = requests.get(f"{API_BASE}/sensors").json()
    
    # Get latest temperature
    temp = requests.get(f"{API_BASE}/sensors/temperatura_e_umidade_externos_temperature/latest").json()
    
    return {
        "api_status": health["status"],
        "sensor_count": len(sensors),
        "latest_temperature": temp
    }
```

### Step 3: Security Considerations

For production use, add security:

**Option A: MQTT with Username/Password**
```yaml
# mosquitto/config/mosquitto.conf
allow_anonymous false
password_file /mosquitto/config/passwd

# Add users:
# docker exec mosquitto mosquitto_passwd -c /mosquitto/config/passwd datamanager
```

**Option B: SSL/TLS Encryption**
```python
import ssl

client = mqtt.Client()
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
client.tls_set_context(context)
client.connect("your-iot-hub.duckdns.org", 8883, 60)  # SSL port
```

**Option C: API Key Authentication**
```python
headers = {"Authorization": "Bearer your-api-key"}
response = requests.get(f"{API_BASE}/sensors", headers=headers)
```

### Step 4: Connection Details for Remote Access

**For Your Data Manager Team:**
```json
{
  "remote_access": {
    "mqtt": {
      "host": "your-iot-hub.duckdns.org",
      "port": 1883,
      "topics": ["ha/statestream/+/+/state"],
      "protocol": "MQTT v3.1.1"
    },
    "rest_api": {
      "base_url": "http://your-iot-hub.duckdns.org:8001",
      "endpoints": {
        "health": "/health",
        "sensors": "/sensors", 
        "latest": "/sensors/{sensor_id}/latest",
        "history": "/sensors/{sensor_id}/history"
      }
    },
    "web_ui": "http://your-iot-hub.duckdns.org:8123"
  }
}
```

### Step 5: Firewall Configuration

**Allow these ports on your home router:**
```bash
# MQTT Real-time data
1883/tcp  # Plain MQTT
8883/tcp  # Secure MQTT

# REST API
8001/tcp  # ScyllaDB API

# Optional: Home Assistant UI  
8123/tcp  # Web interface
```

## 🌟 Benefits for Remote Data Manager

1. **Real-time Access**: MQTT stream from anywhere
2. **Historical Data**: REST API for batch processing  
3. **Always Online**: DuckDNS keeps domain updated
4. **Secure Options**: SSL, authentication available
5. **No VPN Required**: Direct internet access

## 🚀 Quick Test from Remote Location

Your data manager can test with:

```bash
# Test MQTT connection
mosquitto_sub -h your-iot-hub.duckdns.org -p 1883 -t "ha/statestream/#" -v

# Test REST API
curl http://your-iot-hub.duckdns.org:8001/health
```

## 📊 Live Data Available Remotely

The same real-time data you have locally:
- 🌡️ **Temperature sensors**: External, fridge, cellar
- 💧 **Humidity sensors**: Multiple locations  
- 🚪 **Door/contact sensors**: Entry doors, fridge
- ⚡ **Power monitoring**: Voltage, current, power
- 🔋 **Battery levels**: Device status

Your data manager can access all this from their home office, anywhere in the world! 🌍