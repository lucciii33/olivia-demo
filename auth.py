"""Authentication: accepts EITHER an API key OR a Bearer token (either one is enough)."""
import os
from fastapi import Header, HTTPException, status

# Configure via environment. Defaults are for local demo only.
API_KEY = os.getenv("API_KEY", "demo-api-key-123")
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "demo-bearer-token-abc")


async def require_auth(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Pass if a valid X-API-Key header OR a valid Bearer token is present.

    Only one of the two is required.
    """
    # Option A: API key
    if x_api_key and x_api_key == API_KEY:
        return {"method": "api_key"}

    # Option B: Bearer token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token == BEARER_TOKEN:
            return {"method": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid credentials. Provide X-API-Key OR Authorization: Bearer <token>.",
        headers={"WWW-Authenticate": "Bearer"},
    )
