import hmac
import uuid
from fastapi import HTTPException, Request, Header, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import settings

limiter = Limiter(key_func=get_remote_address)


def get_client_id(x_client_id: str = Header(None)) -> str:
    if not x_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Client-ID header is required"
        )
    try:
        uuid.UUID(x_client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Client-ID must be a valid UUID"
        )
    return x_client_id


def verify_admin_token(authorization: str = Header(None)) -> bool:
    if not settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Admin functionality is not enabled"
        )
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token"
        )
    token = authorization[7:]
    if not hmac.compare_digest(token, settings.ADMIN_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token"
        )
    return True


def is_private_ip(url: str) -> bool:
    private_ranges = [
        "10.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
        "192.168.",
        "127.",
        "::1",
        "localhost"
    ]
    url_lower = url.lower()
    for private in private_ranges:
        if private in url_lower:
            return True
    return False
