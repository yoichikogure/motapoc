from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.settings import settings
from app.api.routes_health import router as health_router
from app.api.routes_auth import router as auth_router
from app.api.routes_overview import router as overview_router
from app.api.routes_analytics import router as analytics_router
from app.api.routes_forecasts import router as forecasts_router
from app.api.routes_simulations import router as simulations_router
from app.api.routes_imports import router as imports_router
from app.api.routes_exports import router as exports_router
from app.api.routes_config import router as config_router

app = FastAPI(title=settings.app_name)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site='lax', https_only=False)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(overview_router)
app.include_router(analytics_router)
app.include_router(forecasts_router)
app.include_router(simulations_router)
app.include_router(imports_router)
app.include_router(exports_router)
app.include_router(config_router)

frontend_dir = Path('/app/frontend')
app.mount('/static', StaticFiles(directory=frontend_dir / 'static'), name='static')


@app.get('/')
def root():
    return FileResponse(frontend_dir / 'index.html')
