import os
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse
from app.api.dependencies import get_token_from_request, get_current_user_optional

router = APIRouter(tags=["Auth Pages"])

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

@router.get("/login")
def login_page(request: Request):
    """
    Sert la page de connexion.
    Si l'utilisateur a déjà une session valide, il est redirigé vers Studio.
    """
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if current_user:
        return RedirectResponse(url="/studio")
    return FileResponse(os.path.join(BASE_DIR, "static", "login.html"))

@router.get("/")
def read_root(request: Request):
    """
    Racine de l'application.
    Redirige vers /studio si authentifié, sinon vers /login.
    """
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if not current_user:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/studio")

@router.get("/studio")
def studio_page(request: Request):
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if not current_user:
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(BASE_DIR, "static", "pages", "studio.html"))

@router.get("/excel")
def excel_page(request: Request):
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if not current_user:
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(BASE_DIR, "static", "pages", "excel.html"))

@router.get("/dashboard")
def dashboard_page(request: Request):
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if not current_user:
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(BASE_DIR, "static", "pages", "dashboard.html"))

@router.get("/holidays")
def holidays_page(request: Request):
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if not current_user:
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(BASE_DIR, "static", "pages", "holidays.html"))

@router.get("/sla")
def sla_page(request: Request):
    token = get_token_from_request(request)
    current_user = get_current_user_optional(token)
    if not current_user:
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(BASE_DIR, "static", "pages", "sla.html"))

