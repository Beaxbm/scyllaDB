"""
Simple Gauge API with ScyllaDB Backend - Test Version

Basic REST API for IoT sensor data with minimal prepared statements.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel
from dataclasses import dataclass
import os
import logging
import zoneinfo

from cassandra.cluster import Cluster
from cassandra.policies import TokenAwarePolicy, DCAwareRoundRobinPolicy
from cassandra import ConsistencyLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gauge IoT API - Test",
    description="Simple REST API for IoT sensor data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global ScyllaDB connection
cluster = None
session = None

# Configuration
SCYLLA_HOSTS = os.getenv('SCYLLA_HOSTS', 'scylla-node1').split(',')
KEYSPACE = os.getenv('SCYLLA_KEYSPACE', 'iot')
TENANT = os.getenv('TENANT_ID', 'gauge')
SITE = os.getenv('SITE_ID', 'recife')

# Timezone configuration
LOCAL_TIMEZONE = zoneinfo.ZoneInfo('America/Recife')

def format_timestamp(ts: datetime) -> str:
    """Format timestamp to local timezone ISO format"""
    if ts is None:
        return None
    # ScyllaDB stores timestamps as timezone-naive UTC, so we need to add UTC timezone first
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=zoneinfo.ZoneInfo('UTC'))
    # Convert from UTC to local timezone
    local_ts = ts.astimezone(LOCAL_TIMEZONE)
    return local_ts.isoformat()

class SensorInfo(BaseModel):
    sensor_id: str
    domain: str
    friendly_name: Optional[str] = None
    device_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    last_seen: Optional[datetime] = None

class SensorReading(BaseModel):
    timestamp: datetime
    sensor_id: str
    value_numeric: float = None
    value_text: str = None
    value_binary: bool = None
    domain: str
    unit: str = None
    quality: str = "good"

@app.on_event("startup")
async def startup_event():
    """Initialize ScyllaDB connection"""
    global cluster, session
    try:
        cluster = Cluster(
            contact_points=SCYLLA_HOSTS,
            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
            protocol_version=4
        )
        session = cluster.connect(KEYSPACE)
        session.default_consistency_level = ConsistencyLevel.LOCAL_QUORUM
        logger.info(f"Connected to ScyllaDB: {SCYLLA_HOSTS}")
    except Exception as e:
        logger.error(f"Failed to connect to ScyllaDB: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close ScyllaDB connection"""
    if cluster:
        cluster.shutdown()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Simple query to test connection
        result = session.execute("SELECT sensor_id FROM sensors LIMIT 1")
        return {"status": "healthy", "scylla": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")

@app.get("/sensors", response_model=List[SensorInfo])
async def get_sensors():
    """Get all sensors for the current tenant/site"""
    try:
        query = """
            SELECT sensor_id, domain, friendly_name, device_class, 
                   unit_of_measurement, last_seen
            FROM sensors 
            WHERE tenant = %s AND site = %s
        """
        result = session.execute(query, (TENANT, SITE))
        
        sensors = []
        for row in result:
            sensors.append(SensorInfo(
                sensor_id=row.sensor_id,
                domain=row.domain,
                friendly_name=row.friendly_name,
                device_class=row.device_class,
                unit_of_measurement=row.unit_of_measurement,
                last_seen=row.last_seen
            ))
        
        return sensors
    except Exception as e:
        logger.error(f"Failed to get sensors: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/sensors/{sensor_id}/latest")
async def get_sensor_latest(sensor_id: str):
    """Get latest reading for a specific sensor"""
    try:
        # Get today's data
        today = date.today()
        query = """
            SELECT ts, sensor_id, value_numeric, value_text, value_binary,
                   domain, unit, quality
            FROM sensor_readings
            WHERE tenant = %s AND site = %s AND day_bucket = %s
              AND sensor_id = %s
            ORDER BY ts DESC
            LIMIT 1
        """
        result = session.execute(query, (TENANT, SITE, today, sensor_id))
        
        row = result.one()
        if not row:
            raise HTTPException(status_code=404, detail=f"No data found for sensor {sensor_id}")
        
        return {
            "timestamp": format_timestamp(row.ts),
            "sensor_id": row.sensor_id,
            "value_numeric": row.value_numeric,
            "value_text": row.value_text,
            "value_binary": row.value_binary,
            "domain": row.domain,
            "unit": row.unit,
            "quality": row.quality
        }
    except Exception as e:
        logger.error(f"Failed to get latest reading for {sensor_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/data/count")
async def get_data_count():
    """Get count of records in the database"""
    try:
        # Simple count query
        query = "SELECT COUNT(*) as total FROM sensor_readings WHERE tenant = %s AND site = %s ALLOW FILTERING"
        result = session.execute(query, (TENANT, SITE))
        row = result.one()
        
        return {"total_readings": row.total if row else 0}
    except Exception as e:
        logger.error(f"Failed to count data: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)