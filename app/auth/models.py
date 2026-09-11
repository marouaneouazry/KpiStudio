from pydantic import BaseModel, Field
from typing import Optional, List

class LoginRequest(BaseModel):
    username: str = Field(..., description="Nom d'utilisateur LDAP ou Active Directory")
    password: str = Field(..., description="Mot de passe utilisateur")

class User(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    dn: Optional[str] = None
    groups: List[str] = []

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
