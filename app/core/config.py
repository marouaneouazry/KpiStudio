import os
from typing import Optional
from dotenv import load_dotenv, find_dotenv

# Ensure environment variables from .env are loaded
load_dotenv(find_dotenv(usecwd=True))

class Settings:
    """
    Centralized application configuration for Mantis KPI Studio.
    Provides path centralization, environment variables, and authentication settings.
    Properties dynamically read from os.environ to ensure test overrides take effect.
    """

    @property
    def PROJECT_ROOT(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    @property
    def CONFIG_DIR(self) -> str:
        return os.environ.get("APP_CONFIG_DIR", os.path.join(self.PROJECT_ROOT, "config"))

    @property
    def OUTPUT_DIR(self) -> str:
        return os.environ.get("APP_OUTPUT_DIR", os.path.join(self.PROJECT_ROOT, "outputs"))

    @property
    def HOLIDAYS_DIR(self) -> str:
        return os.path.join(self.CONFIG_DIR, "holidays")

    @property
    def SLA_MAPPING_PATH(self) -> str:
        return os.path.join(self.CONFIG_DIR, "sla_mapping.json")

    @property
    def COLLABORATORS_PATH(self) -> str:
        return os.path.join(self.CONFIG_DIR, "collaborators.json")

    # Mantis Configuration
    @property
    def MANTIS_BASE_URL(self) -> str:
        return os.environ.get("MANTIS_BASE_URL", "")

    @property
    def MANTIS_API_TOKEN(self) -> str:
        return os.environ.get("MANTIS_API_TOKEN", "")

    @property
    def MANTIS_VERIFY_SSL(self) -> bool:
        return os.environ.get("MANTIS_VERIFY_SSL", "false").lower() == "true"

    @property
    def ENVIRONMENT(self) -> str:
        return os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", os.environ.get("ENV", "development"))).lower()

    # JWT Authentication Configuration
    @property
    def JWT_SECRET(self) -> str:
        secret = os.environ.get("JWT_SECRET")
        is_production = self.ENVIRONMENT in ("production", "prod")

        if is_production:
            if not secret or secret == "default_insecure_jwt_secret_change_me_in_production":
                raise RuntimeError(
                    "JWT_SECRET environment variable must be explicitly set in production. "
                    "Refusing to start with missing or default insecure JWT secret."
                )
            return secret

        return secret or "default_insecure_jwt_secret_change_me_in_production"

    @property
    def JWT_ALGORITHM(self) -> str:
        return os.environ.get("JWT_ALGORITHM", "HS256")

    @property
    def JWT_EXPIRE_MINUTES(self) -> int:
        return int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))

    # Cookie Security Configuration
    @property
    def COOKIE_SECURE(self) -> bool:
        default = "true" if self.ENVIRONMENT in ("production", "prod") else "false"
        return os.environ.get("COOKIE_SECURE", default).lower() in ("true", "1", "t", "yes")

    @property
    def COOKIE_SAMESITE(self) -> str:
        return os.environ.get("COOKIE_SAMESITE", "strict").lower()

    # LDAP Configuration
    @property
    def LDAP_SERVER(self) -> str:
        return os.environ.get("LDAP_SERVER", "ldap.company.com")

    @property
    def LDAP_PORT(self) -> int:
        return int(os.environ.get("LDAP_PORT", "389"))

    @property
    def LDAP_USE_SSL(self) -> bool:
        return os.environ.get("LDAP_USE_SSL", "False").lower() in ("true", "1", "t", "yes")

    @property
    def LDAP_BASE_DN(self) -> str:
        return os.environ.get("LDAP_BASE_DN", "dc=company,dc=com")

    @property
    def LDAP_BIND_DN(self) -> Optional[str]:
        return os.environ.get("LDAP_BIND_DN", None)

    @property
    def LDAP_BIND_PASSWORD(self) -> Optional[str]:
        return os.environ.get("LDAP_BIND_PASSWORD", None)

    @property
    def LDAP_SEARCH_FILTER(self) -> str:
        return os.environ.get("LDAP_SEARCH_FILTER", "(sAMAccountName={username})")

    @property
    def ALLOW_MOCK_LDAP(self) -> bool:
        return os.environ.get("ALLOW_MOCK_LDAP", "False").lower() in ("true", "1", "t", "yes")

settings = Settings()
