from sqlalchemy import text
from sqlalchemy.orm import Session


METHODOLOGY = {
    'forecast_models': [
        {'key': 'seasonal_naive', 'label': 'Seasonal Naive', 'description': 'Uses the same month from the previous year as the baseline forecast.'},
        {'key': 'seasonal_trend_v2', 'label': 'Seasonal Trend v2', 'description': 'Uses last-year seasonality plus averaged year-over-year trend and simple uncertainty bands.'},
    ],
    'priority_score': 'Priority score = weighted combination of occupancy pressure, growth pressure, visitors per 1,000 beds, and forecast pressure.',
    'simulation': 'Scenario simulation uses the selected future month forecast as the baseline, then recalculates pressure after additional beds/rooms and induced demand are applied.',
    'limitations': [
        'Prototype-level system intended for planning support, not production operations.',
        'Forecasts are demand-only and do not model exogenous shocks or macroeconomic drivers.',
        'Simulation is rule-based and should be interpreted as indicative planning support.',
    ],
}


class ConfigService:
    def get_config(self, db: Session):
        rows = db.execute(text("""
            SELECT parameter_key, parameter_value, value_type, description, updated_at
            FROM admin.system_parameter
            ORDER BY parameter_key
        """)).mappings().all()
        return [dict(r) for r in rows]

    def update_config(self, db: Session, payload: dict):
        updates = payload.get('items', [])
        for item in updates:
            db.execute(text("""
                INSERT INTO admin.system_parameter(parameter_key, parameter_value, value_type, description, updated_at)
                VALUES (:k, :v, COALESCE(:t, 'number'), :d, NOW())
                ON CONFLICT (parameter_key)
                DO UPDATE SET parameter_value = EXCLUDED.parameter_value,
                              value_type = EXCLUDED.value_type,
                              description = COALESCE(EXCLUDED.description, admin.system_parameter.description),
                              updated_at = NOW()
            """), {
                'k': item['parameter_key'],
                'v': str(item['parameter_value']),
                't': item.get('value_type', 'number'),
                'd': item.get('description'),
            })
        db.commit()
        return {'status': 'ok', 'updated': len(updates)}

    def methodology(self):
        return METHODOLOGY

    def get_numeric_map(self, db: Session):
        rows = db.execute(text("SELECT parameter_key, parameter_value FROM admin.system_parameter")).all()
        out = {}
        for k, v in rows:
            try:
                out[k] = float(v)
            except Exception:
                pass
        return out
