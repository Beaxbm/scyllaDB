# Gauge IoT Infrastructure - Complete Data Pipeline

Complete IoT data infrastructure with Home Assistant, MQTT, and ScyllaDB for high-performance sensor data management and real-time streaming for the Gauge Monoproject.

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
./test-setup.sh
```

### Option 2: Manual Setup

**Core Infrastructure (Home Assistant + MQTT):**
```bash
docker-compose up -d
```

**ScyllaDB Infrastructure (runs alongside):**
```bash
docker-compose -f docker-compose-scylla.yml up -d
```

## 📊 Access Points

- **Home Assistant UI**: http://localhost:8123
- **ScyllaDB API**: http://localhost:8001
- **ScyllaDB Metrics**: http://localhost:19042/metrics
- **MQTT Broker**: localhost:1883 (plain) / localhost:8883 (TLS)

## 🔧 Architecture

```
Home Assistant → MQTT Statestream → ScyllaDB Ingestor → ScyllaDB → REST API
                     ↓
              Real-time MQTT Stream for Main Gauge Project
```

**Core Services:**
- `docker-compose.yml`: Home Assistant + MQTT broker
- `docker-compose-scylla.yml`: ScyllaDB + API + Ingestor

**Key Features:**
- ⚡ **100x faster** queries than traditional databases
- 📈 **Linear scaling** - add nodes for more performance
- 🔄 **Unified schema** - all sensor types in one table
- ⏰ **Timezone-aware** - America/Recife (UTC-3) timestamps
- 🎯 **Time-series optimized** - built for IoT workloads

## 📡 Available Sensor Data

Live MQTT streams available at:
- 🌡️ External Temperature: `ha/statestream/sensor/temperatura_e_umidade_externos_temperature/state`
- 💧 External Humidity: `ha/statestream/sensor/temperatura_e_umidade_externos_humidity/state`
- 🧊 Fridge Temperature: `ha/statestream/sensor/temperatura_e_umidade_frigobar_temperature/state`
- 💧 Fridge Humidity: `ha/statestream/sensor/temperatura_e_umidade_frigobar_humidity/state`
- ☀️ Light Sensors: `ha/statestream/sensor/*_illuminance/state`

## 🔌 Integration Options

### Option 1: Real-time MQTT (for Main Gauge Project)
```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    topic = msg.topic
    value = msg.payload.decode()
    print(f"Sensor update: {topic} = {value}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("ha/statestream/sensor/+/state")
client.loop_forever()
```

### Option 2: REST API (for Data Managers)
```python
import requests

# Get all temperature sensors
sensors = requests.get("http://localhost:8001/sensors/domain/sensor").json()
temps = [s for s in sensors if s.get('unit') == '°C']

# Get recent historical data
events = requests.get("http://localhost:8001/sensors/temperatura_e_umidade_externos_temperature/latest").json()
```

## � API Examples

```bash
# Health check
curl http://localhost:8001/health

# List all sensors
curl http://localhost:8001/sensors

# Get sensor data by type
curl http://localhost:8001/sensors/domain/sensor
curl http://localhost:8001/sensors/domain/binary_sensor

# Get historical data
curl "http://localhost:8001/sensors/temperature_01/history?hours=24"

# Export data
curl "http://localhost:8001/data/export?hours=24"
```

## � Monitoring

```bash
# Container status
docker ps

# Logs
docker-compose logs -f homeassistant
docker-compose -f docker-compose-scylla.yml logs -f scylla-ingestor

# MQTT traffic
docker exec mosquitto mosquitto_sub -h localhost -t "ha/statestream/#"
```

## 📖 Documentation

- **[ScyllaDB Setup Guide](SCYLLA_GUIDE.md)**: Detailed setup and performance info
- **[AI Instructions](.github/copilot-instructions.md)**: For development with AI assistants

Perfect for integration with external data management systems and real-time streaming to the main Gauge project!
