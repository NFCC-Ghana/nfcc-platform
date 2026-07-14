-- ================================================================
-- CIVICFLOOD AI - NATIONAL FLOOD INTELLIGENCE DATABASE
-- PostgreSQL + PostGIS Schema
-- Version: 2.0 (Enhanced)
-- ================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ================================================================
-- 1. DISTRICTS
-- ================================================================
CREATE TABLE IF NOT EXISTS districts (
    id SERIAL PRIMARY KEY,
    district_name VARCHAR(100) UNIQUE NOT NULL,
    region VARCHAR(50) NOT NULL,
    population INTEGER,
    area_km2 DECIMAL(10,2),
    geometry GEOMETRY(POLYGON, 4326),
    centroid GEOMETRY(POINT, 4326),
    vulnerability_score DECIMAL(5,2) DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_districts_region ON districts(region);
CREATE INDEX idx_districts_geometry ON districts USING GIST(geometry);

-- ================================================================
-- 2. HISTORICAL RAINFALL
-- ================================================================
CREATE TABLE IF NOT EXISTS historical_rainfall (
    id SERIAL PRIMARY KEY,
    district_id INTEGER REFERENCES districts(id),
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
    UNIQUE(district_id, date)
);

CREATE INDEX idx_historical_rainfall_district ON historical_rainfall(district_id);
CREATE INDEX idx_historical_rainfall_date ON historical_rainfall(date);

-- ================================================================
-- 3. RIVER GAUGES
-- ================================================================
CREATE TABLE IF NOT EXISTS river_gauges (
    id SERIAL PRIMARY KEY,
    gauge_id VARCHAR(50) UNIQUE NOT NULL,
    river VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    district_id INTEGER REFERENCES districts(id),
    lat DECIMAL(10,6),
    lon DECIMAL(10,6),
    warning_level_m DECIMAL(6,2),
    danger_level_m DECIMAL(6,2),
    flood_stage_m DECIMAL(6,2),
    data_source VARCHAR(50) DEFAULT 'simulated',
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_river_gauges_district ON river_gauges(district_id);

CREATE TABLE IF NOT EXISTS river_measurements (
    id SERIAL PRIMARY KEY,
    gauge_id VARCHAR(50) REFERENCES river_gauges(gauge_id),
    measurement_time TIMESTAMP NOT NULL,
    water_level_m DECIMAL(6,2),
    flow_rate_m3s DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gauge_id, measurement_time)
);

CREATE INDEX idx_river_measurements_gauge ON river_measurements(gauge_id);
CREATE INDEX idx_river_measurements_time ON river_measurements(measurement_time);

-- ================================================================
-- 4. DAMS AND RESERVOIRS
-- ================================================================
CREATE TABLE IF NOT EXISTS dams (
    id SERIAL PRIMARY KEY,
    dam_id VARCHAR(50) UNIQUE NOT NULL,
    dam_name VARCHAR(100) NOT NULL,
    river VARCHAR(100),
    region VARCHAR(50),
    district_id INTEGER REFERENCES districts(id),
    capacity_mw INTEGER,
    capacity_mcm DECIMAL(10,2),
    lat DECIMAL(10,6),
    lon DECIMAL(10,6),
    warning_level_pct DECIMAL(5,2),
    danger_level_pct DECIMAL(5,2),
    downstream_communities TEXT[],
    operator VARCHAR(100),
    dam_type VARCHAR(50),
    data_source VARCHAR(50) DEFAULT 'simulated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dams_region ON dams(region);

CREATE TABLE IF NOT EXISTS reservoir_levels (
    id SERIAL PRIMARY KEY,
    dam_id VARCHAR(50) REFERENCES dams(dam_id),
    measurement_time TIMESTAMP NOT NULL,
    level_mcm DECIMAL(10,2),
    pct_full DECIMAL(5,2),
    inflow_mcm DECIMAL(10,2),
    outflow_mcm DECIMAL(10,2),
    spillway_open BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dam_id, measurement_time)
);

CREATE INDEX idx_reservoir_levels_dam ON reservoir_levels(dam_id);

-- ================================================================
-- 5. SOIL MOISTURE
-- ================================================================
CREATE TABLE IF NOT EXISTS soil_moisture (
    id SERIAL PRIMARY KEY,
    district_id INTEGER REFERENCES districts(id),
    measurement_time TIMESTAMP NOT NULL,
    volumetric_water DECIMAL(6,4),
    saturation_index DECIMAL(5,2),
    runoff_potential VARCHAR(20),
    flash_flood_risk VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(district_id, measurement_time)
);

CREATE INDEX idx_soil_moisture_district ON soil_moisture(district_id);

-- ================================================================
-- 6. WEATHER FORECASTS
-- ================================================================
CREATE TABLE IF NOT EXISTS weather_forecasts (
    id SERIAL PRIMARY KEY,
    district_id INTEGER REFERENCES districts(id),
    forecast_time TIMESTAMP NOT NULL,
    forecast_24h_mm DECIMAL(8,2),
    forecast_48h_mm DECIMAL(8,2),
    forecast_72h_mm DECIMAL(8,2),
    source VARCHAR(50) DEFAULT 'open-meteo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(district_id, forecast_time)
);

CREATE INDEX idx_weather_forecasts_district ON weather_forecasts(district_id);
CREATE INDEX idx_weather_forecasts_time ON weather_forecasts(forecast_time);

-- ================================================================
-- 7. COMMUNITY REPORTS
-- ================================================================
CREATE TABLE IF NOT EXISTS community_reports (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) UNIQUE NOT NULL,
    district_id INTEGER REFERENCES districts(id),
    community VARCHAR(100) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    description TEXT,
    flood_depth_m DECIMAL(5,2),
    photo_url TEXT,
    reporter_name VARCHAR(100),
    reporter_phone VARCHAR(20),
    reporter_email VARCHAR(100),
    report_time TIMESTAMP NOT NULL,
    validated BOOLEAN DEFAULT FALSE,
    validation_confidence DECIMAL(5,2) DEFAULT 0.5,
    trusted_score DECIMAL(5,2) DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_community_reports_district ON community_reports(district_id);
CREATE INDEX idx_community_reports_time ON community_reports(report_time);

-- ================================================================
-- 8. FLOOD EVENTS
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
    damage_estimate_ghs DECIMAL(15,2),
    severity VARCHAR(20),
    description TEXT,
    source VARCHAR(100),
    coordinates JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_flood_events_date ON flood_events(event_date);
CREATE INDEX idx_flood_events_district ON flood_events USING GIN(districts);

-- ================================================================
-- 9. SUBSCRIPTIONS
-- ================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    whatsapp_verified BOOLEAN DEFAULT FALSE,
    sms_verified BOOLEAN DEFAULT FALSE,
    email VARCHAR(100),
    districts TEXT,
    alert_level VARCHAR(20) DEFAULT 'MODERATE',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_phone ON subscriptions(phone_number);

-- ================================================================
-- 10. ALERT HISTORY
-- ================================================================
CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    district_id INTEGER REFERENCES districts(id),
    risk_score DECIMAL(5,2),
    risk_tier VARCHAR(20),
    alert_level VARCHAR(20),
    message TEXT,
    channels TEXT[],
    sent_to TEXT[],
    sent_time TIMESTAMP NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alert_history_district ON alert_history(district_id);
CREATE INDEX idx_alert_history_time ON alert_history(sent_time);

-- ================================================================
-- INITIAL DATA - DISTRICTS
-- ================================================================
INSERT INTO districts (district_name, region, population, area_km2, vulnerability_score) VALUES
    ('Accra Central', 'Greater Accra', 187928, 45.5, 0.92),
    ('Accra West', 'Greater Accra', 203461, 52.3, 0.88),
    ('Accra East', 'Greater Accra', 142587, 38.2, 0.70),
    ('Tema', 'Greater Accra', 198742, 38.7, 0.78),
    ('Kumasi', 'Ashanti', 443981, 98.2, 0.45),
    ('Tamale', 'Northern', 371578, 67.4, 0.55)
ON CONFLICT (district_name) DO NOTHING;

-- ================================================================
-- INITIAL DATA - RIVER GAUGES
-- ================================================================
INSERT INTO river_gauges (gauge_id, river, location, lat, lon, warning_level_m, danger_level_m, flood_stage_m, data_source) VALUES
    ('odaw_accra', 'Odaw', 'Accra', 5.550, -0.200, 2.0, 2.8, 3.2, 'simulated'),
    ('densu_weija', 'Densu', 'Weija', 5.550, -0.333, 2.5, 3.5, 4.0, 'simulated'),
    ('volta_senchi', 'Volta', 'Senchi', 6.033, -0.133, 3.5, 4.5, 5.0, 'simulated')
ON CONFLICT (gauge_id) DO NOTHING;

-- ================================================================
-- INITIAL DATA - DAMS
-- ================================================================
INSERT INTO dams (dam_id, dam_name, river, region, capacity_mw, capacity_mcm, lat, lon, warning_level_pct, danger_level_pct, downstream_communities, operator, dam_type, data_source) VALUES
    ('akosombo', 'Akosombo Dam', 'Volta', 'Eastern', 1020, 148000, 6.300, 0.050, 85, 92, ARRAY['Kpong', 'Akuse', 'Ada', 'Tema'], 'VRA', 'hydroelectric', 'simulated'),
    ('kpong', 'Kpong Dam', 'Volta', 'Greater Accra', 160, 7000, 6.133, -0.067, 80, 88, ARRAY['Kpong', 'Akuse', 'Ada'], 'VRA', 'hydroelectric', 'simulated'),
    ('bui', 'Bui Dam', 'Black Volta', 'Bono East', 400, 12500, 8.283, -2.250, 80, 88, ARRAY['Bui', 'Nkwanta', 'Kintampo'], 'BPA', 'hydroelectric', 'simulated')
ON CONFLICT (dam_id) DO NOTHING;
