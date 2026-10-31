"""Reproducible shuffles. Same seed, same order; nothing here knows what a slot is."""

import random

from .models import SLOTS


def page_order(seed: int, case_ids: list[str], pages: int) -> list[str]:
    """Cases for one rater, in the order they will see them."""
    rng = random.Random(f"pages:{seed}")
    ids = sorted(case_ids)
    rng.shuffle(ids)
    return ids[:pages]


def column_order(seed: int, case_id: str) -> list[str]:
    """Slots from the left-most screen column to the right-most, for one page."""
    rng = random.Random(f"columns:{seed}:{case_id}")
    slots = list(SLOTS)
    rng.shuffle(slots)
    return slots
