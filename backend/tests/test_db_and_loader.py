import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlmodel import Session, select

from app import service
from app.loader import ManifestError, load_manifest
from app.models import Case, RatingEvent, Volume
from helpers import write_prepared


def test_database_is_created_in_wal_mode(engine):
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA user_version")).scalar() == 1
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert {"case", "volume", "rater", "assignment", "ratingevent"} <= tables


def test_manifest_loads_cases_and_volumes(session):
    assert len(session.exec(select(Case)).all()) == 6
    volumes = session.exec(select(Volume).where(Volume.case_id == "case_01")).all()
    assert sorted(v.slot for v in volumes) == list("ABCDE")
    assert all(v.path == f"volumes/{v.opaque_id}.nii" for v in volumes)


def test_no_table_has_an_origin_column(engine):
    with engine.connect() as conn:
        for table in ("case", "volume", "rater", "assignment", "ratingevent"):
            cols = {r[1].lower() for r in conn.execute(text(f'PRAGMA table_info("{table}")'))}
            assert not cols & {"model", "origin", "source", "is_real", "real", "arch"}, table


def test_loading_twice_keeps_everything(session, settings):
    assert load_manifest(session, settings.prepared_dir) == {"added": 0, "kept": 6}
    assert len(session.exec(select(Volume)).all()) == 30


def test_loader_rejects_volumes_with_different_sizes(tmp_path, session):
    folder = tmp_path / "bad"
    write_prepared(folder, cases=[("case_99", "IXI", "T1")])
    victim = next((folder / "volumes").iterdir())
    victim.write_bytes(b"x" * 10)
    with pytest.raises(ManifestError, match="differ in size"):
        load_manifest(session, folder)


def test_loader_rejects_missing_file(tmp_path, session):
    folder = tmp_path / "bad"
    write_prepared(folder, cases=[("case_99", "IXI", "T1")])
    next((folder / "volumes").iterdir()).unlink()
    with pytest.raises(ManifestError, match="not found"):
        load_manifest(session, folder)


def test_loader_rejects_changed_case(tmp_path, session):
    folder = tmp_path / "other"
    write_prepared(folder, cases=[("case_01", "IXI", "T1")])
    with pytest.raises(ManifestError, match="already loaded"):
        load_manifest(session, folder)


def test_rating_events_are_append_only(session):
    rater = service.create_rater(session)
    session.add(
        RatingEvent(client_event_id="evt-00001", rater_id=rater.id, case_id="case_01", slot="A", score=3)
    )
    session.commit()
    with pytest.raises(DatabaseError, match="append-only"):
        session.exec(text("UPDATE ratingevent SET score = 5"))
    session.rollback()
    with pytest.raises(DatabaseError, match="append-only"):
        session.exec(text("DELETE FROM ratingevent"))


def test_database_rejects_score_out_of_range(session):
    rater = service.create_rater(session)
    session.add(
        RatingEvent(client_event_id="evt-00002", rater_id=rater.id, case_id="case_01", slot="A", score=6)
    )
    with pytest.raises(IntegrityError):
        session.commit()
