"""Fail-closed bearer-token guard with Swagger UI security integration."""
import hmac
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# auto_error=False lets this dependency return our own consistent 401 response,
# while registering HTTP Bearer authentication in OpenAPI/Swagger UI.
bearer_scheme = HTTPBearer(auto_error=False)


def require_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    expected = os.getenv("API_ACCESS_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="API access is not configured")

    supplied = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
