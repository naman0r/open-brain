from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db.session import _session_error, engine


def main() -> None:
    if _session_error is not None:
        raise _session_error
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(config_path))
    if not cfg:
        raise RuntimeError("SUPABASE_DB_URL is required. Copy .env.example to .env and set it.")
    if engine is None:
        raise RuntimeError("SUPABASE_DB_URL is required. Copy .env.example to .env and set it.")

    with engine.connect() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        has_legacy_schema = "memories" in tables
        has_alembic_table = "alembic_version" in tables

    if has_legacy_schema and not has_alembic_table:
        # Existing schema created pre-Alembic. Mark current revision as baseline.
        command.stamp(cfg, "head")
        print("Detected existing legacy schema. Stamped Alembic revision to head.")
        return

    command.upgrade(cfg, "head")
    print("Database initialized via Alembic migrations.")


if __name__ == "__main__":
    main()
