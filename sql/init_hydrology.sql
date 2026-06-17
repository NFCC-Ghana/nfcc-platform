-- ================================================================
-- CIVICFLOOD AI - HYDROLOGICAL INTELLIGENCE DATABASE SCHEMA
-- PostgreSQL + PostGIS
-- ================================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ================================================================
-- 1. HISTORICAL RAINFALL
-- ================================================================
CREATE TABLE IF NOT EXISTS historical_rainfall (
    id SERIAL PRIMARY KEY,
    district VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    rainfall_mm DECIMAL(8,2),
    rain_3d DECIMAL(8,2),
    rain_7d DECIMAL(8,2),
    rain_14d DECIMAL(8,2),
    rain_30d DECIMAL(8,2),
    rain_90d DECIMAL(8,2),
    percentile_rank DECIMAL(5,2),
    seasonal_anomaly DECIMAL(8,2),
    recurrence_years DECIMAL(5,2),
    is_extreme BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(district, date)
);

CREATE INDEX idx_historical_rainfall_district ON historical_rainfall(district);
CREATE INDEX idx_historical_rainfall_date ON historical_rainfall(date);

-- ================================================================
-- 2. RIVER GAUGE DATA
-- ================================================================
CREATE TABLE IF NOT EXISTS river_gauges (
    id SERIAL PRIMARY KEY,
    gauge_id VARCHAR(50) UNIQUE NOT NULL,
    river VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    lat DECIMAL(10,6),
    lon DECIMAL(10,6),
    warning_level_m DECIMAL(6,2),
    danger_level_m DECIMAL(6,2),
    flood_stage_m DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS river_measurements (
    id SERIAL PRIMARY KEY,
    gauge_id VARCHAR(50) REFERENCES river_gauges(gauge_id),
    measurement_time TIMESTAMP NOT NULL,
    water_level_m DECIMAL(6,2),
    flow_rate_m3s DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gauge_id, measurement_time)
);

-- ================================================================
-- 3. RESERVOIR/DAM DATA
-- ================================================================
CREATE TABLE IF NOT EXISTS dams (
    id SERIAL PRIMARY KEY,
    dam_id VARCHAR(50) UNIQUE NOT NULL,
    dam_name VARCHAR(100) NOT NULL,
    river VARCHAR(100),
    region VARCHAR(50),
    capacity_mw INTEGER,
    capacity_mcm DECIMAL(10,2),
    lat DECIMAL(10,6),
    lon DECIMAL(10,6),
    warning_level_pct DECIMAL(5,2),
    danger_level_pct DECIMAL(5,2),
    downstream_communities TEXT[],
    operator VARCHAR(100),
    dam_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- 4. COMMUNITY REPORTS
-- ================================================================
CREATE TABLE IF NOT EXISTS community_reports (
    id SERIAL PRIMARY KEY,
    district VARCHAR(100) NOT NULL,
    community VARCHAR(100) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    description TEXT,
    flood_depth_m DECIMAL(5,2),
    photo_url TEXT,
    reporter_name VARCHAR(100),
    reporter_phone VARCHAR(20),
    report_time TIMESTAMP NOT NULL,
    validated BOOLEAN DEFAULT FALSE,
    validation_confidence DECIMAL(5,2) DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- 5. NATIONAL FLOOD EVENTS
-- ================================================================
CREATE TABLE IF NOT EXISTS flood_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    event_date DATE NOT NULL,
    cause VARCHAR(100),
    districts TEXT[],
    rainfall_mm DECIMAL(8,2),
    river_level_m DECIMAL(6,2),
    dam_release VARCHAR(100),
    area_km2 DECIMAL(10,2),
    population_affected INTEGER,
    displaced INTEGER,
    fatalities INTEGER,
    severity VARCHAR(20),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- INITIAL DATA
-- ================================================================
INSERT INTO river_gauges (gauge_id, river, location, region, lat, lon, warning_level_m, danger_level_m, flood_stage_m)
VALUES
    ('odaw_accra', 'Odaw', 'Accra', 'Greater Accra', 5.550, -0.200, 2.0, 2.8, 3.2),
    ('densu_weija', 'Densu', 'Weija', 'Greater Accra', 5.550, -0.333, 2.5, 3.5, 4.0)
ON CONFLICT (gauge_id) DO NOTHING;
