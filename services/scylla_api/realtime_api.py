"""
Real-time Gauge API with WebSocket Support

Provides both REST endpoints and WebSocket streaming for real-time sensor data access.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import json
import asyncio
import logging
from pydantic import BaseModel
import os
import zoneinfo

from cassandra.cluster import Cluster
from cassandra.policies import TokenAwarePolicy, DCAwareRoundRobinPolicy
from cassandra import ConsistencyLevel
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gauge IoT Real-time API",
    description="Real-time REST and WebSocket API for IoT sensor data",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
scylla_session = None
active_websockets: Set[WebSocket] = set()
mqtt_client = None

# Configuration
SCYLLA_HOSTS = os.getenv('SCYLLA_HOSTS', 'scylla-node1').split(',')
SCYLLA_KEYSPACE = os.getenv('SCYLLA_KEYSPACE', 'iot')
MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
TIMEZONE = zoneinfo.ZoneInfo('America/Recife')

# Data models
class SensorReading(BaseModel):
    timestamp: str
    sensor_id: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    value_binary: Optional[bool] = None
    domain: str
    unit: Optional[str] = None
    quality: str = "good"

class RealtimeMessage(BaseModel):
    type: str  # "sensor_update", "connection_status", "error"
    data: Dict[Any, Any]
    timestamp: str

def format_timestamp(dt: datetime) -> str:
    """Format datetime to local timezone string"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo('UTC'))
    local_dt = dt.astimezone(TIMEZONE)
    return local_dt.isoformat()

def setup_scylla():
    """Initialize ScyllaDB connection"""
    global scylla_session
    try:
        cluster = Cluster(
            SCYLLA_HOSTS,
            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
            protocol_version=4
        )
        scylla_session = cluster.connect()
        scylla_session.default_consistency_level = ConsistencyLevel.LOCAL_QUORUM
        scylla_session.set_keyspace(SCYLLA_KEYSPACE)
        logger.info(f"Connected to ScyllaDB: {SCYLLA_HOSTS}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to ScyllaDB: {e}")
        return False

def on_mqtt_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe("ha/statestream/+/+/state")
    else:
        logger.error(f"Failed to connect to MQTT broker: {rc}")

def on_mqtt_message(client, userdata, msg):
    """MQTT message callback - broadcasts to WebSocket clients"""
    try:
        # Parse MQTT topic
        topic_parts = msg.topic.split('/')
        if len(topic_parts) >= 5:
            domain = topic_parts[2]
            sensor_name = topic_parts[3]
            
            # Create real-time message
            message = RealtimeMessage(
                type="sensor_update",
                data={
                    "sensor_id": sensor_name,
                    "domain": domain,
                    "value": msg.payload.decode(),
                    "topic": msg.topic
                },
                timestamp=format_timestamp(datetime.now())
            )
            
            # Broadcast to all connected WebSocket clients
            if active_websockets:
                asyncio.create_task(broadcast_to_websockets(message.dict()))
                
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

async def broadcast_to_websockets(message: dict):
    """Broadcast message to all active WebSocket connections"""
    if not active_websockets:
        return
        
    disconnected = set()
    for websocket in active_websockets.copy():
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"WebSocket send failed: {e}")
            disconnected.add(websocket)
    
    # Remove disconnected clients
    active_websockets -= disconnected

def setup_mqtt():
    """Initialize MQTT client for real-time data"""
    global mqtt_client
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()
        logger.info(f"Connected to MQTT broker: {MQTT_HOST}:{MQTT_PORT}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    setup_scylla()
    setup_mqtt()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

# REST API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": format_timestamp(datetime.now()),
        "services": {
            "scylla": scylla_session is not None,
            "mqtt": mqtt_client is not None,
            "websocket_clients": len(active_websockets)
        }
    }

@app.get("/sensors", response_model=List[Dict])
async def get_all_sensors():
    """Get list of all available sensors"""
    if not scylla_session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        query = """
        SELECT DISTINCT sensor_id, domain 
        FROM sensor_readings 
        WHERE time > ? 
        ALLOW FILTERING
        """
        
        # Get sensors from last 7 days
        cutoff = datetime.now() - timedelta(days=7)
        rows = scylla_session.execute(query, (cutoff,))
        
        sensors = []
        for row in rows:
            sensors.append({
                "sensor_id": row.sensor_id,
                "domain": row.domain
            })
        
        return sensors
        
    except Exception as e:
        logger.error(f"Error fetching sensors: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

@app.get("/sensors/{sensor_id}/latest", response_model=SensorReading)
async def get_latest_reading(sensor_id: str):
    """Get latest reading for a specific sensor"""
    if not scylla_session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        query = """
        SELECT time, sensor_id, value_numeric, value_text, value_binary, domain, unit, quality
        FROM sensor_readings 
        WHERE sensor_id = ? 
        ORDER BY time DESC 
        LIMIT 1
        """
        
        rows = scylla_session.execute(query, (sensor_id,))
        row = rows.one()
        
        if not row:
            raise HTTPException(status_code=404, detail="Sensor not found")
        
        return SensorReading(
            timestamp=format_timestamp(row.time),
            sensor_id=row.sensor_id,
            value_numeric=row.value_numeric,
            value_text=row.value_text,
            value_binary=row.value_binary,
            domain=row.domain,
            unit=row.unit,
            quality=row.quality or "good"
        )
        
    except Exception as e:
        logger.error(f"Error fetching latest reading for {sensor_id}: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

@app.get("/sensors/{sensor_id}/history", response_model=List[SensorReading])
async def get_sensor_history(sensor_id: str, hours: int = 24, limit: int = 1000):
    """Get historical readings for a sensor"""
    if not scylla_session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        query = """
        SELECT time, sensor_id, value_numeric, value_text, value_binary, domain, unit, quality
        FROM sensor_readings 
        WHERE sensor_id = ? AND time > ?
        ORDER BY time DESC 
        LIMIT ?
        """
        
        cutoff = datetime.now() - timedelta(hours=hours)
        rows = scylla_session.execute(query, (sensor_id, cutoff, limit))
        
        readings = []
        for row in rows:
            readings.append(SensorReading(
                timestamp=format_timestamp(row.time),
                sensor_id=row.sensor_id,
                value_numeric=row.value_numeric,
                value_text=row.value_text,
                value_binary=row.value_binary,
                domain=row.domain,
                unit=row.unit,
                quality=row.quality or "good"
            ))
        
        return readings
        
    except Exception as e:
        logger.error(f"Error fetching history for {sensor_id}: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

# WebSocket endpoint for real-time data
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time sensor data streaming"""
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        # Send connection confirmation
        welcome_message = RealtimeMessage(
            type="connection_status",
            data={"status": "connected", "message": "Real-time sensor data stream active"},
            timestamp=format_timestamp(datetime.now())
        )
        await websocket.send_text(json.dumps(welcome_message.dict()))
        
        # Keep connection alive
        while True:
            # Wait for client messages (optional - for client-side filtering requests)
            try:
                data = await websocket.receive_text()
                # Handle client requests if needed
                logger.info(f"WebSocket client message: {data}")
            except:
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        active_websockets.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)