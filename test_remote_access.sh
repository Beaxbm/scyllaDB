#!/bin/bash
# Remote Access Test Script for HexaHealth IoT Infrastructure
# Test gaugescylladb.duckdns.org connectivity

DOMAIN="gaugescylladb.duckdns.org"

echo "🏥 HexaHealth IoT Remote Access Test"
echo "====================================="
echo "Domain: $DOMAIN"
echo "Date: $(date)"
echo ""

echo "🌐 Step 1: Testing DNS resolution..."
if nslookup $DOMAIN > /dev/null 2>&1; then
    IP=$(nslookup $DOMAIN | grep "Address:" | tail -1 | awk '{print $2}')
    echo "✅ DNS resolved: $DOMAIN → $IP"
else
    echo "❌ DNS resolution failed for $DOMAIN"
    echo "💡 Make sure you've updated DuckDNS with your public IP"
    exit 1
fi

echo ""
echo "🔌 Step 2: Testing port connectivity..."

# Test MQTT port
if timeout 5 bash -c "</dev/tcp/$DOMAIN/1883" 2>/dev/null; then
    echo "✅ MQTT port 1883: OPEN"
else
    echo "❌ MQTT port 1883: CLOSED"
    echo "💡 Check router port forwarding for port 1883"
fi

# Test API port
if timeout 5 bash -c "</dev/tcp/$DOMAIN/8001" 2>/dev/null; then
    echo "✅ API port 8001: OPEN"
else
    echo "❌ API port 8001: CLOSED"  
    echo "💡 Check router port forwarding for port 8001"
fi

echo ""
echo "📊 Step 3: Testing API endpoints..."

# Test API health
API_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/api_test http://$DOMAIN:8001/health)
if [ "$API_RESPONSE" = "200" ]; then
    echo "✅ API Health Check: $(cat /tmp/api_test)"
else
    echo "❌ API Health Check failed (HTTP $API_RESPONSE)"
    echo "💡 Ensure Docker services are running: docker-compose up -d"
fi

# Test sensor data
SENSOR_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/sensors_test http://$DOMAIN:8001/sensors)
if [ "$SENSOR_RESPONSE" = "200" ]; then
    SENSOR_COUNT=$(cat /tmp/sensors_test | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    echo "✅ Sensor Data: $SENSOR_COUNT sensors available"
else
    echo "❌ Sensor data request failed (HTTP $SENSOR_RESPONSE)"
fi

echo ""
echo "🧪 Step 4: Testing MQTT real-time data..."

# Test MQTT subscription (brief test)
if command -v mosquitto_sub > /dev/null; then
    echo "📡 Testing MQTT subscription (5 seconds)..."
    timeout 5 mosquitto_sub -h $DOMAIN -t "ha/statestream/#" -C 3 2>/dev/null && echo "✅ MQTT data streaming successfully" || echo "❌ MQTT subscription failed"
else
    echo "💡 Install mosquitto-clients to test MQTT: brew install mosquitto"
fi

echo ""
echo "🎯 Step 5: HexaHealth Integration Test..."

# Test if HexaHealth integration can connect
cat << 'EOF' > /tmp/hexahealth_test.py
import paho.mqtt.client as mqtt
import sys
import time

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ HexaHealth IoT Client connected successfully!")
        client.subscribe("ha/statestream/sensor/+/state")
        print("📊 Subscribed to sensor data stream...")
    else:
        print(f"❌ HexaHealth IoT Client connection failed: {rc}")
        sys.exit(1)

def on_message(client, userdata, msg):
    sensor_id = msg.topic.split('/')[-2]
    value = msg.payload.decode()
    print(f"📈 Sensor Update: {sensor_id} = {value}")
    
try:
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("🔄 Connecting to HexaHealth IoT infrastructure...")
    client.connect("gaugescylladb.duckdns.org", 1883, 60)
    
    # Run for 10 seconds to catch some data
    client.loop_start()
    time.sleep(10)
    client.loop_stop()
    client.disconnect()
    
except Exception as e:
    print(f"❌ HexaHealth integration test failed: {e}")
    sys.exit(1)
EOF

if python3 /tmp/hexahealth_test.py; then
    echo "✅ HexaHealth integration ready!"
else
    echo "❌ HexaHealth integration needs attention"
fi

# Cleanup
rm -f /tmp/api_test /tmp/sensors_test /tmp/hexahealth_test.py

echo ""
echo "📋 Summary for HexaHealth Team:"
echo "================================"
echo "🌐 Remote Access URLs:"
echo "   • MQTT: gaugescylladb.duckdns.org:1883"  
echo "   • API:  http://gaugescylladb.duckdns.org:8001"
echo "   • UI:   http://gaugescylladb.duckdns.org:8123 (optional)"
echo ""
echo "💻 Integration Code:"
echo "   python3 services/hexahealth_simple_integration.py"
echo ""
echo "📊 Your IoT infrastructure is ready for global access!"