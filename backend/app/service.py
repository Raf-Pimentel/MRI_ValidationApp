import json
import secrets

from sqlmodel import Session, select

from .models import SLOTS, Assignment, Case, Rater, RatingEvent, Volume
from .ordering import column_order, page_order


def create_rater(
    session: Session, name: str | None = None, email: str | None = None
) -> Rater:
    rater = Rater(
        token=secrets.token_urlsafe(16),
        name=name,
        email=email,
        seed=secrets.randbits(63),
    )
    session.add(rater)
    session.commit()
    session.refresh(rater)
    return rater


def get_rater(session: Session, token: str) -> Rater | None:
    return session.exec(select(Rater).where(Rater.token == token)).first()


def _assignments(session: Session, rater: Rater) -> list[Assignment]:
    return list(
        session.exec(
            select(Assignment)
            .where(Assignment.rater_id == rater.id)
            .order_by(Assignment.position)
        )
    )


def ensure_assignments(session: Session, rater: Rater, pages: int) -> list[Assignment]:
    """Fix the rater's page and column order on first entry; later calls reuse it."""
    rows = _assignments(session, rater)
    if rows:
        return rows
    case_ids = list(session.exec(select(Case.id)))
    for position, case_id in enumerate(page_order(rater.seed, case_ids, pages), start=1):
        session.add(
            Assignment(
                rater_id=rater.id,
                position=position,
                case_id=case_id,
                column_order=column_order(rater.seed, case_id),
            )
        )
    session.commit()
    return _assignments(session, rater)


def current_ratings(session: Session, rater_id: int, case_id: str) -> dict[str, RatingEvent]:
    """Latest event per slot."""
    events = session.exec(
        select(RatingEvent)
        .where(RatingEvent.rater_id == rater_id, RatingEvent.case_id == case_id)
        .order_by(RatingEvent.id)
    )
    return {e.slot: e for e in events}


def _rated_pairs(session: Session, rater: Rater) -> set[tuple[str, str]]:
    return set(
        session.exec(
            select(RatingEvent.case_id, RatingEvent.slot)
            .where(RatingEvent.rater_id == rater.id)
            .distinct()
        )
    )


def first_incomplete_position(
    session: Session, rater: Rater, assignments: list[Assignment]
) -> int | None:
    rated = _rated_pairs(session, rater)
    for a in assignments:
        if any((a.case_id, s) not in rated for s in SLOTS):
            return a.position
    return None


def count_complete(session: Session, rater: Rater, assignments: list[Assignment]) -> int:
    rated = _rated_pairs(session, rater)
    return sum(all((a.case_id, s) in rated for s in SLOTS) for a in assignments)


def page_volumes(session: Session, case_id: str) -> dict[str, Volume]:
    return {
        v.slot: v for v in session.exec(select(Volume).where(Volume.case_id == case_id))
    }


def dump_viewer_state(state: dict | None) -> str | None:
    return None if state is None else json.dumps(state, separators=(",", ":"), sort_keys=True)
