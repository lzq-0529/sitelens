from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Console accounts. ``owner`` manages everything; ``viewer`` can only look."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[str] = mapped_column(String(36), default="")
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text, default="")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    name: Mapped[str] = mapped_column(String(40), index=True)
    visitor_id: Mapped[str] = mapped_column(String(40), index=True)
    region: Mapped[str] = mapped_column(String(16), default="cn", index=True)
    path: Mapped[str] = mapped_column(String(512), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    referrer: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(80), default="")
    host: Mapped[str] = mapped_column(String(160), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(Text, default="")
    device: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(16), default="human", index=True)
    account: Mapped[str] = mapped_column(String(120), default="")
    props: Mapped[str] = mapped_column(Text, default="{}")


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    region: Mapped[str] = mapped_column(String(16), default="cn", index=True)
    kind: Mapped[str] = mapped_column(String(16), default="human", index=True)
    place: Mapped[str] = mapped_column(String(120), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    device: Mapped[str] = mapped_column(String(160), default="")
    referrer: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(80), default="")
    account: Mapped[str] = mapped_column(String(120), default="", index=True)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    views: Mapped[int] = mapped_column(Integer, default=0)
    viewed_item: Mapped[bool] = mapped_column(Boolean, default=False)
    added_cart: Mapped[bool] = mapped_column(Boolean, default=False)
    began_checkout: Mapped[bool] = mapped_column(Boolean, default=False)
    ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")


class Crawl(Base):
    __tablename__ = "crawls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    region: Mapped[str] = mapped_column(String(16), default="cn", index=True)
    engine: Mapped[str] = mapped_column(String(32), default="", index=True)
    label: Mapped[str] = mapped_column(String(80), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    path: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[int] = mapped_column(Integer, default=200)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[str] = mapped_column(String(16), default="unchecked")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    sku: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(160), default="")
    region: Mapped[str] = mapped_column(String(16), default="cn")
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    channel: Mapped[str] = mapped_column(String(32), default="")
    customer: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(16), default="manual")
    visitor_id: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(16), default="paid")


class GeoCheck(Base):
    __tablename__ = "geo_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    model: Mapped[str] = mapped_column(String(80), default="")
    source_mode: Mapped[str] = mapped_column(String(32), default="grok")
    query: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    scored: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
