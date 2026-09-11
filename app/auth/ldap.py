import logging
from typing import Optional, Dict, Any
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.utils.conv import escape_filter_chars
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPSocketOpenError

try:
    from app.auth.config import settings
    from app.auth.models import User
except ModuleNotFoundError:
    from .config import settings
    from .models import User

logger = logging.getLogger(__name__)

class LDAPAuthenticationError(Exception):
    """Exception personnalisée pour les échecs d'authentification LDAP."""
    pass

class LDAPAuthenticator:
    """
    Gestionnaire d'authentification LDAP / Active Directory.
    Implémente le pattern Search + Bind :
    1. Connexion initiale (compte de service ou anonyme).
    2. Recherche du DN de l'utilisateur avec LDAP_SEARCH_FILTER.
    3. Tentative de Bind avec le DN trouvé et le mot de passe fourni.
    """

    def __init__(self, settings_obj=settings):
        self.settings = settings_obj

    def authenticate(self, username: str, password: str) -> User:
        """
        Authentifie un utilisateur contre le serveur LDAP.
        Retourne un objet User en cas de succès ou lève LDAPAuthenticationError.
        """
        if not username or not password:
            raise LDAPAuthenticationError("L'identifiant et le mot de passe sont requis.")

        # Mode MOCK pour dev / tests isolés
        if self.settings.ALLOW_MOCK_LDAP:
            logger.warning("Authentification en mode MOCK LDAP active.")
            if password == "invalid":
                raise LDAPAuthenticationError("Identifiant ou mot de passe incorrect.")
            return User(
                username=username,
                display_name=f"Mock User ({username})",
                email=f"{username}@company.com",
                dn=f"cn={username},dc=company,dc=com",
                groups=["Users", "MantisAdmins"]
            )

        # 1. Échapper les caractères spéciaux dans l'identifiant
        safe_username = escape_filter_chars(username.strip())

        # 2. Configurer le serveur LDAP
        server = Server(
            host=self.settings.LDAP_SERVER,
            port=self.settings.LDAP_PORT,
            use_ssl=self.settings.LDAP_USE_SSL,
            get_info=ALL
        )

        # 3. Première étape : Connexion de recherche (Search)
        search_conn: Optional[Connection] = None
        try:
            if self.settings.LDAP_BIND_DN and self.settings.LDAP_BIND_PASSWORD:
                search_conn = Connection(
                    server,
                    user=self.settings.LDAP_BIND_DN,
                    password=self.settings.LDAP_BIND_PASSWORD,
                    authentication=SIMPLE,
                    auto_bind=True
                )
            else:
                # Connexion anonyme
                search_conn = Connection(server, auto_bind=True)

        except LDAPSocketOpenError as e:
            logger.error(f"Impossible de se connecter au serveur LDAP {self.settings.LDAP_SERVER}:{self.settings.LDAP_PORT} - {e}")
            raise LDAPAuthenticationError("Le serveur d'authentification LDAP est inatteignable.")
        except LDAPBindError as e:
            logger.error(f"Échec du bind d'administration LDAP avec BIND_DN - {e}")
            raise LDAPAuthenticationError("Erreur de configuration du serveur d'authentification.")
        except LDAPException as e:
            logger.error(f"Erreur de connexion LDAP - {e}")
            raise LDAPAuthenticationError("Erreur lors de la communication avec le serveur d'authentification.")

        # 4. Rechercher l'utilisateur dans le Base DN
        try:
            search_filter = self.settings.LDAP_SEARCH_FILTER.format(username=safe_username)
            attributes = [
                'displayName', 'cn', 'mail', 'userPrincipalName',
                'sAMAccountName', 'uid', 'memberOf'
            ]

            search_success = search_conn.search(
                search_base=self.settings.LDAP_BASE_DN,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes
            )

            if not search_success or not search_conn.entries:
                logger.warning(f"Utilisateur LDAP non trouvé pour le filtre {search_filter}")
                raise LDAPAuthenticationError("Identifiant ou mot de passe incorrect.")

            user_entry = search_conn.entries[0]
            user_dn = user_entry.entry_dn

        except LDAPAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la recherche LDAP de l'utilisateur {username} - {e}")
            raise LDAPAuthenticationError("Erreur lors de la recherche de l'utilisateur dans l'annuaire.")
        finally:
            if search_conn:
                search_conn.unbind()

        # 5. Deuxième étape : Bind de l'utilisateur pour vérifier son mot de passe
        user_conn: Optional[Connection] = None
        try:
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )

            # Extraire les attributs de l'utilisateur
            display_name = str(getattr(user_entry, 'displayName', None) or getattr(user_entry, 'cn', username))
            email = str(getattr(user_entry, 'mail', None) or "")
            
            groups = []
            if hasattr(user_entry, 'memberOf'):
                groups = [str(g) for g in user_entry.memberOf]

            return User(
                username=username,
                display_name=display_name,
                email=email,
                dn=user_dn,
                groups=groups
            )

        except LDAPBindError:
            logger.warning(f"Mot de passe incorrect pour le DN {user_dn}")
            raise LDAPAuthenticationError("Identifiant ou mot de passe incorrect.")
        except LDAPException as e:
            logger.error(f"Erreur lors de la validation du mot de passe pour {user_dn} - {e}")
            raise LDAPAuthenticationError("Échec de la vérification des identifiants.")
        finally:
            if user_conn and user_conn.bound:
                user_conn.unbind()
