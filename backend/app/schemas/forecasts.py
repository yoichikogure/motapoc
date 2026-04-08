from pydantic import BaseModel


class ForecastRunResponse(BaseModel):
    model_run_id: int
    model_name: str
    horizon_months: int
    status: str
