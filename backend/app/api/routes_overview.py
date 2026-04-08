from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_user
from app.core.database import get_db
from app.services.overview_service import OverviewService

router = APIRouter(prefix='/api/overview', tags=['overview'])
service = OverviewService()

@router.get('/kpis')
def get_kpis(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_kpis(db)

@router.get('/regions')
def get_regions(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_regions(db)

@router.get('/map')
def get_map(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_map(db)

@router.get('/sites')
def get_sites(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_sites(db)

@router.get('/regions/{governorate_id}')
def get_region_detail(governorate_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_region_detail(db, governorate_id)
