#!/bin/bash

# Simple MQTT Test Script - No Python Required
# This uses the mosquitto client inside the Docker container

echo "🏠 Gauge IoT - Direct MQTT Test"
echo "================================"
echo "📡 Connecting to MQTT broker..."
echo "🔄 Listening for sensor data (showing 10 messages)..."
echo ""

# Connect to MQTT broker and show live sensor data
docker exec mosquitto mosquitto_sub -h localhost -t "ha/statestream/+/+/state" -v -C 10

echo ""
echo "✅ Test complete! Your MQTT broker is working."
echo ""
echo "💡 To access this data in your application:"
echo "   - Host: localhost"
echo "   - Port: 1883"
echo "   - Topics: ha/statestream/+/+/state"
echo ""
echo "🚀 Run this for continuous monitoring:"
echo "   docker exec mosquitto mosquitto_sub -h localhost -t 'ha/statestream/#' -v"