import json

import pytest
from sqlmodel import select

from app import service
from app.models import RatingEvent, Volume


@pytest.fixture
def token(session):
    return service.create_rater(session, name="Dra. Teste").token


def rate(client, token, position, slot, score, event_id, **extra):
    body = {"client_event_id": event_id, "position": position, "slot": slot, "score": score, **extra}
    return client.post(f"/api/session/{token}/rating", json=body)


def rate_page(client, token, position, prefix="p"):
    for i, slot in enumerate("ABCDE"):
        assert rate(client, token, position, slot, 3, f"{prefix}{position}-{i}-xxxx").status_code == 200


# T2.3 -- token and session

def test_valid_token_opens_the_session(client, token):
    r = client.get(f"/api/session/{token}")
    assert r.status_code == 200
    assert r.json() == {
        "name": "Dra. Teste", "total_pages": 6, "completed_pages": 0, "next_position": 1, "finished": False
    }


def test_invalid_token_gives_a_clear_error(client):
    r = client.get("/api/session/not-a-real-token")
    assert r.status_code == 404
    assert "Link inválido" in r.json()["detail"]
    assert client.get("/api/session/not-a-real-token/page/1").status_code == 404
    assert rate(client, "not-a-real-token", 1, "A", 3, "evt-aaaaaa").status_code == 404


def test_each_rater_gets_their_own_token_and_seed(session):
    a, b = service.create_rater(session), service.create_rater(session)
    assert a.token != b.token and a.seed != b.seed


def test_first_entry_fixes_the_order(client, token):
    first = [client.get(f"/api/session/{token}/page/{p}").json() for p in range(1, 7)]
    again = [client.get(f"/api/session/{token}/page/{p}").json() for p in range(1, 7)]
    assert first == again


# T2.5 -- page and volume

def test_page_json_has_only_slot_sequence_and_opaque_urls(client, session, token):
    page = client.get(f"/api/session/{token}/page/1").json()
    assert set(page) == {"position", "total_pages", "sequence", "columns", "ratings"}
    assert sorted(c["slot"] for c in page["columns"]) == list("ABCDE")
    assert all(set(c) == {"slot", "url"} for c in page["columns"])
    opaque_ids = {v.opaque_id for v in session.exec(select(Volume))}
    assert {c["url"].removeprefix("/api/vol/") for c in page["columns"]} <= opaque_ids
    text = json.dumps(page)
    for word in ("case_", "dataset", "BraTS", "IXI", ".nii", "real", "model"):
        assert word not in text


def test_unknown_page_is_404(client, token):
    assert client.get(f"/api/session/{token}/page/99").status_code == 404
    assert client.get(f"/api/session/{token}/page/0").status_code == 404


def test_volume_is_served_uncompressed_with_uniform_size(client, token):
    page = client.get(f"/api/session/{token}/page/1").json()
    sizes = set()
    for col in page["columns"]:
        r = client.get(col["url"], headers={"Accept-Encoding": "gzip, br"})
        assert r.status_code == 200
        assert "content-encoding" not in r.headers
        assert "content-disposition" not in r.headers
        sizes.add(int(r.headers["content-length"]))
        assert len(r.content) == int(r.headers["content-length"])
    assert len(sizes) == 1


def test_unknown_volume_is_404_and_paths_cannot_escape(client):
    assert client.get("/api/vol/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/vol/..%2Fmanifest.json").status_code == 404


# T2.6 -- ratings

def test_rating_is_stored_and_shown_back_on_the_page(client, session, token):
    r = rate(client, token, 1, "B", 4, "evt-000001", comment="borrado", viewer_state={"slice": {"axial": 5}})
    assert r.status_code == 200
    page = client.get(f"/api/session/{token}/page/1").json()
    assert page["ratings"] == {"B": {"score": 4, "comment": "borrado"}}
    event = session.exec(select(RatingEvent)).one()
    assert json.loads(event.viewer_state_json) == {"slice": {"axial": 5}}


def test_resending_the_same_event_does_not_duplicate(client, session, token):
    first = rate(client, token, 1, "A", 4, "evt-000001").json()
    second = rate(client, token, 1, "A", 4, "evt-000001").json()
    assert first["event_id"] == second["event_id"]
    assert len(session.exec(select(RatingEvent)).all()) == 1


def test_correction_adds_a_new_row_and_becomes_current(client, session, token):
    rate(client, token, 1, "A", 2, "evt-000001")
    rate(client, token, 1, "A", 5, "evt-000002")
    assert [e.score for e in session.exec(select(RatingEvent).order_by(RatingEvent.id))] == [2, 5]
    assert client.get(f"/api/session/{token}/page/1").json()["ratings"]["A"]["score"] == 5


@pytest.mark.parametrize("score", [0, 6, -1, 3.5, "x"])
def test_score_outside_1_to_5_is_rejected(client, session, token, score):
    assert rate(client, token, 1, "A", score, "evt-000001").status_code == 422
    assert session.exec(select(RatingEvent)).all() == []


def test_bad_slot_position_and_event_id_are_rejected(client, token):
    assert rate(client, token, 1, "Z", 3, "evt-000001").status_code == 422
    assert rate(client, token, 99, "A", 3, "evt-000001").status_code == 404
    assert rate(client, token, 1, "A", 3, "x").status_code == 422
    assert rate(client, token, 1, "A", 3, "evt-000001", viewer_state={"k": "x" * 5000}).status_code == 422


def test_event_id_of_another_rater_is_refused(client, session, token):
    other = service.create_rater(session).token
    assert rate(client, token, 1, "A", 3, "evt-000001").status_code == 200
    assert rate(client, other, 1, "A", 3, "evt-000001").status_code == 409


def test_ratings_of_one_rater_do_not_show_for_another(client, session, token):
    other = service.create_rater(session).token
    rate(client, token, 1, "A", 3, "evt-000001")
    case_of_other_p1 = client.get(f"/api/session/{other}/page/1").json()
    assert case_of_other_p1["ratings"] == {}


# T2.7 -- resume

def test_resume_goes_to_first_page_without_a_complete_rating(client, token):
    rate_page(client, token, 1)
    rate_page(client, token, 2)
    # page 3 left with 4 of 5 slots rated
    for i, slot in enumerate("ABCD"):
        rate(client, token, 3, slot, 4, f"q3-{i}-xxxx")
    s = client.get(f"/api/session/{token}").json()
    assert s["next_position"] == 3 and s["completed_pages"] == 2 and not s["finished"]


def test_resume_skips_back_to_an_earlier_incomplete_page(client, token):
    rate_page(client, token, 2)
    assert client.get(f"/api/session/{token}").json()["next_position"] == 1


def test_correcting_a_rating_does_not_undo_completeness(client, token):
    rate_page(client, token, 1)
    rate(client, token, 1, "A", 1, "evt-fix-001")
    assert client.get(f"/api/session/{token}").json()["completed_pages"] == 1


def test_finished_when_every_page_is_complete(client, token):
    for p in range(1, 7):
        rate_page(client, token, p)
    s = client.get(f"/api/session/{token}").json()
    assert s["finished"] and s["next_position"] is None and s["completed_pages"] == 6
