from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.database import get_db
from app.services.config_service import ConfigService

router = APIRouter(prefix='/api/config', tags=['config'])
service = ConfigService()


@router.get('')
def get_config(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.get_config(db)


@router.post('')
def update_config(payload: dict, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.update_config(db, payload)


@router.get('/methodology')
def get_methodology(user=Depends(require_user)):
    return service.methodology()
