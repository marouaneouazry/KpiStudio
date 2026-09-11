from fastapi import APIRouter, Depends, HTTPException, Response, status
from datetime import timedelta
import logging

try:
    from app.auth.models import LoginRequest, TokenResponse, User
    from app.auth.ldap import LDAPAuthenticator, LDAPAuthenticationError
    from app.auth.security import create_access_token
    from app.auth.dependencies import get_current_user
    from app.auth.config import settings
except ModuleNotFoundError:
    from .models import LoginRequest, TokenResponse, User
    from .ldap import LDAPAuthenticator, LDAPAuthenticationError
    from .security import create_access_token
    from .dependencies import get_current_user
    from .config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
ldap_authenticator = LDAPAuthenticator()

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, response: Response):
    """
    Authentifie l'utilisateur via LDAP et initialise une session JWT.
    Le jeton est également enregistré dans un cookie HTTPOnly.
    """
    try:
        user = ldap_authenticator.authenticate(credentials.username, credentials.password)
    except LDAPAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur inattendue lors du login : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur lors de la connexion."
        )

    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    token_data = {
        "sub": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "dn": user.dn,
        "groups": user.groups
    }
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    # Configurer le cookie HTTPOnly sécurisé
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/"
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@router.post("/logout")
async def logout(response: Response):
    """
    Déconnecte l'utilisateur en supprimant le cookie de session HTTPOnly.
    """
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/"
    )
    return {"message": "Déconnexion réussie"}

@router.get("/me", response_model=User)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retourne le profil de l'utilisateur actuellement connecté.
    """
    return current_user
