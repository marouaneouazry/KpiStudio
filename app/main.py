from dotenv import load_dotenv
load_dotenv()

import os
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

CONFIG_DIR = settings.CONFIG_DIR
OUTPUT_DIR = settings.OUTPUT_DIR

# Importation des APIRouters modularisés (Phase 6)
try:
    from app.auth.routes import router as auth_router
    from app.api.routes import (
        auth_pages_router,
        config_router,
        holidays_router,
        reports_router,
        dashboard_router
    )
except ModuleNotFoundError:
    from auth.routes import router as auth_router
    from api.routes import (
        auth_pages_router,
        config_router,
        holidays_router,
        reports_router,
        dashboard_router
    )

app = FastAPI(
    title="Mantis KPI Studio",
    description="Application de génération de KPIs et Dashboards avec authentification LDAP",
    version="2.0.0"
)

# Middleware de sécurité (Security Headers)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response

# Inclusion des routeurs
app.include_router(auth_router)
app.include_router(auth_pages_router)
app.include_router(config_router)
app.include_router(holidays_router)
app.include_router(reports_router)
app.include_router(dashboard_router)

# Fichiers statiques
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "static", "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "static", "js")), name="js")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)