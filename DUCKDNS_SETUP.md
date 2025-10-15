# Quick Setup Guide for gaugescylladb.duckdns.org

## 🌍 Your IoT Hub Domain Setup

**Your Domain**: `gaugescylladb.duckdns.org`

## Step 1: Router Configuration

Configure port forwarding on your router to expose these services:

```
External Port → Internal Port → Service
1883         → 1883         → MQTT (Real-time sensor data)
8883         → 8883         → MQTT SSL (Secure)  
8001         → 8001         → REST API (Historical data)
8123         → 8123         → Home Assistant UI (Optional)
```

**Router Settings Example:**
- **Protocol**: TCP
- **External Port**: 1883
- **Internal IP**: [Your computer's local IP, e.g., 192.168.1.100]
- **Internal Port**: 1883
- **Description**: IoT MQTT Broker

## Step 2: Update DuckDNS IP

Your DuckDNS domain needs to point to your public IP. Create this script:

```bash
#!/bin/bash
# Save as update_duckdns.sh
DOMAIN="gaugescylladb"
TOKEN="your-duckdns-token"  # Get from duckdns.org account

curl "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip="
echo "DuckDNS updated for gaugescylladb.duckdns.org"
```

Run this script periodically or set up a cron job:
```bash
# Add to crontab (crontab -e)
*/5 * * * * /path/to/update_duckdns.sh
```

## Step 3: Test Local Access First

Before setting up remote access, verify everything works locally:

```bash
# Test MQTT
docker exec mosquitto mosquitto_sub -h localhost -t "ha/statestream/#" -C 5

# Test API
curl http://localhost:8001/health
```

## Step 4: Test Remote Access

Once router is configured and DuckDNS is updated:

```bash
# Test from outside your network (use mobile hotspot or ask someone else to test)
curl http://gaugescylladb.duckdns.org:8001/health

# Test MQTT (if you have mosquitto client installed externally)
mosquitto_sub -h gaugescylladb.duckdns.org -p 1883 -t "ha/statestream/#" -C 3
```

## Step 5: Data Manager Remote Connection

**For your data manager team**, provide these connection details:

### MQTT Real-time Access
```json
{
  "host": "gaugescylladb.duckdns.org",
  "port": 1883,
  "topics": ["ha/statestream/+/+/state"],
  "protocol": "MQTT v3.1.1",
  "authentication": "none"
}
```

### REST API Access  
```json
{
  "base_url": "http://gaugescylladb.duckdns.org:8001",
  "endpoints": {
    "health": "/health",
    "sensors": "/sensors",
    "latest": "/sensors/{sensor_id}/latest", 
    "history": "/sensors/{sensor_id}/history?hours=24"
  }
}
```

### Python Code Example
```python
import paho.mqtt.client as mqtt

# Connect to your IoT hub from anywhere
def connect_to_gauge_iot():
    client = mqtt.Client()
    
    def on_message(client, userdata, msg):
        # Real-time sensor data from gaugescylladb.duckdns.org
        topic_parts = msg.topic.split('/')
        sensor_data = {
            "sensor_id": topic_parts[3],
            "value": msg.payload.decode(),
            "timestamp": datetime.now().isoformat()
        }
        print(f"📊 Remote sensor: {sensor_data}")
    
    client.on_message = on_message
    client.connect("gaugescylladb.duckdns.org", 1883, 60)
    client.subscribe("ha/statestream/+/+/state") 
    client.loop_forever()
```

## Step 6: Security Recommendations

For production use, consider:

1. **MQTT Authentication**:
```bash
# Add password protection
docker exec mosquitto mosquitto_passwd -c /mosquitto/config/passwd datamanager
```

2. **SSL/TLS** (Port 8883):
```python
import ssl
client.tls_set_context(ssl.create_default_context())
client.connect("gaugescylladb.duckdns.org", 8883, 60)
```

3. **API Key Authentication**:
```python
headers = {"Authorization": "Bearer your-api-key"}
requests.get("http://gaugescylladb.duckdns.org:8001/sensors", headers=headers)
```

## Step 7: Monitoring and Troubleshooting

**Check if services are accessible:**
```bash
# From external network
nmap -p 1883,8001,8123 gaugescylladb.duckdns.org

# Check DuckDNS resolution
nslookup gaugescylladb.duckdns.org
```

**Common Issues:**
- Router firewall blocking ports
- DuckDNS not updated with current IP
- ISP blocking certain ports
- Docker containers not running

## 🎯 Quick Test Commands

**For your data manager to test remote access:**

```bash
# 1. Test connection
telnet gaugescylladb.duckdns.org 1883

# 2. Test API
curl -i http://gaugescylladb.duckdns.org:8001/health

# 3. Run remote data manager
python3 remote_data_manager.py
```

## 📊 What Your Data Manager Will Receive

Real-time data from anywhere in the world:

- 🌡️ **Temperature**: `temperatura_e_umidade_externos_temperature` = 29.3°C
- 💧 **Humidity**: `temperatura_e_umidade_externos_humidity` = 57.8%
- 🧊 **Fridge Temp**: `temperatura_e_umidade_frigobar_temperature` = 7.2°C
- ⚡ **Voltage**: `tomada_20a_voltage` = 219.2V
- 🚪 **Door Status**: `frigobar_door` = off

All accessible via `gaugescylladb.duckdns.org`! 🌍