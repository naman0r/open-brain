from sqlalchemy import text

from app.db.models import Base
from app.db.session import _session_error, engine


def main() -> None:
    if _session_error is not None:
        raise _session_error
    if engine is None:
        raise RuntimeError("SUPABASE_DB_URL is required. Copy .env.example to .env and set it.")
    with engine.begin() as connection:
        connection.execute(text("create extension if not exists vector"))
    Base.metadata.create_all(bind=engine)
    print("Database initialized (vector extension + tables).")


if __name__ == "__main__":
    main()
