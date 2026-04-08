from math import sqrt

from sqlalchemy import text
from sqlalchemy.orm import Session


class ForecastService:
    def _reliability(self, hist_len: int, mape: float | None):
        if hist_len >= 24 and mape is not None and mape <= 12:
            return 'High'
        if hist_len >= 18 and mape is not None and mape <= 20:
            return 'Moderate'
        return 'Low'

    def _model_name(self, requested: str | None):
        return requested if requested in {'seasonal_naive', 'seasonal_trend_v2'} else 'seasonal_trend_v2'

    def run(self, db: Session, horizon_months: int = 12, model_name: str | None = None):
        model_name = self._model_name(model_name)
        insert_run = text("""
        INSERT INTO forecast.model_run (model_name, forecast_target, horizon_months, status, run_parameters_json)
        VALUES (:model_name, 'total_visitors', :h, 'completed', CAST(:params AS jsonb))
        RETURNING model_run_id
        """)
        params = {'model_name': model_name, 'horizon_months': horizon_months}
        model_run_id = db.execute(insert_run, {'model_name': model_name, 'h': horizon_months, 'params': str(params).replace("'", '"')}).scalar_one()

        governorates = [r[0] for r in db.execute(text('SELECT governorate_id FROM core.governorate ORDER BY governorate_id')).all()]

        for gid in governorates:
            rows = db.execute(text("""
                SELECT month_index, total_visitors
                FROM core.fact_visitors_monthly
                WHERE governorate_id = :gid
                ORDER BY month_index
            """), {'gid': gid}).all()
            if len(rows) < 13:
                continue

            vals = [float(r[1]) for r in rows]
            yoy_growth = []
            resid = []
            for i in range(12, len(vals)):
                prev = vals[i - 12]
                cur = vals[i]
                if prev > 0:
                    yoy_growth.append((cur - prev) / prev)
                    resid.append(cur - prev)
            avg_growth = sum(yoy_growth) / len(yoy_growth) if yoy_growth else 0.03
            sigma = sqrt(sum((x - (sum(resid)/len(resid) if resid else 0)) ** 2 for x in resid) / len(resid)) if resid else max(vals[-12:]) * 0.08
            last12 = vals[-12:]
            last_month = rows[-1][0]

            for step in range(1, horizon_months + 1):
                season_base = last12[(step - 1) % 12]
                if model_name == 'seasonal_naive':
                    forecast_value = season_base
                else:
                    forecast_value = season_base * (1 + avg_growth)
                lower = max(0.0, forecast_value - 1.28 * sigma)
                upper = max(lower, forecast_value + 1.28 * sigma)
                db.execute(text("""
                    INSERT INTO forecast.region_demand_forecast (
                        model_run_id, governorate_id, forecast_month, forecast_value, lower_bound, upper_bound
                    ) VALUES (
                        :mr, :gid, (:last_month + (:step || ' month')::interval)::date, :fv, :lb, :ub
                    )
                """), {
                    'mr': model_run_id,
                    'gid': gid,
                    'last_month': last_month,
                    'step': step,
                    'fv': round(forecast_value, 2),
                    'lb': round(lower, 2),
                    'ub': round(upper, 2),
                })

            abs_err, sq_err, ape = [], [], []
            for i in range(12, len(vals)):
                pred = vals[i - 12] if model_name == 'seasonal_naive' else vals[i - 12] * (1 + avg_growth)
                actual = vals[i]
                err = actual - pred
                abs_err.append(abs(err))
                sq_err.append(err * err)
                if actual != 0:
                    ape.append(abs(err) / actual * 100)

            mae = sum(abs_err) / len(abs_err) if abs_err else None
            rmse = sqrt(sum(sq_err) / len(sq_err)) if sq_err else None
            mape = sum(ape) / len(ape) if ape else None
            reliability = self._reliability(len(vals), mape)

            db.execute(text("""
                INSERT INTO forecast.backtest_metric (
                    model_run_id, governorate_id, mae, rmse, mape, reliability_label
                ) VALUES (:mr, :gid, :mae, :rmse, :mape, :rel)
            """), {'mr': model_run_id, 'gid': gid, 'mae': mae, 'rmse': rmse, 'mape': mape, 'rel': reliability})

        db.commit()
        return {
            'model_run_id': model_run_id,
            'model_name': model_name,
            'horizon_months': horizon_months,
            'status': 'completed',
        }

    def list_runs(self, db: Session):
        sql = text('SELECT model_run_id, model_name, forecast_target, horizon_months, status, created_at FROM forecast.model_run ORDER BY model_run_id DESC')
        return [dict(r) for r in db.execute(sql).mappings().all()]

    def latest(self, db: Session):
        row = db.execute(text("""
        SELECT model_run_id, model_name, forecast_target, horizon_months, status, created_at
        FROM forecast.model_run
        ORDER BY model_run_id DESC
        LIMIT 1
        """)).mappings().first()
        return dict(row) if row else None

    def get_run_detail(self, db: Session, model_run_id: int):
        header = db.execute(text("""
        SELECT model_run_id, model_name, forecast_target, horizon_months, status, created_at, run_parameters_json
        FROM forecast.model_run WHERE model_run_id = :mr
        """), {'mr': model_run_id}).mappings().first()
        rows = db.execute(text("""
        SELECT g.governorate_name_en, f.forecast_month, f.forecast_value, f.lower_bound, f.upper_bound,
               m.mae, m.rmse, m.mape, m.reliability_label, f.governorate_id
        FROM forecast.region_demand_forecast f
        JOIN core.governorate g ON g.governorate_id = f.governorate_id
        LEFT JOIN forecast.backtest_metric m ON m.model_run_id = f.model_run_id AND m.governorate_id = f.governorate_id
        WHERE f.model_run_id = :mr
        ORDER BY g.governorate_id, f.forecast_month
        """), {'mr': model_run_id}).mappings().all()
        return {'run': dict(header) if header else None, 'rows': [dict(r) for r in rows]}
