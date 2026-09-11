from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
try:
    from app.auth.security import decode_access_token
    from app.auth.models import User
except ModuleNotFoundError:
    from .security import decode_access_token
    from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_token_from_request(request: Request, token_header: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Extrait le jeton JWT du cookie 'access_token' ou du header Authorization.
    """
    # 1. Vérifier le cookie
    token = request.cookies.get("access_token")
    if token:
        # Nettoyer le préfixe Bearer si présent dans le cookie
        if token.startswith("Bearer "):
            token = token[7:]
        return token

    # 2. Vérifier le header Bearer
    if token_header:
        return token_header

    return None

def get_current_user(token: Optional[str] = Depends(get_token_from_request)) -> User:
    """
    Dépendance FastAPI pour protéger les routes.
    Lève HTTP 401 Unauthorized si l'utilisateur n'est pas authentifié.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session non valide ou expirée. Veuillez vous connecter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou invalide. Veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton de session invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(
        username=username,
        display_name=payload.get("display_name", username),
        email=payload.get("email"),
        dn=payload.get("dn"),
        groups=payload.get("groups", [])
    )

def get_current_user_optional(token: Optional[str] = Depends(get_token_from_request)) -> Optional[User]:
    """
    Retourne l'utilisateur connecté s'il existe, ou None sinon.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    return User(
        username=username,
        display_name=payload.get("display_name", username),
        email=payload.get("email"),
        dn=payload.get("dn"),
        groups=payload.get("groups", [])
    )
