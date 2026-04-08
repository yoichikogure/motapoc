from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.security import verify_password, get_current_user
from app.core.database import get_db
from app.schemas.auth import LoginRequest

router = APIRouter(prefix='/api/auth', tags=['auth'])


@router.post('/login')
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT user_id, username, password_hash, role_name, full_name, is_active
        FROM admin.app_user
        WHERE username = :username
    """), {'username': payload.username}).mappings().first()
    if not row or not row['is_active'] or not verify_password(payload.password, row['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    request.session['user'] = {
        'user_id': row['user_id'],
        'username': row['username'],
        'role_name': row['role_name'],
        'full_name': row['full_name'],
    }
    return {'ok': True, 'user': request.session['user']}


@router.get('/me')
def me(request: Request, db: Session = Depends(get_db)):
    return {'user': get_current_user(request, db)}


@router.post('/logout')
def logout(request: Request):
    request.session.clear()
    return {'ok': True}
