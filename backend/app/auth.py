"""Small fail-closed bearer-token guard for private API endpoints."""
import hmac
import os

from fastapi import Header, HTTPException, status


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_ACCESS_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="API access is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing bearer token", headers={"WWW-Authenticate": "Bearer"})
