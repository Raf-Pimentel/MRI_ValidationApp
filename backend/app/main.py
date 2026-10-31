from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from . import service
from .config import Settings
from .db import init_db, make_engine
from .models import SLOTS, Assignment, Case, Rater, RatingEvent, Volume

MAX_VIEWER_STATE_BYTES = 4096


class RatingIn(BaseModel):
    client_event_id: str = Field(min_length=8, max_length=64)
    position: int = Field(ge=1)
    slot: str
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    viewer_state: dict[str, Any] | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine = make_engine(settings.db_path)
    init_db(engine)
    # No docs/openapi routes and no GZip middleware: volumes go out byte for byte.
    app = FastAPI(title="MRI ValidationApp", docs_url=None, redoc_url=None, openapi_url=None)

    def db():
        with Session(engine) as session:
            yield session

    Db = Annotated[Session, Depends(db)]

    def rater_from_token(token: str, session: Db) -> Rater:
        rater = service.get_rater(session, token)
        if rater is None:
            raise HTTPException(404, "Link inválido. Peça um novo link ao pesquisador.")
        return rater

    CurrentRater = Annotated[Rater, Depends(rater_from_token)]

    def assignments_for(session: Session, rater: Rater) -> list[Assignment]:
        return service.ensure_assignments(session, rater, settings.pages_per_rater)

    def find_page(assignments: list[Assignment], position: int) -> Assignment:
        for a in assignments:
            if a.position == position:
                return a
        raise HTTPException(404, "Página inexistente.")

    @app.get("/api/session/{token}")
    def get_session(rater: CurrentRater, session: Db):
        assignments = assignments_for(session, rater)
        next_position = service.first_incomplete_position(session, rater, assignments)
        return {
            "name": rater.name,
            "total_pages": len(assignments),
            "completed_pages": service.count_complete(session, rater, assignments),
            "next_position": next_position,
            "finished": next_position is None,
        }

    @app.get("/api/session/{token}/page/{position}")
    def get_page(position: int, rater: CurrentRater, session: Db):
        assignments = assignments_for(session, rater)
        assignment = find_page(assignments, position)
        case = session.get(Case, assignment.case_id)
        volumes = service.page_volumes(session, assignment.case_id)
        ratings = service.current_ratings(session, rater.id, assignment.case_id)
        return {
            "position": position,
            "total_pages": len(assignments),
            "sequence": case.modality,
            "columns": [
                {"slot": slot, "url": f"/api/vol/{volumes[slot].opaque_id}"}
                for slot in assignment.column_order
            ],
            "ratings": {
                slot: {"score": e.score, "comment": e.comment} for slot, e in ratings.items()
            },
        }

    @app.get("/api/vol/{opaque_id}")
    def get_volume(opaque_id: str, session: Db):
        volume = session.exec(select(Volume).where(Volume.opaque_id == opaque_id)).first()
        if volume is None:
            raise HTTPException(404, "Volume inexistente.")
        return FileResponse(
            settings.prepared_dir / volume.path,
            media_type="application/octet-stream",
            headers={"Cache-Control": "private, max-age=86400"},
        )

    @app.post("/api/session/{token}/rating")
    def post_rating(body: RatingIn, rater: CurrentRater, session: Db):
        state = service.dump_viewer_state(body.viewer_state)
        if state is not None and len(state.encode()) > MAX_VIEWER_STATE_BYTES:
            raise HTTPException(422, "viewer_state grande demais.")
        if body.slot not in SLOTS:
            raise HTTPException(422, "Coluna inválida.")
        assignment = find_page(assignments_for(session, rater), body.position)

        def existing() -> RatingEvent | None:
            return session.exec(
                select(RatingEvent).where(
                    RatingEvent.client_event_id == body.client_event_id
                )
            ).first()

        def reply(event: RatingEvent):
            if event.rater_id != rater.id:
                raise HTTPException(409, "Identificador de envio já usado.")
            return {"event_id": event.id, "created_at": event.created_at}

        if (event := existing()) is not None:
            return reply(event)
        event = RatingEvent(
            client_event_id=body.client_event_id,
            rater_id=rater.id,
            case_id=assignment.case_id,
            slot=body.slot,
            score=body.score,
            comment=body.comment,
            viewer_state_json=state,
        )
        session.add(event)
        try:
            session.commit()
        except IntegrityError:  # the same client_event_id arrived twice at once
            session.rollback()
            return reply(existing())
        session.refresh(event)
        return reply(event)

    return app
