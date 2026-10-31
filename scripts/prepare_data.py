"""Prepare a batch in the testkit layout into blinded, uniform files for serving.

Input: a folder with `case_XX/` directories, each holding `case_XX_vol_A..E.nii.gz`
and `info.txt`. The answer key is never read: only `case_*` folders are visited.

Output (see `prepare_batch`):
  <out>/volumes/<opaque_id>.nii   int16, uncompressed, clean header, same bytes per case
  <out>/manifest.json             case, dataset, sequence, and per volume slot/opaque_id/shape/spacing

Usage: python scripts/prepare_data.py <input_dir> <output_dir> [--force]
"""
import argparse
import json
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np

SLOTS = ("A", "B", "C", "D", "E")
INT16_MAX = 32767
NIFTI1_VOX_OFFSET = 352


class CaseError(Exception):
    """A case cannot be prepared; the message says which case and why."""


@dataclass
class Case:
    name: str
    dataset: str
    sequence: str
    volumes: dict  # slot -> nibabel image


def _read_info(path: Path, case: str) -> tuple[str, str]:
    """Read only the Dataset and Modality lines; the rest of info.txt is ignored."""
    if not path.is_file():
        raise CaseError(f"{case}: missing info.txt")
    fields = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(Dataset|Modality):\s*(.+?)\s*$", line)
        if m:
            fields[m.group(1)] = m.group(2)
    for key in ("Dataset", "Modality"):
        if key not in fields:
            raise CaseError(f"{case}: info.txt has no '{key}:' line")
    return fields["Dataset"], fields["Modality"]


def check_compatible(case: str, volumes: dict) -> None:
    """The 5 volumes must share shape, voxel size and orientation."""
    ref_slot = SLOTS[0]
    ref = volumes[ref_slot]
    ref_codes = nib.aff2axcodes(ref.affine)
    for slot in SLOTS[1:]:
        img = volumes[slot]
        if img.shape != ref.shape:
            raise CaseError(f"{case}: shape of slot {slot} is {img.shape}, slot {ref_slot} is {ref.shape}")
        if not np.allclose(img.header.get_zooms()[:3], ref.header.get_zooms()[:3], atol=1e-4):
            raise CaseError(f"{case}: voxel spacing of slot {slot} differs from slot {ref_slot}")
        codes = nib.aff2axcodes(img.affine)
        if codes != ref_codes:
            raise CaseError(
                f"{case}: orientation of slot {slot} is {''.join(codes)}, slot {ref_slot} is {''.join(ref_codes)}"
            )
        if not np.allclose(img.affine, ref.affine, atol=1e-3):
            raise CaseError(f"{case}: affine of slot {slot} differs from slot {ref_slot}")
    if len(ref.shape) != 3:
        raise CaseError(f"{case}: expected 3D volumes, got shape {ref.shape}")


def read_case(case_dir: Path) -> Case:
    """Read one case (volumes + info.txt) and check that its volumes match."""
    name = case_dir.name
    dataset, sequence = _read_info(case_dir / "info.txt", name)
    volumes = {}
    for slot in SLOTS:
        path = case_dir / f"{name}_vol_{slot}.nii.gz"
        if not path.is_file():
            raise CaseError(f"{name}: missing volume for slot {slot} ({path.name})")
        volumes[slot] = nib.load(path)
    check_compatible(name, volumes)
    return Case(name, dataset, sequence, volumes)


def _clean_header_bytes(shape, spacing, affine, slope: float, intercept: float) -> bytes:
    """A NIfTI-1 header built from scratch: no description, names or source fields."""
    hdr = nib.Nifti1Header()
    hdr.set_data_dtype(np.int16)
    hdr.set_data_shape(shape)
    hdr.set_zooms(spacing)
    hdr.set_xyzt_units("mm")
    hdr.set_qform(affine, code=1)
    hdr.set_sform(affine, code=1)
    hdr.set_slope_inter(slope, intercept)
    hdr["vox_offset"] = NIFTI1_VOX_OFFSET
    return hdr.binaryblock + b"\x00" * 4  # 348-byte header + empty extension flag


def repack_case(case: Case) -> tuple[dict, dict]:
    """Return ({slot: file bytes}, {slot: {"shape", "spacing"}}) for one case.

    The 5 volumes share one scale (slope/intercept from the case-wide range), so the
    header does not tell the volumes apart and the sizes are identical.
    """
    arrays = {}
    for slot, img in case.volumes.items():
        arr = np.asarray(img.get_fdata(dtype=np.float32))
        if not np.isfinite(arr).all():
            raise CaseError(f"{case.name}: slot {slot} has NaN or infinite values")
        arrays[slot] = arr
    lo = min(float(a.min()) for a in arrays.values())
    hi = max(float(a.max()) for a in arrays.values())
    slope = (hi - lo) / INT16_MAX if hi > lo else 1.0
    ref = case.volumes[SLOTS[0]]
    shape = ref.shape
    spacing = tuple(float(z) for z in ref.header.get_zooms()[:3])
    header = _clean_header_bytes(shape, spacing, ref.affine, slope, lo)
    files, info = {}, {}
    for slot, arr in arrays.items():
        q = np.rint((arr - lo) / slope).astype(np.int16)
        files[slot] = header + q.tobytes(order="F")
        info[slot] = {"shape": list(shape), "spacing": list(spacing)}
    return files, info


def prepare_batch(input_dir: Path, output_dir: Path) -> dict:
    """Prepare every `case_*` folder in input_dir and write volumes + manifest."""
    case_dirs = sorted(p for p in input_dir.glob("case_*") if p.is_dir())
    if not case_dirs:
        raise CaseError(f"no case_* folders in {input_dir}")
    volumes_dir = output_dir / "volumes"
    volumes_dir.mkdir(parents=True)
    manifest = {"cases": []}
    for case_dir in case_dirs:
        case = read_case(case_dir)
        files, info = repack_case(case)
        entry = {"case": case.name, "dataset": case.dataset, "sequence": case.sequence, "volumes": []}
        for slot in SLOTS:
            opaque_id = str(uuid.uuid4())
            (volumes_dir / f"{opaque_id}.nii").write_bytes(files[slot])
            entry["volumes"].append({"slot": slot, "opaque_id": opaque_id, **info[slot]})
        manifest["cases"].append(entry)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--force", action="store_true", help="replace the output folder if it exists")
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        if not args.force:
            print(f"error: {args.output_dir} already exists (use --force to replace it)", file=sys.stderr)
            return 1
        shutil.rmtree(args.output_dir)
    try:
        manifest = prepare_batch(args.input_dir, args.output_dir)
    except CaseError as e:
        shutil.rmtree(args.output_dir, ignore_errors=True)
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"prepared {len(manifest['cases'])} cases into {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
