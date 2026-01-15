"""
RealGo MVP - Autenticación JWT con JWKS (Neon Auth)

Este módulo maneja la verificación de tokens JWT usando JWKS.
Soporta EdDSA/Ed25519 (usado por Neon Auth) y RS256.
"""

import os
import base64
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from jose.constants import ALGORITHMS
from pydantic import BaseModel

# Para Ed25519
try:
    from nacl.signing import VerifyKey
    from nacl.encoding import RawEncoder
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False


# Security scheme
security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Usuario autenticado actual."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    claims: dict = {}


def get_jwks_url() -> Optional[str]:
    """Obtiene la URL del JWKS desde variables de entorno."""
    # Soporta múltiples nombres de variable
    return (
        os.getenv("JWKS_URL") or 
        os.getenv("NEON_AUTH_JWKS_URL") or 
        os.getenv("BETTER_AUTH_JWKS_URL")
    )


class JWKSManager:
    """Gestiona la obtención y cache del JWKS."""
    
    def __init__(self):
        self._jwks_cache: Optional[dict] = None
        self._jwks_url: Optional[str] = None
    
    @property
    def jwks_url(self) -> Optional[str]:
        """Obtiene la URL del JWKS (lee de env cada vez por si cambia)."""
        if self._jwks_url is None:
            self._jwks_url = get_jwks_url()
        return self._jwks_url
    
    def refresh_url(self):
        """Fuerza re-lectura de la URL del JWKS."""
        self._jwks_url = get_jwks_url()
    
    @property
    def is_configured(self) -> bool:
        """Verifica si el JWKS está configurado."""
        url = self.jwks_url
        return url is not None and len(url) > 0
    
    def get_jwks(self) -> dict:
        """Obtiene el JWKS (con cache)."""
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service not configured (JWKS_URL not set)"
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


def decode_ed25519_token(token: str, jwk: dict) -> dict:
    """
    Decodifica un token JWT firmado con Ed25519.
    python-jose no soporta EdDSA nativamente, así que lo hacemos manualmente.
    """
    if not NACL_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyNaCl not installed - Ed25519 not supported"
        )
    
    try:
        # Separar las partes del JWT
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Decodificar la clave pública Ed25519
        x = jwk.get("x")
        if not x:
            raise ValueError("JWK missing 'x' parameter")
        
        # Añadir padding si es necesario
        padding = 4 - len(x) % 4
        if padding != 4:
            x += "=" * padding
        
        public_key_bytes = base64.urlsafe_b64decode(x)
        verify_key = VerifyKey(public_key_bytes)
        
        # Decodificar la firma
        sig_padding = 4 - len(signature_b64) % 4
        if sig_padding != 4:
            signature_b64 += "=" * sig_padding
        signature = base64.urlsafe_b64decode(signature_b64)
        
        # Verificar la firma
        message = f"{header_b64}.{payload_b64}".encode()
        verify_key.verify(message, signature)
        
        # Decodificar el payload
        payload_padding = 4 - len(payload_b64) % 4
        if payload_padding != 4:
            payload_b64 += "=" * payload_padding
        
        import json
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        return payload
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Ed25519 token: {str(e)}"
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
    alg = key.get("alg", "RS256")
    
    try:
        # EdDSA (Ed25519) - usado por Neon Auth
        if alg == "EdDSA":
            payload = decode_ed25519_token(token, key)
        else:
            # RS256, ES256, etc - usar python-jose
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg],
                options={
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
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
