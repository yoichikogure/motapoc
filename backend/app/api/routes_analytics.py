from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_user
from app.core.database import get_db
from app.services.indicator_service import IndicatorService

router = APIRouter(prefix='/api/analytics', tags=['analytics'])
service = IndicatorService()

@router.post('/recompute')
def recompute(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.recompute(db)
