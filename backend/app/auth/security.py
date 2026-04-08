import hashlib
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def get_current_user(request: Request, db: Session) -> dict:
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    row = db.execute(text("""
        SELECT user_id, username, role_name, full_name, is_active
        FROM admin.app_user
        WHERE username = :username
    """), {'username': user['username']}).mappings().first()
    if not row or not row['is_active']:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Inactive user')
    return dict(row)
