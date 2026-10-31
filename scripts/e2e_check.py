"""End-to-end check (T5.1): a simulated rater answers every case through the HTTP API,
the admin CSV is exported, and the result is compared with the answer key.

Offline tool: it is the only place besides tests that reads answer_key.csv.
Usage (from the repository root):
    python scripts/e2e_check.py [prepared_dir] [answer_key.csv]
"""

import csv
import io
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app import service  # noqa: E402
from app.config import Settings  # noqa: E402
from app.db import init_db, make_engine  # noqa: E402
from app.loader import load_manifest  # noqa: E402
from app.main import create_app  # noqa: E402

DEFAULT_PREPARED = ROOT / "data" / "prepared"
DEFAULT_KEY = (
    ROOT / "radiologist_grading_testkit" / "radiologist_grading_testkit" / "testkit"
    / "_answer_key_do_not_share_with_radiologists" / "answer_key.csv"
)
PASSWORD = "e2e-password"


def read_key(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def simulate(prepared_dir: Path, workdir: Path, seed: int = 0) -> list[dict]:
    """Rate every slot of every page once, then a few corrections. Returns the exported rows."""
    settings = Settings(
        db_path=workdir / "e2e.db", prepared_dir=prepared_dir, pages_per_rater=1000,
        admin_password=PASSWORD,
    )
    engine = make_engine(settings.db_path)
    init_db(engine)
    with Session(engine) as session:
        load_manifest(session, prepared_dir)
        token = service.create_rater(session, name="Simulated rater").token
    client = TestClient(create_app(settings))
    rng = random.Random(seed)

    info = client.get(f"/api/session/{token}").json()
    n = 0

    def rate(position: int, slot: str, score: int) -> None:
        nonlocal n
        n += 1
        r = client.post(f"/api/session/{token}/rating", json={
            "client_event_id": f"e2e-{n:06d}", "position": position, "slot": slot,
            "score": score, "viewer_state": {"slices": {"axial": 1}},
        })
        r.raise_for_status()

    for position in range(1, info["total_pages"] + 1):
        page = client.get(f"/api/session/{token}/page/{position}").json()
        for col in page["columns"]:
            rate(position, col["slot"], rng.randint(1, 5))
    assert client.get(f"/api/session/{token}").json()["finished"]

    r = client.get("/api/admin/export.csv", auth=("admin", PASSWORD))
    r.raise_for_status()
    engine.dispose()  # release the SQLite files so Windows can delete the folder
    return list(csv.DictReader(io.StringIO(r.text)))


def compare(rows: list[dict], key: list[dict]) -> list[str]:
    """Problems found; empty means everything matches."""
    problems = []
    expected: dict[str, dict] = {}
    for k in key:
        expected.setdefault(k["case"], {"slots": set(), "dataset": k["dataset"], "seq": k["modality"]})
        expected[k["case"]]["slots"].add(k["slot"])
    if len(key) != 5 * len(expected):
        problems.append(f"key has {len(key)} rows for {len(expected)} cases (expected 5 each)")

    got_cases = {r["case"] for r in rows}
    if got_cases != set(expected):
        problems.append(f"cases differ: missing {sorted(set(expected) - got_cases)}, "
                        f"extra {sorted(got_cases - set(expected))}")
    if len(rows) != len(key):
        problems.append(f"{len(rows)} ratings exported, expected {len(key)}")

    per_pair = Counter((r["case"], r["slot"]) for r in rows)
    for case, e in expected.items():
        for slot in sorted(e["slots"]):
            if per_pair[(case, slot)] != 1:
                problems.append(f"{case}/{slot}: {per_pair[(case, slot)]} ratings, expected 1")
    for r in rows:
        e = expected.get(r["case"])
        if e is None:
            continue
        if r["slot"] not in e["slots"]:
            problems.append(f"{r['case']}: slot {r['slot']} not in the answer key")
        if (r["dataset"], r["sequence"]) != (e["dataset"], e["seq"]):
            problems.append(f"{r['case']}: dataset/sequence differ from the answer key")
        if not 1 <= int(r["score"]) <= 5:
            problems.append(f"{r['case']}/{r['slot']}: score {r['score']} out of range")
        if not 1 <= int(r["screen_position"]) <= 5:
            problems.append(f"{r['case']}/{r['slot']}: screen_position {r['screen_position']}")
    for case in expected:
        positions = sorted(int(r["screen_position"]) for r in rows if r["case"] == case)
        if positions != [1, 2, 3, 4, 5]:
            problems.append(f"{case}: screen positions {positions}, expected 1 to 5 once each")
    return problems


def main(argv: list[str]) -> int:
    prepared = Path(argv[1]) if len(argv) > 1 else DEFAULT_PREPARED
    key_path = Path(argv[2]) if len(argv) > 2 else DEFAULT_KEY
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        rows = simulate(prepared, Path(tmp))
    key = read_key(key_path)
    problems = compare(rows, key)
    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1
    print(f"OK: {len({r['case'] for r in rows})} cases, {len(rows)} ratings, "
          "slots and screen positions match the answer key")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
