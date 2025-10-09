# MQTT Infrastructure Branch - Gauge Monoproject

MQTT infrastructure component providing real-time sensor data streaming for the Gauge Monoproject.

## 🏗️ Services

- **Mosquitto MQTT Broker**: Message broker for sensor data
- **Home Assistant**: IoT platform with Tuya device integration
- **MQTT Statestream**: Real-time sensor data publishing

## 🚀 Quick Start

```bash
# Start MQTT infrastructure
docker compose up -d

# Check services
docker compose ps

# Monitor sensor data
docker exec -it mosquitto sh -c "mosquitto_sub -h localhost -p 1883 -t 'ha/statestream/#' -v"
```

## 📊 Available Sensor Data

- 🌡️ External Temperature: `ha/statestream/sensor/temperatura_e_umidade_externos_temperature/state`
- 💧 External Humidity: `ha/statestream/sensor/temperatura_e_umidade_externos_humidity/state`
- 🧊 Fridge Temperature: `ha/statestream/sensor/temperatura_e_umidade_frigobar_temperature/state`
- 💧 Fridge Humidity: `ha/statestream/sensor/temperatura_e_umidade_frigobar_humidity/state`
- ☀️ Light Sensors: `ha/statestream/sensor/*_illuminance/state`

## 🔌 Integration with Main Project

### Python Client Example
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

## 🛠️ Configuration

- **Home Assistant UI**: http://localhost:8123
- **MQTT Broker**: localhost:1883 (plain) / localhost:8883 (TLS)
- **Configuration**: `homeassistant/configuration.yaml`

## 🔗 Connection to Main Gauge Project

This infrastructure provides real-time sensor data that can be consumed by other branches/components of the gauge_monoproject via MQTT subscription.

## 📁 Structure

```
mqtt-infrastructure/
├── docker-compose.yml          # Services definition
├── homeassistant/              # HA configuration
├── mosquitto/                  # MQTT broker config
└── README.md                   # This documentation
```
