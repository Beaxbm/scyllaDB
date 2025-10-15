# AI Agent Instructions for Gauge IoT Infrastructure

## Project Overview
This is a complete IoT data collection and management infrastructure for Zigbee sensor networks. The system uses Home Assistant as the central hub, MQTT for communication, and provides a REST API for remote data access.

## Architecture & Data Flow
```
Zigbee Devices → Zigbee2MQTT → Mosquitto MQTT → Home Assistant → MQTT Statestream → MQTT Bridge → TimescaleDB → REST API
```

Key components and their roles:
- **Home Assistant** (`homeassistant/`): Central IoT hub with MQTT statestream publishing to `ha/statestream/*`
- **Zigbee2MQTT** (`zigbee2mqtt/`): Zigbee-to-MQTT bridge, web UI on port 8080
- **Mosquitto** (`mosquitto/`): MQTT broker with SSL certificates in `config/`
- **TimescaleDB**: Time-series database storing sensor data with hourly aggregations
- **MQTT Bridge** (`services/mqtt_bridge/`): Python service subscribing to statestream, storing in DB
- **Gauge API** (`services/api/`): FastAPI REST service exposing JSON endpoints on port 8000

## Development Workflows

### Starting the Infrastructure
```bash
docker-compose up -d  # Start all services
docker-compose logs -f mqtt-bridge  # Monitor data ingestion
curl http://localhost:8000/health    # Verify API health
```

### Key Configuration Files
- `homeassistant/configuration.yaml`: Contains `mqtt_statestream` config publishing sensor/binary_sensor domains
- `zigbee2mqtt/data/configuration.yaml`: Zigbee network settings, references `/dev/ttyUSB0` adapter
- `mosquitto/config/mosquitto.conf`: MQTT broker with SSL certificates
- `database/init/01_init.sql`: TimescaleDB schema with hypertables and continuous aggregates

### Database Schema
Main table: `sensor_data` (hypertable partitioned by time)
- Primary key: `(time, entity_id)`
- Continuous aggregate: `sensor_data_hourly` for performance
- Indexes on `entity_id`, `domain`, and `time` for fast queries

## API Patterns & Usage

### Standard Endpoints
- `GET /sensors` - List all available sensors with metadata
- `GET /sensors/{entity_id}/latest` - Latest reading for specific sensor
- `GET /sensors/{entity_id}/history?hours=24&limit=1000` - Historical data
- `GET /sensors/domain/{domain}` - All sensors in domain (sensor, binary_sensor)
- `GET /data/export?domain=sensor&hours=12` - Bulk data export

### JSON Response Structure
```json
{
  "time": "2025-10-15T14:30:00.123456+00:00",
  "entity_id": "sensor.temperature_01", 
  "state": "23.5",
  "domain": "sensor",
  "friendly_name": "Living Room Temperature",
  "unit_of_measurement": "°C",
  "attributes": {...}
}
```

## Project-Specific Conventions

### Entity ID Patterns
- Follows Home Assistant format: `{domain}.{name}` (e.g., `sensor.temperature_01`)
- Domains filtered in statestream: `sensor`, `binary_sensor`

### Service Dependencies
- All services depend on `mosquitto` for MQTT communication
- Data services depend on `timescaledb` for persistence
- MQTT Bridge must start before API to ensure data availability

### Error Handling & Monitoring
- Services use structured logging with timestamps
- Database connections include retry logic with exponential backoff
- API includes `/health` endpoint checking database connectivity

## Development Environment
- Uses Docker Compose for container orchestration
- Python services use separate Dockerfiles in `services/*/`
- SSL certificates stored in `mosquitto/config/` for secure MQTT
- Database initialization scripts in `database/init/`

## Common Debugging Patterns
1. Check MQTT message flow: `docker-compose logs mosquitto`
2. Verify data ingestion: `docker-compose logs mqtt-bridge`  
3. Database connectivity: `curl http://localhost:8000/health`
4. Home Assistant statestream: Check `homeassistant/home-assistant.log*`

## Integration Points
- External data managers access via HTTP GET to port 8000
- Direct database access available on port 5432
- Zigbee device management via web UI on port 8080
- Home Assistant UI on port 8123