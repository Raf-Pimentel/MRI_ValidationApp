"""Tables. None of them stores where a volume came from; only its slot (A-E)."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel

SLOTS = ("A", "B", "C", "D", "E")
SCHEMA_VERSION = 1


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Case(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset: str
    modality: str


class Volume(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("case_id", "slot"),)

    id: int | None = Field(default=None, primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    slot: str
    opaque_id: str = Field(unique=True, index=True)
    path: str  # relative to the prepared data folder
    shape: list[int] = Field(sa_column=Column(JSON))
    spacing: list[float] = Field(sa_column=Column(JSON))


class Rater(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    name: str | None = None
    email: str | None = None
    seed: int
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None


class Assignment(SQLModel, table=True):
    """Page order (position, 1-based) and slot order on screen for one rater."""

    rater_id: int = Field(foreign_key="rater.id", primary_key=True)
    position: int = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id")
    column_order: list[str] = Field(sa_column=Column(JSON))


class RatingEvent(SQLModel, table=True):
    """Append-only. The current rating is the latest row for (rater, case, slot)."""

    __table_args__ = (CheckConstraint("score BETWEEN 1 AND 5", name="score_range"),)

    id: int | None = Field(default=None, primary_key=True)
    client_event_id: str = Field(unique=True, index=True)
    rater_id: int = Field(foreign_key="rater.id", index=True)
    case_id: str = Field(foreign_key="case.id")
    slot: str
    score: int
    comment: str | None = None
    viewer_state_json: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
