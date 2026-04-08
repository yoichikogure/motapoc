from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.config_service import ConfigService


class SimulationService:
    def run(self, db: Session, payload: dict):
        cfg = ConfigService().get_numeric_map(db)
        base_run_id = payload.get('based_on_model_run_id')
        if not base_run_id:
            base_run_id = db.execute(text('SELECT model_run_id FROM forecast.model_run ORDER BY model_run_id DESC LIMIT 1')).scalar()

        scenario_run_id = db.execute(text("""
        INSERT INTO simulation.scenario_run (
            governorate_id, target_month, scenario_type,
            additional_beds, additional_rooms, induced_demand_ratio,
            based_on_model_run_id, status
        )
        VALUES (
            :governorate_id, :target_month, 'bed_addition',
            :additional_beds, :additional_rooms, :induced_demand_ratio,
            :based_on_model_run_id, 'completed'
        )
        RETURNING scenario_run_id
        """), payload | {'based_on_model_run_id': base_run_id}).scalar_one()

        w_occ = cfg.get('priority_weight_occupancy', 0.35)
        w_growth = cfg.get('priority_weight_growth', 0.20)
        w_vpb = cfg.get('priority_weight_visitor_bed', 0.25)
        w_fc = cfg.get('priority_weight_forecast', 0.20)

        detail = db.execute(text("""
        WITH forecast_base AS (
            SELECT forecast_value
            FROM forecast.region_demand_forecast
            WHERE model_run_id = :mr AND governorate_id = :gid AND forecast_month = :target_month::date
            LIMIT 1
        ), latest_hist AS (
            SELECT v.total_visitors, rb.total_beds, rb.total_rooms, o.average_occupancy_rate,
                   i.growth_pressure_index, c.capacity_classification
            FROM core.fact_visitors_monthly v
            JOIN core.fact_rooms_beds_monthly rb ON rb.governorate_id = v.governorate_id AND rb.month_index = v.month_index
            LEFT JOIN core.fact_hotel_occupancy_monthly o ON o.governorate_id = v.governorate_id AND o.month_index = v.month_index
            LEFT JOIN analytics.region_indicator_monthly i ON i.governorate_id = v.governorate_id AND i.month_index = v.month_index
            LEFT JOIN analytics.region_classification_monthly c ON c.governorate_id = v.governorate_id AND c.month_index = v.month_index
            WHERE v.governorate_id = :gid
            ORDER BY v.month_index DESC LIMIT 1
        )
        SELECT
            COALESCE(fb.forecast_value, lh.total_visitors) AS baseline_demand,
            lh.total_beds AS baseline_beds,
            lh.total_rooms AS baseline_rooms,
            COALESCE(lh.average_occupancy_rate, 0) * 100 AS occupancy_pressure,
            COALESCE(lh.growth_pressure_index, 0) AS growth_pressure,
            COALESCE(lh.capacity_classification, 'Balanced') AS capacity_status_before
        FROM latest_hist lh
        LEFT JOIN forecast_base fb ON TRUE
        """), {'mr': base_run_id, 'gid': payload['governorate_id'], 'target_month': payload['target_month']}).mappings().first()
        if not detail:
            db.rollback()
            raise ValueError('Unable to compute scenario baseline')

        baseline_demand = float(detail['baseline_demand'] or 0)
        baseline_beds = float(detail['baseline_beds'] or 0)
        scenario_demand = baseline_demand * (1 + float(payload.get('induced_demand_ratio', 0)))
        scenario_beds = baseline_beds + float(payload.get('additional_beds', 0))
        visitors_before = (baseline_demand / baseline_beds * 1000) if baseline_beds > 0 else None
        visitors_after = (scenario_demand / scenario_beds * 1000) if scenario_beds > 0 else None
        occ_pressure = float(detail['occupancy_pressure'] or 0)
        growth_pressure = max(0.0, float(detail['growth_pressure'] or 0))
        forecast_pressure_before = min(100.0, (baseline_demand / baseline_beds) * 4) if baseline_beds > 0 else 0
        forecast_pressure_after = min(100.0, (scenario_demand / scenario_beds) * 4) if scenario_beds > 0 else 0
        visitor_bed_before = min(100.0, (visitors_before / 25.0) if visitors_before is not None else 0)
        visitor_bed_after = min(100.0, (visitors_after / 25.0) if visitors_after is not None else 0)
        priority_before = min(100.0, occ_pressure * w_occ + min(growth_pressure, 100.0) * w_growth + visitor_bed_before * w_vpb + forecast_pressure_before * w_fc)
        priority_after = min(100.0, occ_pressure * w_occ + min(growth_pressure, 100.0) * w_growth + visitor_bed_after * w_vpb + forecast_pressure_after * w_fc)

        def classify(p):
            if p >= cfg.get('classification_tight_threshold', 75):
                return 'Under-capacity'
            if p >= cfg.get('classification_balanced_threshold', 45):
                return 'Balanced'
            return 'Over-capacity'

        after_status = classify(occ_pressure * (baseline_beds / scenario_beds if scenario_beds else 1))
        if priority_after < priority_before - 5:
            note = 'Capacity stress improves under the selected future baseline.'
        elif priority_after > priority_before + 5:
            note = 'Oversupply risk may remain limited; demand assumptions dominate the result.'
        else:
            note = 'Scenario changes are modest; monitor demand before committing large investment.'

        db.execute(text("""
        INSERT INTO simulation.region_scenario_result (
            scenario_run_id, governorate_id, target_month,
            baseline_demand, scenario_demand, demand_delta,
            baseline_beds, scenario_beds, beds_delta,
            priority_score_before, priority_score_after,
            capacity_status_before, capacity_status_after,
            visitors_per_1000_beds_before, visitors_per_1000_beds_after,
            recommendation_text
        ) VALUES (
            :srid, :gid, :target_month,
            :bd, :sd, :dd,
            :bb, :sb, :bed_delta,
            :pb, :pa,
            :csb, :csa,
            :vbb, :vba,
            :note
        )
        """), {
            'srid': scenario_run_id,
            'gid': payload['governorate_id'],
            'target_month': payload['target_month'],
            'bd': round(baseline_demand, 2),
            'sd': round(scenario_demand, 2),
            'dd': round(scenario_demand - baseline_demand, 2),
            'bb': round(baseline_beds, 2),
            'sb': round(scenario_beds, 2),
            'bed_delta': payload.get('additional_beds', 0),
            'pb': round(priority_before, 2),
            'pa': round(priority_after, 2),
            'csb': detail['capacity_status_before'],
            'csa': after_status,
            'vbb': round(visitors_before, 4) if visitors_before is not None else None,
            'vba': round(visitors_after, 4) if visitors_after is not None else None,
            'note': note,
        })
        db.commit()
        return {
            'scenario_run_id': scenario_run_id,
            'governorate_id': payload['governorate_id'],
            'target_month': payload['target_month'],
            'scenario_type': 'bed_addition',
            'status': 'completed',
        }

    def list_runs(self, db: Session):
        sql = text('SELECT scenario_run_id, governorate_id, target_month, scenario_type, status, created_at FROM simulation.scenario_run ORDER BY scenario_run_id DESC')
        return [dict(r) for r in db.execute(sql).mappings().all()]

    def latest(self, db: Session):
        row = db.execute(text("""
        SELECT scenario_run_id, governorate_id, target_month, scenario_type, status, created_at
        FROM simulation.scenario_run
        ORDER BY scenario_run_id DESC LIMIT 1
        """)).mappings().first()
        return dict(row) if row else None

    def get_run_detail(self, db: Session, scenario_run_id: int):
        run_row = db.execute(text("""
        SELECT scenario_run_id, governorate_id, target_month, scenario_type, additional_beds,
               additional_rooms, induced_demand_ratio, based_on_model_run_id, status, created_at
        FROM simulation.scenario_run
        WHERE scenario_run_id = :srid
        """), {'srid': scenario_run_id}).mappings().first()
        result_row = db.execute(text("""
        SELECT r.*, g.governorate_name_en
        FROM simulation.region_scenario_result r
        JOIN core.governorate g ON g.governorate_id = r.governorate_id
        WHERE r.scenario_run_id = :srid
        LIMIT 1
        """), {'srid': scenario_run_id}).mappings().first()
        return {'run': dict(run_row) if run_row else None, 'result': dict(result_row) if result_row else None}
