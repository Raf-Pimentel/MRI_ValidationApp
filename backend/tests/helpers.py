import json
import uuid
from pathlib import Path

from app.models import SLOTS

CASES = [("case_01", "BraTS-GLI", "T1ce"), ("case_02", "IXI", "T2"), ("case_03", "BraTS-MET", "FLAIR"),
         ("case_04", "IXI", "T1"), ("case_05", "BraTS-GLI", "FLAIR"), ("case_06", "IXI", "T2")]


def write_prepared(folder: Path, cases=CASES, size=64) -> None:
    """Small stand-in for the output of scripts/prepare_data.py."""
    (folder / "volumes").mkdir(parents=True)
    entries = []
    for case, dataset, sequence in cases:
        volumes = []
        for slot in SLOTS:
            opaque_id = str(uuid.uuid4())
            (folder / "volumes" / f"{opaque_id}.nii").write_bytes(bytes([ord(slot)]) * size)
            volumes.append(
                {"slot": slot, "opaque_id": opaque_id, "shape": [4, 4, 4], "spacing": [1.0, 1.0, 1.0]}
            )
        entries.append({"case": case, "dataset": dataset, "sequence": sequence, "volumes": volumes})
    (folder / "manifest.json").write_text(json.dumps({"cases": entries}), encoding="utf-8")
