from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, Optional

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


def _normalize_database_url(raw: str) -> str:
    # некоторые платформы дают postgres://
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql://", 1)

    u = make_url(raw)

    # если драйвер не указан — SQLAlchemy по умолчанию берёт psycopg2
    if u.drivername == "postgresql":
        raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)

    return raw


def _make_local_sqlite_url() -> str:
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sqlite_file = data_dir / "database.db"
    return f"sqlite:///{sqlite_file}"


def _try_create_engine(url: str):
    kwargs = {"echo": True, "pool_pre_ping": True}

    # SQLite нужен check_same_thread=False
    if url.startswith("sqlite:///"):
        kwargs["connect_args"] = {"check_same_thread": False}

    try:
        eng = create_engine(url, **kwargs)
        # быстрая проверка “вообще коннектится?”
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        print(f"[db] failed to init engine for {make_url(url).drivername}: {e}")
        return None


def _build_engine():
    # 1) PostgreSQL из DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        normalized = _normalize_database_url(database_url)
        eng = _try_create_engine(normalized)
        if eng is not None:
            print(f"[db] using {make_url(normalized).drivername}")
            return eng

    # 2) SQLite из SQLITE_URL (если вдруг хочешь задавать явно)
    sqlite_url = os.getenv("SQLITE_URL")
    if sqlite_url:
        eng = _try_create_engine(sqlite_url)
        if eng is not None:
            print(f"[db] using {make_url(sqlite_url).drivername}")
            return eng

    # 3) Local sqlite file
    local_sqlite = _make_local_sqlite_url()
    eng = _try_create_engine(local_sqlite)
    if eng is None:
        raise RuntimeError("Could not initialize any database engine (postgres/sqlite/local).")
    print(f"[db] using {make_url(local_sqlite).drivername}")
    return eng


engine = _build_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
