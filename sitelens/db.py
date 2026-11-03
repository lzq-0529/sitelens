from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from . import config
from .models import Base

engine = None
SessionLocal: sessionmaker | None = None


def init_db(url: str | None = None) -> None:
    global engine, SessionLocal
    url = url or config.database_url()
    sqlite = url.startswith("sqlite")
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False} if sqlite else {})
    if sqlite:

        @event.listens_for(engine, "connect")
        def _pragmas(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    assert SessionLocal is not None, "init_db() first"
    with SessionLocal() as session:
        yield session
