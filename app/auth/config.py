try:
    from app.core.config import settings as core_settings
except ModuleNotFoundError:
    from core.config import settings as core_settings

class AuthSettings:
    """
    Configuration de l'authentification LDAP et JWT.
    Délégué de manière centralisée à app.core.config.settings.
    """
    @property
    def JWT_SECRET(self) -> str:
        return core_settings.JWT_SECRET

    @property
    def JWT_ALGORITHM(self) -> str:
        return core_settings.JWT_ALGORITHM

    @property
    def JWT_EXPIRE_MINUTES(self) -> int:
        return core_settings.JWT_EXPIRE_MINUTES

    @property
    def COOKIE_SECURE(self) -> bool:
        return core_settings.COOKIE_SECURE

    @property
    def COOKIE_SAMESITE(self) -> str:
        return core_settings.COOKIE_SAMESITE

    @property
    def LDAP_SERVER(self) -> str:
        return core_settings.LDAP_SERVER

    @property
    def LDAP_PORT(self) -> int:
        return core_settings.LDAP_PORT

    @property
    def LDAP_USE_SSL(self) -> bool:
        return core_settings.LDAP_USE_SSL

    @property
    def LDAP_BASE_DN(self) -> str:
        return core_settings.LDAP_BASE_DN

    @property
    def LDAP_BIND_DN(self):
        return core_settings.LDAP_BIND_DN

    @property
    def LDAP_BIND_PASSWORD(self):
        return core_settings.LDAP_BIND_PASSWORD

    @property
    def LDAP_SEARCH_FILTER(self) -> str:
        return core_settings.LDAP_SEARCH_FILTER

    @property
    def ALLOW_MOCK_LDAP(self) -> bool:
        return core_settings.ALLOW_MOCK_LDAP

settings = AuthSettings()

