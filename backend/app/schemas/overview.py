from pydantic import BaseModel
from typing import Any, List


class KpiResponse(BaseModel):
    latest_month: str | None
    total_visitors: float
    total_rooms: float
    total_beds: float
    average_occupancy_rate: float
    high_priority_zones: int


class RegionRow(BaseModel):
    governorate_id: int
    governorate_code: str
    governorate_name_en: str
    latest_total_visitors: float | None
    latest_total_beds: float | None
    latest_average_occupancy_rate: float | None
    priority_score: float | None
    capacity_classification: str | None


class RegionDetailResponse(BaseModel):
    governorate_id: int
    governorate_name_en: str
    time_series: List[dict[str, Any]]
