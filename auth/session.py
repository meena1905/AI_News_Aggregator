import hashlib
import os
import secrets
import time
from fastapi import HTTPException, Request, Response
SESSION_COOKIE = "session_token"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
_sessions: dict[str, dict] = {}
def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[hash_token(token)] = {
        "user_id": user_id,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    return token
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
def get_session_user_id(token: str | None) -> str | None:
    if not token:
        return None
    session = _sessions.get(hash_token(token))
    if not session:
        return None
    if session["expires_at"] < time.time():
        _sessions.pop(hash_token(token), None)
        return None
    return session["user_id"]
def require_user(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    user_id = get_session_user_id(token)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    return user_id
def set_session_cookie(response: Response, token: str) -> None:
    production = os.getenv("ENVIRONMENT", "development") == "production"

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=production,
        samesite="lax",
        path="/",
    )
def clear_session(response: Response, token: str | None) -> None:
    if token:
        _sessions.pop(hash_token(token), None)
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
    )