import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.db import init_db, make_engine  # noqa: E402
from app.loader import load_manifest  # noqa: E402
from app.main import create_app  # noqa: E402
from helpers import write_prepared  # noqa: E402

@pytest.fixture
def settings(tmp_path):
    write_prepared(tmp_path / "prepared")
    return Settings(db_path=tmp_path / "app.db", prepared_dir=tmp_path / "prepared", pages_per_rater=50)


@pytest.fixture
def engine(settings):
    engine = make_engine(settings.db_path)
    init_db(engine)
    with Session(engine) as session:
        load_manifest(session, settings.prepared_dir)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(settings, engine):
    return TestClient(create_app(settings))
