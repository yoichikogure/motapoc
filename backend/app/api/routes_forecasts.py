from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_user
from app.core.database import get_db
from app.services.forecast_service import ForecastService

router = APIRouter(prefix='/api/forecasts', tags=['forecasts'])
service = ForecastService()

@router.post('/run')
def run_forecast(payload: dict | None = None, user=Depends(require_user), db: Session = Depends(get_db)):
    payload = payload or {}
    return service.run(db, horizon_months=int(payload.get('horizon_months', 12)), model_name=payload.get('model_name'))

@router.get('/runs')
def list_runs(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.list_runs(db)

@router.get('/latest')
def latest(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.latest(db)

@router.get('/runs/{model_run_id}')
def run_detail(model_run_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_run_detail(db, model_run_id)
