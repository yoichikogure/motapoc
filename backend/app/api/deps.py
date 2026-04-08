from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.core.database import get_db


def require_user(request: Request, db: Session = Depends(get_db)):
    return get_current_user(request, db)
