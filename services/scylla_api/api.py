"""
Enhanced Gauge API with ScyllaDB Backend

Provides unified REST API for IoT sensor data with:
- Fast time-series queries using ScyllaDB
- Unified sensor data model (numeric, binary, text)
- Real-time and historical data endpoints
- Aggregated statistics
- Multi-sensor site views
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta, timezone, date
from pydantic import BaseModel
from dataclasses import dataclass
import os
import logging
from uuid import UUID

from cassandra.cluster import Cluster
from cassandra.policies import TokenAwarePolicy, DCAwareRoundRobinPolicy
from cassandra import ConsistencyLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gauge IoT API",
    description="Unified REST API for IoT sensor data powered by ScyllaDB",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API responses
class SensorInfo(BaseModel):
    sensor_id: str
    domain: str
    friendly_name: Optional[str]
    device_class: Optional[str]
    unit_of_measurement: Optional[str]
    last_seen: Optional[datetime]
    attributes: Dict[str, str] = {}

class SensorReading(BaseModel):
    timestamp: datetime
    sensor_id: str
    value_numeric: Optional[float]
    value_text: Optional[str]
    value_binary: Optional[bool]
    domain: str
    unit: Optional[str]
    quality: str
    attributes: Dict[str, str] = {}

class SensorEvent(BaseModel):
    timestamp: datetime
    sensor_id: str
    event_type: str
    old_value: Optional[str]
    new_value: Optional[str]
    severity: str
    message: str
    details: Dict[str, str] = {}

class SensorStats(BaseModel):
    sensor_id: str
    hour_bucket: datetime
    sample_count: int
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    true_count: Optional[int]
    false_count: Optional[int]
    change_count: Optional[int]

# Global ScyllaDB connection
scylla_session = None
prepared_statements = {}

def get_scylla_session():
    """Get or create ScyllaDB session"""
    global scylla_session, prepared_statements
    
    if scylla_session is None:
        hosts = os.getenv('SCYLLA_HOSTS', 'scylla-node1').split(',')
        keyspace = os.getenv('SCYLLA_KEYSPACE', 'iot')
        
        cluster = Cluster(
            contact_points=hosts,
            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
            protocol_version=4
        )
        scylla_session = cluster.connect(keyspace)
        scylla_session.default_consistency_level = ConsistencyLevel.LOCAL_QUORUM
        
        # Prepare common statements
        prepared_statements = {
            'get_sensors': scylla_session.prepare("""
                SELECT sensor_id, domain, friendly_name, device_class, 
                       unit_of_measurement, last_seen, attributes
                FROM sensors 
                WHERE tenant = ? AND site = ?
            """),
            
            'get_sensor_latest': scylla_session.prepare("""
                SELECT ts, sensor_id, value_numeric, value_text, value_binary,
                       domain, unit, quality, attributes
                FROM sensor_readings
                WHERE tenant = ? AND site = ? AND day_bucket = ?
                  AND sensor_id = ?
                ORDER BY ts DESC
                LIMIT 1
            """),
            
            'get_sensor_history': scylla_session.prepare("""
                SELECT ts, sensor_id, value_numeric, value_text, value_binary,
                       domain, unit, quality, attributes
                FROM sensor_readings
                WHERE tenant = ? AND site = ? AND day_bucket = ?
                  AND sensor_id = ? AND ts >= ?
                ORDER BY ts DESC
                LIMIT ?
            """),
            
            'get_domain_sensors': scylla_session.prepare("""
                SELECT sensor_id, domain, friendly_name, device_class, 
                       unit_of_measurement, last_seen, attributes
                FROM sensors
                WHERE tenant = ? AND site = ? AND domain = ?
            """),
            
            'get_sensor_events': scylla_session.prepare("""
                SELECT ts, sensor_id, event_type, old_value, new_value,
                       severity, message, details
                FROM sensor_events
                WHERE tenant = ? AND site = ? AND day_bucket = ?
                  AND sensor_id = ? AND ts >= ?
                ORDER BY ts DESC
                LIMIT ?
            """),
            
            'get_hourly_stats': scylla_session.prepare("""
                SELECT sensor_id, hour_bucket, sample_count, min_value, max_value,
                       avg_value, true_count, false_count, change_count
                FROM sensor_stats_hourly
                WHERE tenant = ? AND site = ? AND sensor_id = ?
                ORDER BY hour_bucket DESC
                LIMIT 100 ALLOW FILTERING
            """)
        }
        
        logger.info(f"Connected to ScyllaDB: {hosts}")
    
    return scylla_session

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    get_scylla_session()

@app.get("/", response_model=Dict[str, str])
async def root():
    """API information"""
    return {
        "message": "Gauge IoT API powered by ScyllaDB",
        "version": "2.0.0",
        "backend": "ScyllaDB"
    }

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check with ScyllaDB connectivity"""
    try:
        session = get_scylla_session()
        # Simple query to check connectivity
        session.execute("SELECT release_version FROM system.local")
        return {"status": "healthy", "database": "ScyllaDB connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}

@app.get("/sensors", response_model=List[SensorInfo])
async def list_sensors(
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """List all sensors with metadata"""
    try:
        session = get_scylla_session()
        rows = session.execute(prepared_statements['get_sensors'], (tenant, site))
        
        sensors = []
        for row in rows:
            sensors.append(SensorInfo(
                sensor_id=row.sensor_id,
                domain=row.domain,
                friendly_name=row.friendly_name,
                device_class=row.device_class,
                unit_of_measurement=row.unit_of_measurement,
                last_seen=row.last_seen,
                attributes=row.attributes or {}
            ))
        
        return sensors
    except Exception as e:
        logger.error(f"Error listing sensors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/{sensor_id}/latest", response_model=SensorReading)
async def get_sensor_latest(
    sensor_id: str = Path(..., description="Sensor ID"),
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """Get latest reading for a specific sensor"""
    try:
        session = get_scylla_session()
        
        # Look back 7 days for the latest reading
        start_day = (datetime.now(timezone.utc) - timedelta(days=7)).date()
        
        rows = session.execute(
            prepared_statements['get_sensor_latest'], 
            (tenant, site, start_day, sensor_id)
        )
        
        row = rows.one() if rows else None
        if not row:
            raise HTTPException(status_code=404, detail="Sensor not found or no recent data")
        
        return SensorReading(
            timestamp=row.ts,
            sensor_id=row.sensor_id,
            value_numeric=row.value_numeric,
            value_text=row.value_text,
            value_binary=row.value_binary,
            domain=row.domain,
            unit=row.unit,
            quality=row.quality,
            attributes=row.attributes or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/{sensor_id}/history", response_model=List[SensorReading])
async def get_sensor_history(
    sensor_id: str = Path(..., description="Sensor ID"),
    hours: int = Query(24, description="Number of hours to look back"),
    limit: int = Query(1000, description="Maximum number of records"),
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """Get historical data for a specific sensor"""
    try:
        session = get_scylla_session()
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)
        
        # Calculate day range for partition keys
        start_day = start_time.date()
        end_day = now.date()
        
        rows = session.execute(
            prepared_statements['get_sensor_history'],
            (tenant, site, start_day, end_day, sensor_id, start_time, limit)
        )
        
        readings = []
        for row in rows:
            readings.append(SensorReading(
                timestamp=row.ts,
                sensor_id=row.sensor_id,
                value_numeric=row.value_numeric,
                value_text=row.value_text,
                value_binary=row.value_binary,
                domain=row.domain,
                unit=row.unit,
                quality=row.quality,
                attributes=row.attributes or {}
            ))
        
        return readings
    except Exception as e:
        logger.error(f"Error getting sensor history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/domain/{domain}", response_model=List[SensorReading])
async def get_sensors_by_domain(
    domain: str = Path(..., description="Sensor domain (sensor, binary_sensor)"),
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """Get latest readings for all sensors in a domain"""
    try:
        session = get_scylla_session()
        
        rows = session.execute(
            prepared_statements['get_domain_sensors'],
            (tenant, site, domain)
        )
        
        readings = []
        for row in rows:
            readings.append(SensorReading(
                timestamp=row.ts,
                sensor_id=row.sensor_id,
                value_numeric=row.value_numeric,
                value_text=row.value_text,
                value_binary=row.value_binary,
                domain=row.domain,
                unit=row.unit,
                quality=row.quality,
                attributes=row.attributes or {}
            ))
        
        return readings
    except Exception as e:
        logger.error(f"Error getting sensors by domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/{sensor_id}/events", response_model=List[SensorEvent])
async def get_sensor_events(
    sensor_id: str = Path(..., description="Sensor ID"),
    hours: int = Query(24, description="Number of hours to look back"),
    limit: int = Query(100, description="Maximum number of events"),
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """Get events for a specific sensor"""
    try:
        session = get_scylla_session()
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)
        start_day = start_time.date()
        end_day = now.date()
        
        rows = session.execute(
            prepared_statements['get_sensor_events'],
            (tenant, site, start_day, end_day, sensor_id, start_time, limit)
        )
        
        events = []
        for row in rows:
            events.append(SensorEvent(
                timestamp=row.ts,
                sensor_id=row.sensor_id,
                event_type=row.event_type,
                old_value=row.old_value,
                new_value=row.new_value,
                severity=row.severity,
                message=row.message,
                details=row.details or {}
            ))
        
        return events
    except Exception as e:
        logger.error(f"Error getting sensor events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/{sensor_id}/stats/hourly", response_model=List[SensorStats])
async def get_hourly_stats(
    sensor_id: str = Path(..., description="Sensor ID"),
    hours: int = Query(24, description="Number of hours to look back"),
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """Get hourly aggregated statistics"""
    try:
        session = get_scylla_session()
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)
        
        # Round to hour boundaries
        start_hour = start_time.replace(minute=0, second=0, microsecond=0)
        end_hour = now.replace(minute=0, second=0, microsecond=0)
        
        rows = session.execute(
            prepared_statements['get_hourly_stats'],
            (tenant, site, sensor_id, start_hour, end_hour)
        )
        
        stats = []
        for row in rows:
            stats.append(SensorStats(
                sensor_id=row.sensor_id,
                hour_bucket=row.hour_bucket,
                sample_count=row.sample_count or 0,
                min_value=row.min_value,
                max_value=row.max_value,
                avg_value=row.avg_value,
                true_count=row.true_count,
                false_count=row.false_count,
                change_count=row.change_count
            ))
        
        return stats
    except Exception as e:
        logger.error(f"Error getting hourly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/export", response_model=Dict[str, Any])
async def export_data(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    hours: int = Query(24, description="Number of hours to look back"),
    tenant: str = Query("gauge", description="Tenant ID"),
    site: str = Query("recife", description="Site ID")
):
    """Export sensor data with optional filters"""
    try:
        session = get_scylla_session()
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)
        start_day = start_time.date()
        end_day = now.date()
        
        if sensor_id:
            # Export specific sensor
            rows = session.execute(
                prepared_statements['get_sensor_history'],
                (tenant, site, start_day, end_day, sensor_id, start_time, 10000)
            )
        elif domain:
            # Export by domain - need custom query
            query = f"""
                SELECT ts, sensor_id, value_numeric, value_text, value_binary,
                       domain, unit, quality, attributes
                FROM sensor_readings
                WHERE tenant = ? AND site = ? AND day_bucket >= ? AND day_bucket <= ?
                  AND domain = ? AND ts >= ?
                LIMIT 10000
            """
            rows = session.execute(query, (tenant, site, start_day, end_day, domain, start_time))
        else:
            # Export all sensors
            query = f"""
                SELECT ts, sensor_id, value_numeric, value_text, value_binary,
                       domain, unit, quality, attributes
                FROM sensor_readings
                WHERE tenant = ? AND site = ? AND day_bucket >= ? AND day_bucket <= ?
                  AND ts >= ?
                LIMIT 10000
            """
            rows = session.execute(query, (tenant, site, start_day, end_day, start_time))
        
        data = []
        for row in rows:
            data.append({
                "timestamp": row.ts.isoformat(),
                "sensor_id": row.sensor_id,
                "value_numeric": row.value_numeric,
                "value_text": row.value_text,
                "value_binary": row.value_binary,
                "domain": row.domain,
                "unit": row.unit,
                "quality": row.quality,
                "attributes": row.attributes or {}
            })
        
        return {
            "export_time": now.isoformat(),
            "filters": {
                "domain": domain,
                "sensor_id": sensor_id,
                "hours": hours
            },
            "record_count": len(data),
            "data": data
        }
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)