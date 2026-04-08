from pydantic import BaseModel


class SimulationRequest(BaseModel):
    governorate_id: int
    target_month: str
    additional_beds: int = 0
    additional_rooms: int = 0
    induced_demand_ratio: float = 0.0
    based_on_model_run_id: int | None = None


class SimulationRunResponse(BaseModel):
    scenario_run_id: int
    governorate_id: int
    target_month: str
    scenario_type: str
    status: str
