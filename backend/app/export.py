"""CSV export of every rating event. Only slots appear, never where a volume came from."""

import csv
import io

from sqlmodel import Session, select

from .models import Assignment, Case, Rater, RatingEvent

COLUMNS = [
    "event_id", "created_at", "rater_id", "rater_name", "case", "dataset", "sequence",
    "page_position", "screen_position", "slot", "score", "comment", "viewer_state",
]


def export_csv(session: Session) -> str:
    cases = {c.id: c for c in session.exec(select(Case))}
    raters = {r.id: r for r in session.exec(select(Rater))}
    assignments = {(a.rater_id, a.case_id): a for a in session.exec(select(Assignment))}
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)
    for e in session.exec(select(RatingEvent).order_by(RatingEvent.id)):
        a = assignments.get((e.rater_id, e.case_id))
        case = cases[e.case_id]
        writer.writerow([
            e.id,
            e.created_at.isoformat(),
            e.rater_id,
            raters[e.rater_id].name or "",
            e.case_id,
            case.dataset,
            case.modality,
            a.position if a else "",
            a.column_order.index(e.slot) + 1 if a else "",
            e.slot,
            e.score,
            e.comment or "",
            e.viewer_state_json or "",
        ])
    return out.getvalue()
