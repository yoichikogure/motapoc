from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.database import get_db
from app.services.export_service import ExportService

router = APIRouter(prefix='/api/exports', tags=['exports'])
service = ExportService()


@router.get('/overview.csv')
def export_overview_csv(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.overview_csv(db)


@router.get('/regions/{governorate_id}.csv')
def export_region_csv(governorate_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.region_csv(db, governorate_id)


@router.get('/executive-summary.html')
def export_executive_summary(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.executive_summary_html(db)
