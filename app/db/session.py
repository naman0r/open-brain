from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

db_url = settings.supabase_db_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

_session_error: RuntimeError | None = None
if db_url and "#@" in db_url:
    _session_error = RuntimeError(
        "SUPABASE_DB_URL appears malformed. If your DB password contains special characters "
        "(e.g. #, @, !), URL-encode it before placing it in the connection string."
    )

engine = create_engine(db_url, pool_pre_ping=True) if db_url and _session_error is None else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def get_db() -> Generator[Session, None, None]:
    if _session_error is not None:
        raise _session_error
    if SessionLocal is None:
        raise RuntimeError("SUPABASE_DB_URL is required. Copy .env.example to .env and set it.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
