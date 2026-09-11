from app.api.routes.auth import router as auth_pages_router
from app.api.routes.config import router as config_router
from app.api.routes.holidays import router as holidays_router
from app.api.routes.reports import router as reports_router
from app.api.routes.dashboard import router as dashboard_router

__all__ = [
    "auth_pages_router",
    "config_router",
    "holidays_router",
    "reports_router",
    "dashboard_router",
]
