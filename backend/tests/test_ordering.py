from collections import Counter

from app.models import SLOTS
from app.ordering import column_order, page_order

CASES = [f"case_{i:02d}" for i in range(1, 9)]


def test_same_seed_gives_same_order():
    assert page_order(42, CASES, 50) == page_order(42, CASES, 50)
    assert column_order(42, "case_01") == column_order(42, "case_01")
    assert page_order(42, CASES, 50) == page_order(42, list(reversed(CASES)), 50)


def test_different_seeds_give_different_orders():
    assert len({tuple(page_order(s, CASES, 50)) for s in range(50)}) > 30
    assert len({tuple(column_order(s, "case_01")) for s in range(50)}) > 30


def test_page_order_has_no_repeats_and_respects_limit():
    assert sorted(page_order(1, CASES, 50)) == CASES
    assert len(page_order(1, CASES, 3)) == 3


def test_column_order_is_a_permutation_of_the_slots():
    for seed in range(100):
        assert sorted(column_order(seed, "case_03")) == sorted(SLOTS)


def test_column_order_differs_between_pages_for_the_same_rater():
    assert len({tuple(column_order(7, c)) for c in CASES}) > 1


def test_every_slot_lands_in_every_screen_column_about_equally():
    n = 5000
    for column in range(5):
        counts = Counter(column_order(seed, "case_01")[column] for seed in range(n))
        for slot in SLOTS:
            assert 0.17 * n < counts[slot] < 0.23 * n, (column, slot, counts)


def test_first_page_is_spread_over_cases():
    n = 4000
    counts = Counter(page_order(seed, CASES, 50)[0] for seed in range(n))
    for case in CASES:
        assert 0.10 * n < counts[case] < 0.15 * n, counts
