import pytest

import e2e_check

pytestmark = pytest.mark.skipif(
    not (e2e_check.DEFAULT_PREPARED / "manifest.json").exists() or not e2e_check.DEFAULT_KEY.exists(),
    reason="needs data/prepared and the testkit answer key",
)


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    return e2e_check.simulate(e2e_check.DEFAULT_PREPARED, tmp_path_factory.mktemp("e2e"))


def test_simulated_rater_matches_the_answer_key(rows):
    key = e2e_check.read_key(e2e_check.DEFAULT_KEY)
    assert e2e_check.compare(rows, key) == []
    assert len(rows) == 40


def test_compare_detects_problems(rows):
    key = e2e_check.read_key(e2e_check.DEFAULT_KEY)
    assert e2e_check.compare(rows[:-1], key)  # a missing rating
    assert e2e_check.compare(rows + [rows[0]], key)  # a duplicated rating
    bad = [dict(r) for r in rows]
    bad[0]["dataset"] = "OUTRO"
    assert e2e_check.compare(bad, key)
