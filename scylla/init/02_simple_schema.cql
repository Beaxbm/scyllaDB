-- Simplified IoT Schema for ScyllaDB
-- Remove TTL and complex compaction for initial setup

-- Create keyspace
CREATE KEYSPACE IF NOT EXISTS iot
WITH replication = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

USE iot;

-- Sensor metadata table
CREATE TABLE IF NOT EXISTS sensors (
  tenant text,
  site text,
  sensor_id text,
  domain text,
  device_id text,
  friendly_name text,
  unit_of_measurement text,
  device_class text,
  state_class text,
  entity_category text,
  created_at timestamp,
  last_seen timestamp,
  attributes map<text, text>,
  config map<text, text>,
  PRIMARY KEY ((tenant, site), domain, sensor_id)
) WITH comment = 'Sensor metadata and configuration';

-- Main sensor data table
CREATE TABLE IF NOT EXISTS sensor_readings (
  tenant text,
  site text,
  day_bucket date,
  sensor_id text,
  ts timestamp,
  ts_uuid timeuuid,
  
  value_numeric double,
  value_text text,
  value_binary boolean,
  
  domain text,
  unit text,
  quality text,
  attributes map<text, text>,
  
  PRIMARY KEY ((tenant, site, day_bucket, sensor_id), ts, ts_uuid)
) WITH CLUSTERING ORDER BY (ts DESC, ts_uuid DESC)
  AND comment = 'Unified time-series sensor data';

-- Events table
CREATE TABLE IF NOT EXISTS sensor_events (
  tenant text,
  site text,
  day_bucket date,
  sensor_id text,
  ts timestamp,
  ts_uuid timeuuid,
  
  event_type text,
  old_value text,
  new_value text,
  severity text,
  message text,
  details map<text, text>,
  
  PRIMARY KEY ((tenant, site, day_bucket, sensor_id), ts, ts_uuid)
) WITH CLUSTERING ORDER BY (ts DESC, ts_uuid DESC)
  AND comment = 'Sensor state changes and alerts';

-- Hourly statistics table
CREATE TABLE IF NOT EXISTS sensor_stats_hourly (
  tenant text,
  site text,
  sensor_id text,
  hour_bucket timestamp,
  
  sample_count bigint,
  min_value double,
  max_value double,
  avg_value double,
  sum_value double,
  
  true_count bigint,
  false_count bigint,
  change_count bigint,
  
  good_count bigint,
  stale_count bigint,
  error_count bigint,
  
  PRIMARY KEY ((tenant, site, sensor_id), hour_bucket)
) WITH CLUSTERING ORDER BY (hour_bucket DESC)
  AND comment = 'Hourly statistics for dashboard performance';

-- Initial system entry
INSERT INTO sensors (tenant, site, sensor_id, domain, friendly_name, created_at) 
VALUES ('gauge', 'recife', '_system', 'system', 'System Status', toTimestamp(now()));