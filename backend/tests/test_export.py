import dataclasses
import io
import json

import pytest
from fastapi.testclient import TestClient

from app import service
from app.main import create_app
from test_api import rate

PASSWORD = "s3nha-de-teste"
URL = "/api/admin/export.csv"


@pytest.fixture
def admin_client(settings, engine):
    return TestClient(create_app(dataclasses.replace(settings, admin_password=PASSWORD)))


@pytest.fixture
def token(session):
    return service.create_rater(session, name="Dra. Teste").token


# T4.1 -- CSV

def test_csv_opens_in_pandas_with_one_row_per_event(admin_client, token):
    pd = pytest.importorskip("pandas")
    state = {"slices": {"axial": 12}, "brightness": 0.5}
    rate(admin_client, token, 1, "A", 3, "evt-000001", viewer_state=state)
    rate(admin_client, token, 1, "A", 4, "evt-000002", comment='bom, "quase" real\nlinha 2')
    rate(admin_client, token, 2, "C", 5, "evt-000003")

    r = admin_client.get(URL, auth=("admin", PASSWORD))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    df = pd.read_csv(io.StringIO(r.text))

    assert len(df) == 3  # a correction is a new row, not an update
    assert list(df["score"]) == [3, 4, 5]
    assert list(df["slot"]) == ["A", "A", "C"]
    assert list(df["page_position"]) == [1, 1, 2]
    assert df["screen_position"].between(1, 5).all()
    assert df.loc[1, "comment"] == 'bom, "quase" real\nlinha 2'
    assert json.loads(df.loc[0, "viewer_state"]) == state
    assert df["viewer_state"].isna().tolist() == [False, True, True]


def test_screen_position_matches_the_page_column_order(admin_client, token):
    page = admin_client.get(f"/api/session/{token}/page/1").json()
    for i, col in enumerate(page["columns"]):
        rate(admin_client, token, 1, col["slot"], 3, f"evt-col-{i}-xx")
    rows = admin_client.get(URL, auth=("x", PASSWORD)).text.splitlines()[1:]
    header = admin_client.get(URL, auth=("x", PASSWORD)).text.splitlines()[0].split(",")
    slot_i, pos_i = header.index("slot"), header.index("screen_position")
    got = {r.split(",")[slot_i]: int(r.split(",")[pos_i]) for r in rows}
    assert got == {c["slot"]: i + 1 for i, c in enumerate(page["columns"])}


def test_csv_has_no_origin_information(admin_client, token):
    rate(admin_client, token, 1, "A", 3, "evt-000001")
    header = admin_client.get(URL, auth=("x", PASSWORD)).text.splitlines()[0]
    for word in ("opaque", "path", "model", "real", "token", "seed"):
        assert word not in header


def test_empty_database_exports_only_the_header(admin_client):
    r = admin_client.get(URL, auth=("x", PASSWORD))
    assert r.status_code == 200
    assert len(r.text.splitlines()) == 1


# T4.2 -- password

def test_export_needs_the_password(admin_client, token):
    rate(admin_client, token, 1, "A", 3, "evt-000001")
    assert admin_client.get(URL).status_code == 401
    assert admin_client.get(URL, auth=("admin", "errada")).status_code == 401
    assert admin_client.get(URL, auth=("admin", "")).status_code == 401
    assert "WWW-Authenticate" in admin_client.get(URL).headers
    assert admin_client.get(URL, auth=("admin", PASSWORD)).status_code == 200


def test_export_is_off_when_no_password_is_configured(client, token):
    rate(client, token, 1, "A", 3, "evt-000001")
    assert client.get(URL).status_code == 404
    assert client.get(URL, auth=("admin", "")).status_code == 404
    assert client.get(URL, auth=("admin", "qualquer")).status_code == 404


def test_password_is_read_from_the_environment(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("MRI_ADMIN_PASSWORD", raising=False)
    assert Settings.from_env().admin_password is None
    monkeypatch.setenv("MRI_ADMIN_PASSWORD", "abc")
    assert Settings.from_env().admin_password == "abc"
    monkeypatch.setenv("MRI_ADMIN_PASSWORD", "")
    assert Settings.from_env().admin_password is None
