from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from crypto_mas.infrastructure.config.settings import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> bool:
    """Verify the X-API-Key header against the configured api_security_key.

    If api_security_key is empty in settings, authentication is bypassed for development.
    If configured, raises 401 Unauthorized when key is missing or invalid.
    """
    settings = get_settings()
    if not settings.api_security_key:
        return True

    if not api_key or api_key != settings.api_security_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    return True
