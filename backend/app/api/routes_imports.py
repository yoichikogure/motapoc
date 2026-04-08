from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.database import get_db
from app.services.import_service import ImportService

router = APIRouter(prefix='/api/imports', tags=['imports'])
service = ImportService()


@router.post('/{dataset_type}')
def import_dataset(dataset_type: str, file: UploadFile = File(...), user=Depends(require_user), db: Session = Depends(get_db)):
    return service.upload_csv(db, dataset_type, file, user['username'])


@router.get('')
def list_import_jobs(user=Depends(require_user), db: Session = Depends(get_db)):
    return service.list_jobs(db)


@router.get('/{job_id}/errors')
def list_import_errors(job_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    return service.list_errors(db, job_id)
