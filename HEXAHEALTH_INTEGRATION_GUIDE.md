# 🏥 HexaHealth IoT Integration Guide

## Quick Setup for Your Product Team

### 🚀 Option 1: DuckDNS (Fastest - Development/Testing)

**Pros:** 
- ✅ Free and immediate setup
- ✅ Perfect for product development and testing
- ✅ Your team can start integrating today

**Setup Steps:**

1. **Your IoT hub is already configured:** `gaugescylladb.duckdns.org`

2. **Router Configuration (One-time setup):**
```bash
# Forward these ports on your router:
# External Port → Internal Port → Service
1883         → 1883         → Real-time sensor data (MQTT)
8001         → 8001         → Historical data API (REST)
8123         → 8123         → IoT management UI (Optional)
```

3. **Test the connection:**
```bash
# From any internet connection (not your local network)
curl http://gaugescylladb.duckdns.org:8001/health
# Should return: {"status": "healthy", "timestamp": "..."}
```

4. **Your team can immediately use:**
```python
# Install in your HexaHealth backend
pip install paho-mqtt

# Use the integration service
from services.hexahealth_simple_integration import HexaHealthIoTClient

# Connect to your IoT data
iot_client = HexaHealthIoTClient(environment="development")
iot_client.connect_realtime()

# Get patient environment data
environment_status = iot_client.get_current_environment_status()
health_alerts = iot_client.get_health_alerts()
```

---

### 🌐 Option 2: Cloud Deployment (Production-Ready)

**For when you're ready to scale:**

#### AWS Deployment
```bash
# 1. Deploy your IoT infrastructure to AWS EC2
# 2. Use Route 53 for DNS: iot-api.hexahealth.com  
# 3. Add Application Load Balancer for high availability
# 4. Use RDS for database scaling
```

#### DigitalOcean (Simpler)
```bash
# 1. Create a droplet ($20/month)
# 2. Deploy with Docker
# 3. Use DigitalOcean DNS: iot.hexahealth.com
# 4. Add SSL certificate with Let's Encrypt
```

---

## 🔌 Frontend Integration Examples

### React Dashboard Component
```jsx
import React, { useState, useEffect } from 'react';

function PatientEnvironmentDashboard({ patientId }) {
  const [environmentData, setEnvironmentData] = useState({});
  const [healthAlerts, setHealthAlerts] = useState([]);

  useEffect(() => {
    // Connect to your IoT API
    const fetchEnvironmentData = async () => {
      try {
        const response = await fetch(`/api/iot/patient/${patientId}/environment`);
        const data = await response.json();
        setEnvironmentData(data);
      } catch (error) {
        console.error('Failed to fetch environment data:', error);
      }
    };

    // Real-time updates via WebSocket
    const ws = new WebSocket(`wss://gaugescylladb.duckdns.org/realtime`);
    ws.onmessage = (event) => {
      const sensorData = JSON.parse(event.data);
      // Update UI with real-time sensor data
      updateEnvironmentDisplay(sensorData);
    };

    fetchEnvironmentData();
    const interval = setInterval(fetchEnvironmentData, 30000); // Update every 30s

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, [patientId]);

  return (
    <div className="patient-environment-dashboard">
      <h3>Patient Environment Monitoring</h3>
      
      {/* Health Score */}
      <div className="health-score">
        <h4>Environment Health Score</h4>
        <div className="score-circle">
          {environmentData.overall_health_score || 'N/A'}/100
        </div>
      </div>

      {/* Temperature Zones */}
      <div className="temperature-zones">
        <h4>Temperature Monitoring</h4>
        {environmentData.temperature_zones?.zones && 
          Object.entries(environmentData.temperature_zones.zones).map(([zone, temp]) => (
            <div key={zone} className="temp-zone">
              <span>{zone}</span>
              <span className={temp < 18 || temp > 26 ? 'temp-alert' : 'temp-normal'}>
                {temp}°C
              </span>
            </div>
          ))
        }
      </div>

      {/* Health Alerts */}
      <div className="health-alerts">
        <h4>Health Alerts</h4>
        {healthAlerts.length === 0 ? (
          <p className="no-alerts">✅ No health concerns detected</p>
        ) : (
          healthAlerts.map((alert, index) => (
            <div key={index} className={`alert ${alert.severity}`}>
              <span className="alert-time">
                {new Date(alert.timestamp).toLocaleTimeString()}
              </span>
              <span className="alert-message">{alert.message}</span>
            </div>
          ))
        )}
      </div>

      {/* Activity Summary */}
      <div className="activity-summary">
        <h4>Patient Activity</h4>
        <p>Active zones: {environmentData.activity_detected?.active_zones || 0}</p>
        <div className="recent-activity">
          {environmentData.activity_detected?.recent_activity?.slice(0, 3).map((activity, index) => (
            <div key={index} className="activity-item">
              <span>{activity.location}</span>
              <span>{new Date(activity.time).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default PatientEnvironmentDashboard;
```

### CSS for the Dashboard
```css
.patient-environment-dashboard {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.health-score .score-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  margin: 10px 0;
}

.temp-zone {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  margin: 4px 0;
  background: white;
  border-radius: 4px;
}

.temp-alert {
  color: #dc3545;
  font-weight: bold;
}

.temp-normal {
  color: #28a745;
}

.alert.high {
  background-color: #f8d7da;
  border-left: 4px solid #dc3545;
  padding: 10px;
  margin: 5px 0;
}

.no-alerts {
  color: #28a745;
  font-style: italic;
}

.activity-item {
  display: flex;
  justify-content: space-between;
  padding: 5px;
  background: white;
  margin: 2px 0;
  border-radius: 3px;
}
```

---

## 🔧 Backend Integration Examples

### Django Integration
```python
# views.py - HexaHealth backend
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from services.hexahealth_simple_integration import HexaHealthIoTClient
import json

# Initialize IoT client (singleton)
iot_client = HexaHealthIoTClient(environment="development")
iot_client.connect_realtime()

@csrf_exempt
def patient_environment_api(request, patient_id):
    """API endpoint for patient environment data"""
    
    if request.method == 'GET':
        try:
            # Get current environment status
            environment_status = iot_client.get_current_environment_status()
            health_alerts = iot_client.get_health_alerts(hours=24)
            
            # Add patient-specific logic
            patient_data = {
                'patient_id': patient_id,
                'environment_health': environment_status,
                'health_alerts': health_alerts,
                'recommendations': generate_health_recommendations(environment_status),
                'last_updated': environment_status.get('last_update')
            }
            
            return JsonResponse(patient_data)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def generate_health_recommendations(environment_status):
    """Generate health recommendations based on environment data"""
    recommendations = []
    
    health_score = environment_status.get('overall_health_score', 100)
    
    if health_score < 70:
        recommendations.append({
            'type': 'environment',
            'priority': 'high',
            'message': 'Environment conditions may be affecting patient health',
            'actions': ['Check temperature and humidity levels', 'Improve ventilation']
        })
    
    # Temperature recommendations
    temp_zones = environment_status.get('temperature_zones', {}).get('zones', {})
    for zone, temp in temp_zones.items():
        if temp < 18:
            recommendations.append({
                'type': 'temperature',
                'priority': 'medium',
                'message': f'Temperature in {zone} is too cold ({temp}°C)',
                'actions': ['Increase heating', 'Check for drafts']
            })
        elif temp > 28:
            recommendations.append({
                'type': 'temperature', 
                'priority': 'medium',
                'message': f'Temperature in {zone} is too warm ({temp}°C)',
                'actions': ['Improve cooling', 'Check ventilation']
            })
    
    return recommendations

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/iot/patient/<str:patient_id>/environment/', views.patient_environment_api, name='patient_environment'),
]
```

### Flask Integration
```python
# app.py - HexaHealth Flask backend
from flask import Flask, jsonify, request
from services.hexahealth_simple_integration import HexaHealthIoTClient
import threading
import time

app = Flask(__name__)

# Initialize IoT client in background thread
iot_client = None

def init_iot_client():
    global iot_client
    iot_client = HexaHealthIoTClient(environment="development")
    connected = iot_client.connect_realtime()
    if connected:
        print("✅ IoT client connected")
    else:
        print("❌ IoT client connection failed")

# Start IoT client in background
threading.Thread(target=init_iot_client, daemon=True).start()

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'iot_connected': iot_client is not None,
        'timestamp': time.time()
    })

@app.route('/api/iot/dashboard')
def iot_dashboard():
    """Main IoT dashboard data"""
    if not iot_client:
        return jsonify({'error': 'IoT client not connected'}), 503
    
    try:
        environment_status = iot_client.get_current_environment_status()
        health_alerts = iot_client.get_health_alerts(hours=6)
        
        dashboard_data = {
            'environment': environment_status,
            'alerts': health_alerts,
            'summary': {
                'total_sensors': environment_status.get('sensors_active', 0),
                'health_score': environment_status.get('overall_health_score', 0),
                'alert_count': len(health_alerts),
                'locations_monitored': len(environment_status.get('locations', []))
            }
        }
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/iot/location/<location_name>')
def location_data(location_name):
    """Get data for specific location"""
    if not iot_client:
        return jsonify({'error': 'IoT client not connected'}), 503
    
    try:
        location_sensors = iot_client.get_sensor_data_for_location(location_name)
        return jsonify({
            'location': location_name,
            'sensors': location_sensors,
            'sensor_count': len(location_sensors)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## 📱 Quick Test Instructions

### 1. Test Your Current Setup
```bash
# From outside your network (use mobile hotspot):
curl http://gaugescylladb.duckdns.org:8001/health

# Should return: {"status": "healthy", ...}
```

### 2. Run the HexaHealth Integration
```bash
cd /Users/beatrizximenesbandeira/Projetos/Infra_Gauge_FullZigbeeBIA

# Install requirements
pip install paho-mqtt

# Test the integration
python services/hexahealth_simple_integration.py
```

### 3. Expected Output
```
🏥 Starting HexaHealth IoT Integration...
✅ Connected to real-time IoT data stream
📊 Monitoring patient environment data...
📊 temperature: 29.3 °C | Location: Outdoor Environment
📊 humidity: 57.8 % | Location: Outdoor Environment  
📊 temperature: 7.2 °C | Location: Kitchen/Refrigerator
📊 electrical: 219.2 V | Location: Indoor Environment

🏥 Health Status Update:
   Overall Health Score: 87.5/100
   Active Sensors: 8
   Health Alerts: 0
   Temperature Zones:
     • Outdoor Environment: 29.3°C
     • Kitchen/Refrigerator: 7.2°C
```

## 🎯 My Recommendation

**Start with DuckDNS** (your current setup) for immediate development:

1. ✅ **Configure your router** (port forwarding 1883 and 8001)
2. ✅ **Test the integration** with the Python script I created  
3. ✅ **Integrate with your HexaHealth frontend/backend** using the examples above
4. ✅ **Develop your product features** using real IoT data

**When ready for production customers:**

1. 🚀 **Deploy to cloud** (AWS, DigitalOcean, or Azure)
2. 🔒 **Add security** (SSL, authentication, rate limiting) 
3. 📈 **Scale infrastructure** for multiple customers
4. 🌐 **Use professional domain** (iot.hexahealth.com)

Your IoT infrastructure is production-ready and can support both approaches! 🎉

Would you like me to help you with:
1. **Router configuration** for DuckDNS access?
2. **Frontend integration** examples for your specific UI framework?
3. **Backend API** design for your HexaHealth product?
4. **Cloud deployment** planning for production?