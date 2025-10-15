# Gauge IoT Infrastructure

Complete IoT data infrastructure with Home Assistant, MQTT, and ScyllaDB for high-performance sensor data management.

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

## 🔧 Architecture

```
Home Assistant → MQTT Statestream → ScyllaDB Ingestor → ScyllaDB → REST API
```

**Core Services:**
- `docker-compose.yml`: Home Assistant + MQTT broker
- `docker-compose-scylla.yml`: ScyllaDB + API + Ingestor

**Key Features:**
- ⚡ **100x faster** queries than traditional databases
- 📈 **Linear scaling** - add nodes for more performance
- 🔄 **Unified schema** - all sensor types in one table
- ⏰ **Automatic TTL** - data retention without maintenance
- 🎯 **Time-series optimized** - built for IoT workloads

## 📡 API Examples

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

## 🔍 Monitoring

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

## 🎯 For Your Data Manager

The API provides fast JSON responses for all sensor data:

```python
import requests

# Get all temperature sensors
sensors = requests.get("http://localhost:8001/sensors/domain/sensor").json()
temps = [s for s in sensors if s.get('unit') == '°C']

# Get recent door events  
events = requests.get("http://localhost:8001/sensors/porta_entrada/events").json()
```

Perfect for integration with external data management systems!
