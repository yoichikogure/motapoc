CREATE INDEX IF NOT EXISTS idx_import_job_created_at ON admin.import_job(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_import_error_job ON admin.import_error(import_job_id);
CREATE INDEX IF NOT EXISTS idx_visitors_month ON core.fact_visitors_monthly(month_index);
CREATE INDEX IF NOT EXISTS idx_rooms_beds_month ON core.fact_rooms_beds_monthly(month_index);
CREATE INDEX IF NOT EXISTS idx_occ_month ON core.fact_hotel_occupancy_monthly(month_index);
CREATE INDEX IF NOT EXISTS idx_forecast_run ON forecast.region_demand_forecast(model_run_id, governorate_id, forecast_month);
CREATE INDEX IF NOT EXISTS idx_tourism_site_governorate ON core.tourism_site(governorate_id);
