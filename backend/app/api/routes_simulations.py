from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_user
from app.core.database import get_db
from app.services.simulation_service import SimulationService
from app.schemas.simulations import SimulationRequest

router = APIRouter(prefix='/api/simulations', tags=['simulations'])
service = SimulationService()

@router.post('/run')
def run_simulation(payload: SimulationRequest, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.run(db, payload.model_dump())

@router.get('/runs')
def list_runs(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.list_runs(db)

@router.get('/latest')
def latest(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.latest(db)

@router.get('/runs/{scenario_run_id}')
def run_detail(scenario_run_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_run_detail(db, scenario_run_id)
