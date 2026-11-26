import secrets

from fastapi import Cookie, Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import SecurityError, SessionClaims, SessionSigner

SESSION_COOKIE = "commandos_session"
CSRF_COOKIE = "commandos_csrf"


def require_owner(
    commandos_session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> SessionClaims:
    if not commandos_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        claims = SessionSigner(settings.session_secret.get_secret_value()).verify(commandos_session)
    except SecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from exc
    if claims.email.lower() != settings.owner_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")
    return claims


def require_csrf(
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    commandos_csrf: str | None = Cookie(default=None),
    _claims: SessionClaims = Depends(require_owner),
) -> None:
    if (
        not x_csrf_token
        or not commandos_csrf
        or not secrets.compare_digest(x_csrf_token, commandos_csrf)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
