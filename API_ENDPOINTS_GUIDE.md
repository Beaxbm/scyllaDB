# 📊 Working API Endpoints for HexaHealth Integration

## ✅ Confirmed Working Endpoints

Your IoT infrastructure at `gaugescylladb.duckdns.org:8001` has these **working endpoints**:

### 1. Health Check
```bash
GET http://gaugescylladb.duckdns.org:8001/health
```
**Response:**
```json
{"status":"healthy","scylla":"connected"}
```

### 2. List All Sensors
```bash  
GET http://gaugescylladb.duckdns.org:8001/sensors
```
**Response:** Array of 45 sensors
```json
[
  {
    "sensor_id": "temperatura_e_umidade_externos_temperature",
    "domain": "sensor",
    "friendly_name": null,
    "device_class": null,
    "unit_of_measurement": null,
    "last_seen": "2025-10-16T13:57:26.343000"
  }
]
```

### 3. Get Latest Sensor Reading
```bash
GET http://gaugescylladb.duckdns.org:8001/sensors/{sensor_id}/latest
```

**Examples:**
```bash
# Temperature data
curl "http://gaugescylladb.duckdns.org:8001/sensors/temperatura_e_umidade_externos_temperature/latest"

# Humidity data  
curl "http://gaugescylladb.duckdns.org:8001/sensors/temperatura_e_umidade_externos_humidity/latest"

# Voltage monitoring
curl "http://gaugescylladb.duckdns.org:8001/sensors/tomada_20a_voltage/latest"
```

**Response:**
```json
{
  "timestamp": "2025-10-16T13:57:26.343000-03:00",
  "sensor_id": "temperatura_e_umidade_externos_temperature", 
  "value_numeric": 29.6,
  "value_text": null,
  "value_binary": null,
  "domain": "sensor",
  "unit": null,
  "quality": "good"
}
```

### 4. Get Sensor History
```bash
GET http://gaugescylladb.duckdns.org:8001/sensors/{sensor_id}/history?hours=24&limit=100
```

**Example:**
```bash
curl "http://gaugescylladb.duckdns.org:8001/sensors/temperatura_e_umidade_externos_temperature/history?hours=6"
```

## ❌ Endpoints That Don't Exist (Return "detail: Not Found")

These endpoints are **NOT available** - don't use them:

```bash
❌ GET http://gaugescylladb.duckdns.org:8001/
❌ GET http://gaugescylladb.duckdns.org:8001/latest
❌ GET http://gaugescylladb.duckdns.org:8001/data/export  
❌ GET http://gaugescylladb.duckdns.org:8001/sensors/domain/sensor
```

## 🏥 HexaHealth Integration Examples

### Python Integration
```python
import requests
import json

# Base URL for your IoT API
BASE_URL = "http://gaugescylladb.duckdns.org:8001"

def get_patient_environment_data():
    """Get current environment data for patient monitoring"""
    
    # Get all available sensors
    sensors_response = requests.get(f"{BASE_URL}/sensors")
    sensors = sensors_response.json()
    
    environment_data = {
        "temperature_sensors": [],
        "humidity_sensors": [], 
        "electrical_monitoring": [],
        "access_control": []
    }
    
    # Get latest readings for key sensors
    for sensor in sensors:
        sensor_id = sensor["sensor_id"]
        
        try:
            # Get latest reading
            latest_response = requests.get(f"{BASE_URL}/sensors/{sensor_id}/latest")
            if latest_response.status_code == 200:
                latest_data = latest_response.json()
                
                # Categorize by sensor type for health monitoring
                if "temperature" in sensor_id:
                    environment_data["temperature_sensors"].append({
                        "location": extract_location(sensor_id),
                        "value": latest_data["value_numeric"],
                        "unit": "°C",
                        "timestamp": latest_data["timestamp"],
                        "health_status": assess_temperature_health(latest_data["value_numeric"])
                    })
                    
                elif "humidity" in sensor_id:
                    environment_data["humidity_sensors"].append({
                        "location": extract_location(sensor_id), 
                        "value": latest_data["value_numeric"],
                        "unit": "%",
                        "timestamp": latest_data["timestamp"],
                        "health_status": assess_humidity_health(latest_data["value_numeric"])
                    })
                    
                elif "voltage" in sensor_id:
                    environment_data["electrical_monitoring"].append({
                        "location": extract_location(sensor_id),
                        "value": latest_data["value_numeric"], 
                        "unit": "V",
                        "timestamp": latest_data["timestamp"],
                        "safety_status": assess_electrical_safety(latest_data["value_numeric"])
                    })
                    
        except Exception as e:
            print(f"Error reading sensor {sensor_id}: {e}")
            
    return environment_data

def extract_location(sensor_id):
    """Extract location from sensor ID"""
    if "externos" in sensor_id:
        return "Outdoor"
    elif "frigobar" in sensor_id:
        return "Kitchen/Refrigerator"
    elif "cervejeira" in sensor_id:
        return "Beverage Cooler"
    elif "adega" in sensor_id:
        return "Wine Cellar"
    else:
        return "Indoor"

def assess_temperature_health(temp_celsius):
    """Assess health impact of temperature"""
    if temp_celsius < 16 or temp_celsius > 28:
        return {"level": "concern", "message": "Temperature outside comfortable range"}
    elif temp_celsius < 18 or temp_celsius > 26:
        return {"level": "monitor", "message": "Temperature suboptimal"}
    else:
        return {"level": "good", "message": "Temperature in healthy range"}

def assess_humidity_health(humidity_percent):
    """Assess health impact of humidity"""
    if humidity_percent < 30 or humidity_percent > 70:
        return {"level": "concern", "message": "Humidity may affect respiratory health"}
    elif humidity_percent < 40 or humidity_percent > 60:
        return {"level": "monitor", "message": "Humidity outside optimal range"}
    else:
        return {"level": "good", "message": "Humidity in healthy range"}

def assess_electrical_safety(voltage):
    """Assess electrical safety"""
    if voltage < 200 or voltage > 240:
        return {"level": "concern", "message": "Voltage outside safe range"}
    else:
        return {"level": "safe", "message": "Voltage within normal limits"}

# Example usage
if __name__ == "__main__":
    try:
        # Test API connectivity
        health_response = requests.get(f"{BASE_URL}/health")
        print(f"🏥 API Health: {health_response.json()}")
        
        # Get patient environment data
        env_data = get_patient_environment_data()
        
        print("\n🌡️ Temperature Monitoring:")
        for temp_sensor in env_data["temperature_sensors"]:
            print(f"  📍 {temp_sensor['location']}: {temp_sensor['value']}°C - {temp_sensor['health_status']['message']}")
            
        print("\n💧 Humidity Monitoring:")
        for humidity_sensor in env_data["humidity_sensors"]:
            print(f"  📍 {humidity_sensor['location']}: {humidity_sensor['value']}% - {humidity_sensor['health_status']['message']}")
            
        print("\n⚡ Electrical Monitoring:")
        for electrical_sensor in env_data["electrical_monitoring"]:
            print(f"  📍 {electrical_sensor['location']}: {electrical_sensor['value']}V - {electrical_sensor['safety_status']['message']}")
            
    except Exception as e:
        print(f"❌ Error connecting to IoT infrastructure: {e}")
```

### JavaScript/React Integration
```javascript
// HexaHealth IoT API Client
class HexaHealthIoTClient {
    constructor() {
        this.baseURL = 'http://gaugescylladb.duckdns.org:8001';
    }
    
    async checkHealth() {
        const response = await fetch(`${this.baseURL}/health`);
        return response.json();
    }
    
    async getAllSensors() {
        const response = await fetch(`${this.baseURL}/sensors`);
        return response.json();
    }
    
    async getLatestReading(sensorId) {
        const response = await fetch(`${this.baseURL}/sensors/${sensorId}/latest`);
        if (response.ok) {
            return response.json();
        }
        return null;
    }
    
    async getPatientEnvironmentData() {
        try {
            const sensors = await this.getAllSensors();
            const environmentData = {
                temperature: [],
                humidity: [],
                electrical: [],
                lastUpdate: new Date().toISOString()
            };
            
            for (const sensor of sensors) {
                const latest = await this.getLatestReading(sensor.sensor_id);
                if (latest && latest.value_numeric !== null) {
                    
                    if (sensor.sensor_id.includes('temperature')) {
                        environmentData.temperature.push({
                            location: this.extractLocation(sensor.sensor_id),
                            value: latest.value_numeric,
                            timestamp: latest.timestamp,
                            healthStatus: this.assessTemperatureHealth(latest.value_numeric)
                        });
                    }
                    
                    if (sensor.sensor_id.includes('humidity')) {
                        environmentData.humidity.push({
                            location: this.extractLocation(sensor.sensor_id),
                            value: latest.value_numeric,
                            timestamp: latest.timestamp,
                            healthStatus: this.assessHumidityHealth(latest.value_numeric)
                        });
                    }
                    
                    if (sensor.sensor_id.includes('voltage')) {
                        environmentData.electrical.push({
                            location: this.extractLocation(sensor.sensor_id),
                            value: latest.value_numeric,
                            timestamp: latest.timestamp,
                            safetyStatus: this.assessElectricalSafety(latest.value_numeric)
                        });
                    }
                }
            }
            
            return environmentData;
        } catch (error) {
            console.error('Error fetching environment data:', error);
            return null;
        }
    }
    
    extractLocation(sensorId) {
        if (sensorId.includes('externos')) return 'Outdoor';
        if (sensorId.includes('frigobar')) return 'Kitchen/Refrigerator'; 
        if (sensorId.includes('cervejeira')) return 'Beverage Cooler';
        if (sensorId.includes('adega')) return 'Wine Cellar';
        return 'Indoor';
    }
    
    assessTemperatureHealth(temp) {
        if (temp < 16 || temp > 28) return { level: 'concern', color: 'red' };
        if (temp < 18 || temp > 26) return { level: 'monitor', color: 'yellow' };
        return { level: 'good', color: 'green' };
    }
    
    assessHumidityHealth(humidity) {
        if (humidity < 30 || humidity > 70) return { level: 'concern', color: 'red' };
        if (humidity < 40 || humidity > 60) return { level: 'monitor', color: 'yellow' };
        return { level: 'good', color: 'green' };
    }
    
    assessElectricalSafety(voltage) {
        if (voltage < 200 || voltage > 240) return { level: 'concern', color: 'red' };
        return { level: 'safe', color: 'green' };
    }
}

// React Component Example
function PatientEnvironmentDashboard() {
    const [environmentData, setEnvironmentData] = useState(null);
    const [loading, setLoading] = useState(true);
    const iotClient = new HexaHealthIoTClient();
    
    useEffect(() => {
        const fetchData = async () => {
            const data = await iotClient.getPatientEnvironmentData();
            setEnvironmentData(data);
            setLoading(false);
        };
        
        fetchData();
        const interval = setInterval(fetchData, 30000); // Update every 30 seconds
        
        return () => clearInterval(interval);
    }, []);
    
    if (loading) return <div>Loading patient environment data...</div>;
    if (!environmentData) return <div>Unable to load environment data</div>;
    
    return (
        <div className="patient-environment-dashboard">
            <h2>Patient Environment Monitoring</h2>
            
            <div className="temperature-section">
                <h3>🌡️ Temperature Monitoring</h3>
                {environmentData.temperature.map((sensor, index) => (
                    <div key={index} className={`sensor-reading ${sensor.healthStatus.color}`}>
                        <span>{sensor.location}</span>
                        <span>{sensor.value}°C</span>
                        <span className="status">{sensor.healthStatus.level}</span>
                    </div>
                ))}
            </div>
            
            <div className="humidity-section">
                <h3>💧 Humidity Monitoring</h3>
                {environmentData.humidity.map((sensor, index) => (
                    <div key={index} className={`sensor-reading ${sensor.healthStatus.color}`}>
                        <span>{sensor.location}</span>
                        <span>{sensor.value}%</span>
                        <span className="status">{sensor.healthStatus.level}</span>
                    </div>
                ))}
            </div>
            
            <div className="electrical-section">
                <h3>⚡ Electrical Safety</h3>
                {environmentData.electrical.map((sensor, index) => (
                    <div key={index} className={`sensor-reading ${sensor.safetyStatus.color}`}>
                        <span>{sensor.location}</span>
                        <span>{sensor.value}V</span>
                        <span className="status">{sensor.safetyStatus.level}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

## 🎯 Key Takeaways for HexaHealth Team

1. **✅ Use these working endpoints** - they're all tested and operational
2. **❌ Avoid the non-existent endpoints** - they'll return "detail: Not Found"
3. **📊 45 sensors available** - temperature, humidity, voltage, door sensors
4. **🌐 Global access** - works from anywhere via `gaugescylladb.duckdns.org`
5. **🔄 Real-time MQTT** - also available at `gaugescylladb.duckdns.org:1883`

Your IoT infrastructure is **fully operational** for HexaHealth integration! 🏥✨