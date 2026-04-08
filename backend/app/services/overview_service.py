from sqlalchemy import text
from sqlalchemy.orm import Session


class OverviewService:
    def get_kpis(self, db: Session):
        sql = text("""
        WITH latest AS (
            SELECT MAX(month_index) AS month_index FROM core.fact_visitors_monthly
        ),
        visitors AS (
            SELECT COALESCE(SUM(total_visitors),0) AS total_visitors
            FROM core.fact_visitors_monthly v JOIN latest l ON v.month_index = l.month_index
        ),
        capacity AS (
            SELECT COALESCE(SUM(total_rooms),0) AS total_rooms,
                   COALESCE(SUM(total_beds),0) AS total_beds
            FROM core.fact_rooms_beds_monthly r JOIN latest l ON r.month_index = l.month_index
        ),
        occ AS (
            SELECT COALESCE(AVG(average_occupancy_rate),0) AS average_occupancy_rate
            FROM core.fact_hotel_occupancy_monthly o JOIN latest l ON o.month_index = l.month_index
        ),
        hp AS (
            SELECT COUNT(*) AS high_priority_zones
            FROM analytics.region_priority_score_monthly p
            JOIN latest l ON p.month_index = l.month_index
            JOIN admin.system_parameter sp ON sp.parameter_key = 'high_priority_threshold'
            WHERE p.priority_score >= CAST(sp.parameter_value AS numeric)
        )
        SELECT
            (SELECT month_index::text FROM latest) AS latest_month,
            visitors.total_visitors,
            capacity.total_rooms,
            capacity.total_beds,
            occ.average_occupancy_rate,
            hp.high_priority_zones
        FROM visitors, capacity, occ, hp
        """)
        return dict(db.execute(sql).mappings().one())

    def get_regions(self, db: Session):
        sql = text("""
        WITH latest AS (
            SELECT MAX(month_index) AS month_index FROM core.fact_visitors_monthly
        ), latest_fc AS (
            SELECT DISTINCT ON (f.governorate_id)
                f.governorate_id, f.forecast_value, f.lower_bound, f.upper_bound
            FROM forecast.region_demand_forecast f
            JOIN forecast.model_run mr ON mr.model_run_id = f.model_run_id
            ORDER BY f.governorate_id, mr.model_run_id DESC, f.forecast_month
        )
        SELECT
            g.governorate_id,
            g.governorate_code,
            g.governorate_name_en,
            v.total_visitors AS latest_total_visitors,
            rb.total_beds AS latest_total_beds,
            o.average_occupancy_rate AS latest_average_occupancy_rate,
            p.priority_score,
            p.justification_text,
            p.occupancy_component,
            p.growth_component,
            p.visitor_bed_component,
            p.forecast_component,
            i.visitors_per_1000_beds,
            i.occupancy_pressure_index,
            i.growth_pressure_index,
            i.forecast_pressure_index,
            c.capacity_classification,
            fc.forecast_value AS next_forecast_value,
            fc.lower_bound AS next_forecast_lower,
            fc.upper_bound AS next_forecast_upper
        FROM core.governorate g
        LEFT JOIN latest l ON TRUE
        LEFT JOIN core.fact_visitors_monthly v
               ON v.governorate_id = g.governorate_id AND v.month_index = l.month_index
        LEFT JOIN core.fact_rooms_beds_monthly rb
               ON rb.governorate_id = g.governorate_id AND rb.month_index = l.month_index
        LEFT JOIN core.fact_hotel_occupancy_monthly o
               ON o.governorate_id = g.governorate_id AND o.month_index = l.month_index
        LEFT JOIN analytics.region_indicator_monthly i
               ON i.governorate_id = g.governorate_id AND i.month_index = l.month_index
        LEFT JOIN analytics.region_priority_score_monthly p
               ON p.governorate_id = g.governorate_id AND p.month_index = l.month_index
        LEFT JOIN analytics.region_classification_monthly c
               ON c.governorate_id = g.governorate_id AND c.month_index = l.month_index
        LEFT JOIN latest_fc fc ON fc.governorate_id = g.governorate_id
        ORDER BY p.priority_score DESC NULLS LAST, g.governorate_id
        """)
        return [dict(r) for r in db.execute(sql).mappings().all()]

    def get_map(self, db: Session):
        sql = text("""
        SELECT json_build_object(
          'type','FeatureCollection',
          'features', COALESCE(json_agg(feature), '[]'::json)
        ) AS geojson
        FROM (
          SELECT json_build_object(
            'type','Feature',
            'geometry', ST_AsGeoJSON(boundary_geom)::json,
            'properties', json_build_object(
                'governorate_id', governorate_id,
                'governorate_code', governorate_code,
                'governorate_name_en', governorate_name_en
            )
          ) AS feature
          FROM gis.admin_boundary
          ORDER BY governorate_id
        ) t
        """)
        return db.execute(sql).scalar_one()

    def get_sites(self, db: Session):
        sql = text("""
        SELECT tourism_site_id, site_name_en, site_category, governorate_id, latitude, longitude
        FROM core.tourism_site
        ORDER BY site_name_en
        """)
        return [dict(r) for r in db.execute(sql).mappings().all()]

    def get_region_detail(self, db: Session, governorate_id: int):
        ts_sql = text("""
        WITH latest_run AS (SELECT model_run_id FROM forecast.model_run ORDER BY model_run_id DESC LIMIT 1)
        SELECT
            v.month_index::text AS month_index,
            v.total_visitors,
            rb.total_rooms,
            rb.total_beds,
            o.average_occupancy_rate,
            p.priority_score
        FROM core.fact_visitors_monthly v
        LEFT JOIN core.fact_rooms_beds_monthly rb
          ON rb.governorate_id = v.governorate_id AND rb.month_index = v.month_index
        LEFT JOIN core.fact_hotel_occupancy_monthly o
          ON o.governorate_id = v.governorate_id AND o.month_index = v.month_index
        LEFT JOIN analytics.region_priority_score_monthly p
          ON p.governorate_id = v.governorate_id AND p.month_index = v.month_index
        WHERE v.governorate_id = :gid
        ORDER BY v.month_index
        """)
        row = db.execute(text("""
            WITH latest AS (SELECT MAX(month_index) AS month_index FROM core.fact_visitors_monthly),
            latest_fc AS (
                SELECT DISTINCT ON (f.governorate_id)
                    f.governorate_id, f.forecast_month, f.forecast_value, f.lower_bound, f.upper_bound,
                    m.mape, m.mae, m.rmse, m.reliability_label
                FROM forecast.region_demand_forecast f
                JOIN forecast.model_run mr ON mr.model_run_id = f.model_run_id
                LEFT JOIN forecast.backtest_metric m ON m.model_run_id = f.model_run_id AND m.governorate_id = f.governorate_id
                WHERE f.governorate_id = :gid
                ORDER BY f.governorate_id, mr.model_run_id DESC, f.forecast_month
            )
            SELECT g.governorate_id, g.governorate_name_en,
                   p.priority_score, p.justification_text, p.occupancy_component, p.growth_component,
                   p.visitor_bed_component, p.forecast_component,
                   i.visitors_per_1000_beds, i.occupancy_pressure_index, i.growth_pressure_index, i.forecast_pressure_index,
                   c.capacity_classification,
                   fc.forecast_month AS next_forecast_month, fc.forecast_value AS next_forecast_value,
                   fc.lower_bound AS next_forecast_lower, fc.upper_bound AS next_forecast_upper,
                   fc.mape, fc.mae, fc.rmse, fc.reliability_label
            FROM core.governorate g
            LEFT JOIN latest l ON TRUE
            LEFT JOIN analytics.region_indicator_monthly i ON i.governorate_id = g.governorate_id AND i.month_index = l.month_index
            LEFT JOIN analytics.region_priority_score_monthly p ON p.governorate_id = g.governorate_id AND p.month_index = l.month_index
            LEFT JOIN analytics.region_classification_monthly c ON c.governorate_id = g.governorate_id AND c.month_index = l.month_index
            LEFT JOIN latest_fc fc ON fc.governorate_id = g.governorate_id
            WHERE g.governorate_id = :gid
        """), {'gid': governorate_id}).mappings().first()
        sites = db.execute(text("SELECT tourism_site_id, site_name_en, site_category, latitude, longitude FROM core.tourism_site WHERE governorate_id = :gid ORDER BY site_name_en"), {'gid': governorate_id}).mappings().all()
        result = dict(row) if row else {'governorate_id': governorate_id}
        result['time_series'] = [dict(r) for r in db.execute(ts_sql, {'gid': governorate_id}).mappings().all()]
        result['sites'] = [dict(r) for r in sites]
        return result
