"""Sign-in for the console. There is no public registration."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import AuditLog, SessionRow, User

OWNER = "owner"
VIEWER = "viewer"
ROLES = (OWNER, VIEWER)
_ITERATIONS = 310_000
_LOGIN_WINDOW = 900
_LOGIN_MAX_FAILURES = 8
_failures: dict[str, list[float]] = {}
_failures_lock = Lock()


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), _ITERATIONS).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)).hex()
    return hmac.compare_digest(actual, digest)


def check_password_strength(password: str) -> None:
    if len(password) < 10:
        raise HTTPException(status_code=400, detail="密码至少 10 位")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(db: Session, username: str, password: str, *, role: str = VIEWER, display_name: str = "") -> User:
    username = username.strip()
    if not username or len(username) > 64:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="角色只能是 owner 或 viewer")
    check_password_strength(password)
    if db.scalar(select(User).where(User.username == username)) is not None:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        id=new_id(),
        username=username,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name.strip()[:80] or username,
    )
    db.add(user)
    db.flush()
    return user


def audit(db: Session, user: User | None, action: str, detail: str = "") -> None:
    db.add(AuditLog(user_id=user.id if user else "", action=action, detail=detail[:2000]))


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else ""
    if peer in _LOOPBACK:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        return forwarded or peer
    return peer or "?"


def _login_key(request: Request, username: str) -> str:
    return f"{client_ip(request)}:{username.lower()}"


def check_login_allowed(request: Request, username: str) -> None:
    cutoff = monotonic() - _LOGIN_WINDOW
    with _failures_lock:
        recent = [stamp for stamp in _failures.get(_login_key(request, username), []) if stamp >= cutoff]
        _failures[_login_key(request, username)] = recent
        if len(recent) >= _LOGIN_MAX_FAILURES:
            raise HTTPException(status_code=429, detail="失败次数过多，请 15 分钟后再试")


def record_login_failure(request: Request, username: str) -> None:
    with _failures_lock:
        _failures.setdefault(_login_key(request, username), []).append(monotonic())


def start_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    db.add(
        SessionRow(
            id=new_id(),
            user_id=user.id,
            token_hash=_token_hash(token),
            expires_at=utcnow() + timedelta(days=config.SESSION_DAYS),
        )
    )
    user.last_login_at = utcnow()
    response.set_cookie(
        config.SESSION_COOKIE,
        token,
        max_age=config.SESSION_DAYS * 86400,
        httponly=True,
        samesite="strict",
        secure=config.cookie_secure(),
        path="/",
    )


def end_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(config.SESSION_COOKIE)
    if token:
        row = db.scalar(select(SessionRow).where(SessionRow.token_hash == _token_hash(token)))
        if row is not None:
            db.delete(row)
    response.delete_cookie(config.SESSION_COOKIE, path="/")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(config.SESSION_COOKIE)
    if token:
        row = db.scalar(select(SessionRow).where(SessionRow.token_hash == _token_hash(token)))
        if row is not None and as_utc(row.expires_at) > utcnow():
            user = db.get(User, row.user_id)
            if user is not None and not user.disabled:
                return user
    raise HTTPException(status_code=401, detail="请先登录")


def owner_user(user: User = Depends(current_user)) -> User:
    if user.role != OWNER:
        raise HTTPException(status_code=403, detail="只有管理员可以操作，你的账号只能查看")
    return user


def user_view(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "disabled": user.disabled,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
