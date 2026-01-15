"""
RealGo MVP - Autenticación JWT con JWKS (Better Auth)

Este módulo maneja la verificación de tokens JWT usando JWKS.
"""

import os
from typing import Optional
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from pydantic import BaseModel


# Security scheme
security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Usuario autenticado actual."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    claims: dict = {}


class JWKSManager:
    """Gestiona la obtención y cache del JWKS."""
    
    def __init__(self):
        self._jwks_cache: Optional[dict] = None
        self._jwks_url = os.getenv("BETTER_AUTH_JWKS_URL")
    
    @property
    def jwks_url(self) -> Optional[str]:
        """Obtiene la URL del JWKS (puede cambiar en runtime)."""
        if self._jwks_url is None:
            self._jwks_url = os.getenv("BETTER_AUTH_JWKS_URL")
        return self._jwks_url
    
    @property
    def is_configured(self) -> bool:
        """Verifica si el JWKS está configurado."""
        return self.jwks_url is not None and len(self.jwks_url) > 0
    
    def get_jwks(self) -> dict:
        """Obtiene el JWKS (con cache)."""
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service not configured"
            )
        
        if self._jwks_cache is None:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(self.jwks_url)
                    response.raise_for_status()
                    self._jwks_cache = response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Could not fetch JWKS: {str(e)}"
                )
        
        return self._jwks_cache
    
    def clear_cache(self):
        """Limpia el cache del JWKS."""
        self._jwks_cache = None
    
    def get_signing_key(self, token: str) -> dict:
        """Obtiene la clave de firma para un token."""
        try:
            header = jwt.get_unverified_header(token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
        
        kid = header.get("kid")
        jwks = self.get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        # Si no encontramos la key, limpiamos cache e intentamos de nuevo
        self.clear_cache()
        jwks = self.get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signing key not found"
        )


# Instancia global del manager
jwks_manager = JWKSManager()


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """
    Dependency que extrae y valida el usuario del token JWT.
    
    Raises:
        HTTPException 401: Si el token es inválido o no está presente
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = creds.credentials
    
    # Verificar si auth está configurado
    if not jwks_manager.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    # Obtener clave de firma
    key = jwks_manager.get_signing_key(token)
    
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            options={
                "verify_aud": False,  # Configurar según necesidad
                "verify_iss": False,  # Configurar según necesidad
            },
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID (sub claim)"
        )
    
    return CurrentUser(
        user_id=user_id,
        email=payload.get("email"),
        name=payload.get("name"),
        role=payload.get("role"),
        claims=payload,
    )


async def get_current_user_optional(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """
    Dependency opcional - retorna None si no hay token.
    Útil para endpoints que funcionan con o sin autenticación.
    """
    if creds is None:
        return None
    
    if not jwks_manager.is_configured:
        return None
    
    try:
        return await get_current_user(creds)
    except HTTPException:
        return None


def require_role(*allowed_roles: str):
    """
    Dependency factory que verifica que el usuario tenga uno de los roles permitidos.
    
    Uso:
        @app.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint():
            ...
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
