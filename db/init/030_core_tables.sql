CREATE TABLE IF NOT EXISTS core.fact_visitors_monthly (
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    month_index DATE NOT NULL,
    total_visitors NUMERIC(14,2) NOT NULL,
    PRIMARY KEY (governorate_id, month_index)
);

CREATE TABLE IF NOT EXISTS core.fact_rooms_beds_monthly (
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    month_index DATE NOT NULL,
    total_rooms NUMERIC(14,2) NOT NULL,
    total_beds NUMERIC(14,2) NOT NULL,
    PRIMARY KEY (governorate_id, month_index)
);

CREATE TABLE IF NOT EXISTS core.fact_hotel_occupancy_monthly (
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    month_index DATE NOT NULL,
    average_occupancy_rate NUMERIC(8,4) NOT NULL,
    PRIMARY KEY (governorate_id, month_index)
);

CREATE TABLE IF NOT EXISTS core.tourism_site (
    tourism_site_id BIGSERIAL PRIMARY KEY,
    site_name_en TEXT NOT NULL,
    site_category TEXT,
    governorate_id INTEGER REFERENCES core.governorate(governorate_id),
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    site_geom geometry(Point, 4326)
);

CREATE TABLE IF NOT EXISTS gis.admin_boundary (
    governorate_id INTEGER PRIMARY KEY REFERENCES core.governorate(governorate_id),
    governorate_code TEXT NOT NULL,
    governorate_name_en TEXT NOT NULL,
    boundary_geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics.region_indicator_monthly (
    indicator_id BIGSERIAL PRIMARY KEY,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    month_index DATE NOT NULL,
    visitors_per_1000_beds NUMERIC(14,4),
    occupancy_pressure_index NUMERIC(14,4),
    growth_pressure_index NUMERIC(14,4),
    capacity_adequacy_index NUMERIC(14,4),
    forecast_pressure_index NUMERIC(14,4),
    UNIQUE (governorate_id, month_index)
);

CREATE TABLE IF NOT EXISTS analytics.region_classification_monthly (
    classification_id BIGSERIAL PRIMARY KEY,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    month_index DATE NOT NULL,
    capacity_classification TEXT NOT NULL,
    UNIQUE (governorate_id, month_index)
);

CREATE TABLE IF NOT EXISTS analytics.region_priority_score_monthly (
    score_id BIGSERIAL PRIMARY KEY,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    month_index DATE NOT NULL,
    priority_score NUMERIC(10,2) NOT NULL,
    justification_text TEXT,
    occupancy_component NUMERIC(10,2),
    growth_component NUMERIC(10,2),
    visitor_bed_component NUMERIC(10,2),
    forecast_component NUMERIC(10,2),
    UNIQUE (governorate_id, month_index)
);

CREATE TABLE IF NOT EXISTS forecast.model_run (
    model_run_id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    forecast_target TEXT NOT NULL,
    horizon_months INTEGER NOT NULL,
    status TEXT NOT NULL,
    run_parameters_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecast.region_demand_forecast (
    forecast_id BIGSERIAL PRIMARY KEY,
    model_run_id BIGINT NOT NULL REFERENCES forecast.model_run(model_run_id) ON DELETE CASCADE,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    forecast_month DATE NOT NULL,
    forecast_value NUMERIC(14,2) NOT NULL,
    lower_bound NUMERIC(14,2),
    upper_bound NUMERIC(14,2)
);

CREATE TABLE IF NOT EXISTS forecast.backtest_metric (
    metric_id BIGSERIAL PRIMARY KEY,
    model_run_id BIGINT NOT NULL REFERENCES forecast.model_run(model_run_id) ON DELETE CASCADE,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    mae NUMERIC(14,4),
    rmse NUMERIC(14,4),
    mape NUMERIC(14,4),
    reliability_label TEXT
);

CREATE TABLE IF NOT EXISTS simulation.scenario_run (
    scenario_run_id BIGSERIAL PRIMARY KEY,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    target_month DATE NOT NULL,
    scenario_type TEXT NOT NULL,
    additional_beds INTEGER NOT NULL DEFAULT 0,
    additional_rooms INTEGER NOT NULL DEFAULT 0,
    induced_demand_ratio NUMERIC(10,4) NOT NULL DEFAULT 0,
    based_on_model_run_id BIGINT REFERENCES forecast.model_run(model_run_id),
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation.region_scenario_result (
    result_id BIGSERIAL PRIMARY KEY,
    scenario_run_id BIGINT NOT NULL REFERENCES simulation.scenario_run(scenario_run_id) ON DELETE CASCADE,
    governorate_id INTEGER NOT NULL REFERENCES core.governorate(governorate_id),
    target_month DATE NOT NULL,
    baseline_demand NUMERIC(14,2),
    scenario_demand NUMERIC(14,2),
    demand_delta NUMERIC(14,2),
    baseline_beds NUMERIC(14,2),
    scenario_beds NUMERIC(14,2),
    beds_delta NUMERIC(14,2),
    priority_score_before NUMERIC(10,2),
    priority_score_after NUMERIC(10,2),
    capacity_status_before TEXT,
    capacity_status_after TEXT,
    visitors_per_1000_beds_before NUMERIC(14,4),
    visitors_per_1000_beds_after NUMERIC(14,4),
    recommendation_text TEXT
);
