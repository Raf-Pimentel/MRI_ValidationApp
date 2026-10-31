from pathlib import Path

from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine

from .models import SCHEMA_VERSION


def make_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    return engine


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(f"PRAGMA user_version={SCHEMA_VERSION}"))
        # Ratings are append-only: corrections are new rows, never edits.
        for op in ("UPDATE", "DELETE"):
            conn.execute(
                text(
                    f"CREATE TRIGGER IF NOT EXISTS rating_event_no_{op.lower()} "
                    f"BEFORE {op} ON ratingevent BEGIN "
                    "SELECT RAISE(ABORT, 'rating_event is append-only'); END"
                )
            )


def get_session(engine):
    with Session(engine) as session:
        yield session
