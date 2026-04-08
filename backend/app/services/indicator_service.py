from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.config_service import ConfigService


class IndicatorService:
    def recompute(self, db: Session):
        cfg = ConfigService().get_numeric_map(db)
        tight = cfg.get('classification_tight_threshold', 75)
        balanced = cfg.get('classification_balanced_threshold', 45)
        w_occ = cfg.get('priority_weight_occupancy', 0.35)
        w_growth = cfg.get('priority_weight_growth', 0.20)
        w_vpb = cfg.get('priority_weight_visitor_bed', 0.25)
        w_fc = cfg.get('priority_weight_forecast', 0.20)

        db.execute(text("TRUNCATE analytics.region_indicator_monthly, analytics.region_classification_monthly, analytics.region_priority_score_monthly RESTART IDENTITY"))

        indicator_sql = text("""
        WITH latest_run AS (
            SELECT model_run_id FROM forecast.model_run ORDER BY model_run_id DESC LIMIT 1
        ),
        next_fc AS (
            SELECT DISTINCT ON (governorate_id)
                governorate_id,
                forecast_value
            FROM forecast.region_demand_forecast
            WHERE model_run_id = (SELECT model_run_id FROM latest_run)
            ORDER BY governorate_id, forecast_month
        )
        INSERT INTO analytics.region_indicator_monthly (
            governorate_id, month_index, visitors_per_1000_beds,
            occupancy_pressure_index, growth_pressure_index, capacity_adequacy_index, forecast_pressure_index
        )
        SELECT
            v.governorate_id,
            v.month_index,
            CASE WHEN COALESCE(rb.total_beds,0) > 0
                 THEN (v.total_visitors::numeric / rb.total_beds::numeric) * 1000
                 ELSE NULL END AS visitors_per_1000_beds,
            COALESCE(o.average_occupancy_rate,0) * 100 AS occupancy_pressure_index,
            CASE
                WHEN prev.total_visitors IS NULL OR prev.total_visitors = 0 THEN NULL
                ELSE ((v.total_visitors - prev.total_visitors)::numeric / prev.total_visitors::numeric) * 100
            END AS growth_pressure_index,
            CASE WHEN COALESCE(v.total_visitors,0) > 0
                 THEN (rb.total_beds::numeric / v.total_visitors::numeric) * 1000
                 ELSE NULL END AS capacity_adequacy_index,
            CASE WHEN rb.total_beds > 0 AND fc.forecast_value IS NOT NULL
                 THEN LEAST(100, (fc.forecast_value / rb.total_beds::numeric) * 4)
                 ELSE NULL END AS forecast_pressure_index
        FROM core.fact_visitors_monthly v
        LEFT JOIN core.fact_rooms_beds_monthly rb
          ON rb.governorate_id = v.governorate_id AND rb.month_index = v.month_index
        LEFT JOIN core.fact_hotel_occupancy_monthly o
          ON o.governorate_id = v.governorate_id AND o.month_index = v.month_index
        LEFT JOIN core.fact_visitors_monthly prev
          ON prev.governorate_id = v.governorate_id AND prev.month_index = (v.month_index - INTERVAL '12 month')
        LEFT JOIN next_fc fc ON fc.governorate_id = v.governorate_id
        """)
        db.execute(indicator_sql)

        class_sql = text("""
        INSERT INTO analytics.region_classification_monthly (governorate_id, month_index, capacity_classification)
        SELECT
            governorate_id,
            month_index,
            CASE
                WHEN occupancy_pressure_index >= :tight THEN 'Under-capacity'
                WHEN occupancy_pressure_index >= :balanced THEN 'Balanced'
                ELSE 'Over-capacity'
            END
        FROM analytics.region_indicator_monthly
        """)
        db.execute(class_sql, {'tight': tight, 'balanced': balanced})

        score_sql = text("""
        INSERT INTO analytics.region_priority_score_monthly (
            governorate_id, month_index, priority_score, justification_text,
            occupancy_component, growth_component, visitor_bed_component, forecast_component
        )
        SELECT
            i.governorate_id,
            i.month_index,
            ROUND(LEAST(100,
                COALESCE(i.occupancy_pressure_index,0) * :w_occ +
                LEAST(GREATEST(COALESCE(i.growth_pressure_index,0),0),100) * :w_growth +
                LEAST(COALESCE(i.visitors_per_1000_beds,0) / 25,100) * :w_vpb +
                LEAST(COALESCE(i.forecast_pressure_index,0),100) * :w_fc
            )::numeric, 2) AS priority_score,
            CASE
                WHEN c.capacity_classification = 'Under-capacity' THEN 'Capacity expansion priority'
                WHEN c.capacity_classification = 'Balanced' THEN 'Seasonal management / service quality priority'
                ELSE 'Demand diversification / marketing priority'
            END AS justification_text,
            ROUND((COALESCE(i.occupancy_pressure_index,0) * :w_occ)::numeric,2),
            ROUND((LEAST(GREATEST(COALESCE(i.growth_pressure_index,0),0),100) * :w_growth)::numeric,2),
            ROUND((LEAST(COALESCE(i.visitors_per_1000_beds,0) / 25,100) * :w_vpb)::numeric,2),
            ROUND((LEAST(COALESCE(i.forecast_pressure_index,0),100) * :w_fc)::numeric,2)
        FROM analytics.region_indicator_monthly i
        JOIN analytics.region_classification_monthly c
          ON c.governorate_id = i.governorate_id AND c.month_index = i.month_index
        """)
        db.execute(score_sql, {'w_occ': w_occ, 'w_growth': w_growth, 'w_vpb': w_vpb, 'w_fc': w_fc})
        db.commit()
        return {"status": "ok"}
