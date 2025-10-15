-- Gauge IoT Keyspace & Tables for ScyllaDB
-- Optimized for Home Assistant sensor data with unified schema

-- Create keyspace
CREATE KEYSPACE IF NOT EXISTS iot
WITH replication = {
  'class': 'NetworkTopologyStrategy',
  'datacenter1': 1  -- Single DC for dev, use 3+ for production
};

-- Sensor metadata (one row per sensor)
-- Stores sensor configuration and discovery info from Home Assistant
CREATE TABLE IF NOT EXISTS iot.sensors (
  tenant text,              -- 'gauge' 
  site text,               -- 'recife'
  sensor_id text,          -- 'temperature_01', 'porta_entrada_da_sala', etc.
  domain text,             -- 'sensor', 'binary_sensor'
  device_id text,          -- Home Assistant device ID
  friendly_name text,      -- 'Living Room Temperature'
  unit_of_measurement text, -- '°C', '%', 'lx', 'W', etc.
  device_class text,       -- 'temperature', 'humidity', 'door', 'motion'
  state_class text,        -- 'measurement', 'total_increasing'
  entity_category text,    -- 'diagnostic', 'config'
  created_at timestamp,    -- First discovery time
  last_seen timestamp,     -- Last data received
  attributes map<text, text>, -- Additional HA attributes as key-value
  config map<text, text>,     -- Custom configuration
  PRIMARY KEY ((tenant, site), domain, sensor_id)
) WITH comment = 'Sensor metadata and configuration from Home Assistant';

-- Unified time-series data for ALL sensor types
-- Partition by tenant/site/day/sensor for optimal performance
CREATE TABLE IF NOT EXISTS iot.sensor_readings (
  tenant text,
  site text,
  day_bucket date,         -- YYYY-MM-DD for daily partitions
  sensor_id text,
  ts timestamp,            -- Event timestamp
  ts_uuid timeuuid,        -- For ordering and deduplication
  
  -- Unified value storage
  value_numeric double,    -- For temperature, humidity, lux, power, battery%
  value_text text,         -- For states like 'on', 'off', 'available', 'unavailable'
  value_binary boolean,    -- For door/motion sensors (true/false)
  
  -- Metadata
  domain text,             -- 'sensor' or 'binary_sensor'
  unit text,               -- '°C', '%', 'lx', etc.
  quality text,            -- 'good', 'stale', 'error', 'unavailable'
  attributes map<text, text>, -- Additional state attributes
  
  PRIMARY KEY ((tenant, site, day_bucket, sensor_id), ts, ts_uuid)
) WITH CLUSTERING ORDER BY (ts DESC, ts_uuid DESC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': '1'
  }
  AND default_time_to_live = 2592000  -- 30 days retention
  AND comment = 'Unified time-series data for all sensor types';

-- Events table for significant state changes
CREATE TABLE IF NOT EXISTS iot.sensor_events (
  tenant text,
  site text,
  day_bucket date,
  sensor_id text,
  ts timestamp,
  ts_uuid timeuuid,
  
  event_type text,         -- 'state_change', 'threshold_breach', 'offline', 'online'
  old_value text,          -- Previous value
  new_value text,          -- New value
  severity text,           -- 'info', 'warning', 'critical'
  message text,            -- Human readable message
  details map<text, text>, -- Additional context
  
  PRIMARY KEY ((tenant, site, day_bucket, sensor_id), ts, ts_uuid)
) WITH CLUSTERING ORDER BY (ts DESC, ts_uuid DESC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': '1'
  }
  AND default_time_to_live = 5184000  -- 60 days retention
  AND comment = 'Significant sensor state changes and alerts';

-- Hourly aggregates for fast dashboard queries
CREATE TABLE IF NOT EXISTS iot.sensor_stats_hourly (
  tenant text,
  site text,
  sensor_id text,
  hour_bucket timestamp,   -- Rounded to hour: 2025-10-15T14:00:00Z
  
  -- Statistics for numeric sensors
  sample_count bigint,
  min_value double,
  max_value double,
  avg_value double,
  sum_value double,
  
  -- For binary sensors
  true_count bigint,       -- Number of true/on states
  false_count bigint,      -- Number of false/off states
  change_count bigint,     -- Number of state changes
  
  -- Quality metrics
  good_count bigint,       -- Number of good quality readings
  stale_count bigint,      -- Number of stale readings
  error_count bigint,      -- Number of error readings
  
  PRIMARY KEY ((tenant, site, sensor_id), hour_bucket)
) WITH CLUSTERING ORDER BY (hour_bucket DESC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': '7'
  }
  AND comment = 'Hourly statistics for dashboard performance';

-- Indexes for common query patterns (will be added later)
-- CREATE INDEX IF NOT EXISTS ON iot.sensors (device_class);
-- CREATE INDEX IF NOT EXISTS ON iot.sensor_readings (domain);
-- CREATE INDEX IF NOT EXISTS ON iot.sensor_readings (quality);

-- Initial tenant/site setup
INSERT INTO iot.sensors (tenant, site, sensor_id, domain, friendly_name, created_at) 
VALUES ('gauge', 'recife', '_system', 'system', 'System Status', toTimestamp(now()));