"""Loads the manifest written by scripts/prepare_data.py into the database."""

import json
from pathlib import Path

from sqlmodel import Session

from .models import SLOTS, Case, Volume


class ManifestError(ValueError):
    pass


def load_manifest(session: Session, prepared_dir: Path) -> dict[str, int]:
    """Insert new cases; leave unchanged ones alone. Returns counts of added/kept cases.

    Refuses a case that already exists with different volumes, since ratings may
    already point to it.
    """
    manifest = json.loads((prepared_dir / "manifest.json").read_text(encoding="utf-8"))
    added = kept = 0
    for entry in manifest["cases"]:
        case_id = entry["case"]
        rows = _volumes_for(entry, prepared_dir)
        existing = session.get(Case, case_id)
        if existing is not None:
            _check_same(session, case_id, rows)
            kept += 1
            continue
        session.add(Case(id=case_id, dataset=entry["dataset"], modality=entry["sequence"]))
        session.add_all(rows)
        added += 1
    session.commit()
    return {"added": added, "kept": kept}


def _volumes_for(entry: dict, prepared_dir: Path) -> list[Volume]:
    case_id = entry["case"]
    by_slot = {v["slot"]: v for v in entry["volumes"]}
    if sorted(by_slot) != list(SLOTS) or len(entry["volumes"]) != len(SLOTS):
        raise ManifestError(f"{case_id}: expected exactly slots {''.join(SLOTS)}")
    rows, sizes = [], set()
    for slot in SLOTS:
        v = by_slot[slot]
        rel = f"volumes/{v['opaque_id']}.nii"
        file = prepared_dir / rel
        if not file.is_file():
            raise ManifestError(f"{case_id}/{slot}: file {rel} not found")
        sizes.add(file.stat().st_size)
        rows.append(
            Volume(
                case_id=case_id,
                slot=slot,
                opaque_id=v["opaque_id"],
                path=rel,
                shape=list(v["shape"]),
                spacing=list(v["spacing"]),
            )
        )
    if len(sizes) != 1:
        raise ManifestError(f"{case_id}: volumes differ in size in bytes ({sorted(sizes)})")
    return rows


def _check_same(session: Session, case_id: str, rows: list[Volume]) -> None:
    from sqlmodel import select

    current = {
        v.slot: v.opaque_id
        for v in session.exec(select(Volume).where(Volume.case_id == case_id))
    }
    if current != {r.slot: r.opaque_id for r in rows}:
        raise ManifestError(
            f"{case_id} is already loaded with different volumes; "
            "start from a new database for a new batch"
        )
