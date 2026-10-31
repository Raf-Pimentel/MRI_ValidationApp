import csv
import json
import re
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

import prepare_data as prep

ROOT = Path(__file__).resolve().parents[2]
TESTKIT = ROOT / "radiologist_grading_testkit" / "radiologist_grading_testkit" / "testkit"
ANSWER_KEY = next(TESTKIT.glob("_answer_key*/answer_key.csv"), None)
needs_testkit = pytest.mark.skipif(not TESTKIT.is_dir(), reason="testkit not present")

# Words that would reveal where a volume comes from. Model names from the real answer
# key are added at test time; this list covers the generic hints.
FORBIDDEN = ["real", "ground", "truth", "original", "recon", "autoencoder", "answer",
             "resblock", "mednext", "segresnet", "swin", "matched", "maisi", "control"]


def make_case(root: Path, name="case_01", shape=(12, 14, 10), seed=0) -> Path:
    """A synthetic case: 5 float volumes with different value ranges and noise."""
    rng = np.random.default_rng(seed)
    case_dir = root / name
    case_dir.mkdir(parents=True)
    affine = np.diag([1.0, 1.0, 1.0, 1.0])
    for i, slot in enumerate(prep.SLOTS):
        data = rng.normal(100 * i, 10 + 5 * i, shape).astype(np.float32)
        nib.save(nib.Nifti1Image(data, affine), case_dir / f"{name}_vol_{slot}.nii.gz")
    (case_dir / "info.txt").write_text(
        "Dataset: BraTS-GLI\nModality: T1ce\n5 volumes: one real MRI + 4 autoencoder reconstructions\n"
    )
    return case_dir


def rewrite_volume(case_dir: Path, slot: str, data=None, affine=None):
    path = case_dir / f"{case_dir.name}_vol_{slot}.nii.gz"
    img = nib.load(path)
    data = np.asarray(img.dataobj) if data is None else data
    nib.save(nib.Nifti1Image(data, img.affine if affine is None else affine), path)


# ---- T1.1: reading and compatibility ----

def test_read_case_ok(tmp_path):
    case = prep.read_case(make_case(tmp_path))
    assert (case.dataset, case.sequence) == ("BraTS-GLI", "T1ce")
    assert set(case.volumes) == set(prep.SLOTS)


def test_shape_mismatch_fails_clearly(tmp_path):
    d = make_case(tmp_path)
    rewrite_volume(d, "C", data=np.zeros((12, 14, 11), np.float32))
    with pytest.raises(prep.CaseError, match=r"case_01: shape of slot C"):
        prep.read_case(d)


def test_orientation_mismatch_fails_clearly(tmp_path):
    d = make_case(tmp_path)
    rewrite_volume(d, "D", affine=np.diag([-1.0, 1.0, 1.0, 1.0]))
    with pytest.raises(prep.CaseError, match=r"case_01: orientation of slot D is L"):
        prep.read_case(d)


def test_spacing_mismatch_fails_clearly(tmp_path):
    d = make_case(tmp_path)
    rewrite_volume(d, "B", affine=np.diag([2.0, 2.0, 2.0, 1.0]))
    with pytest.raises(prep.CaseError, match=r"case_01: voxel spacing of slot B"):
        prep.read_case(d)


def test_missing_volume_and_bad_info_fail_clearly(tmp_path):
    d = make_case(tmp_path)
    (d / "case_01_vol_E.nii.gz").unlink()
    with pytest.raises(prep.CaseError, match=r"missing volume for slot E"):
        prep.read_case(d)
    d2 = make_case(tmp_path, "case_02")
    (d2 / "info.txt").write_text("Dataset: BraTS-GLI\n")
    with pytest.raises(prep.CaseError, match=r"no 'Modality:' line"):
        prep.read_case(d2)


@needs_testkit
def test_all_testkit_cases_are_compatible():
    cases = sorted(TESTKIT.glob("case_*"))
    assert len(cases) == 8
    for d in cases:
        prep.read_case(d)


# ---- T1.2: repacking ----

def test_repack_same_size_clean_header_and_values(tmp_path):
    case = prep.read_case(make_case(tmp_path))
    files, _ = prep.repack_case(case)
    assert len({len(b) for b in files.values()}) == 1
    # The 5 headers are byte-identical, so nothing in them tells the volumes apart.
    assert len({b[:prep.NIFTI1_VOX_OFFSET] for b in files.values()}) == 1
    out = tmp_path / "v.nii"
    for slot, blob in files.items():
        out.write_bytes(blob)
        img = nib.load(out)
        assert img.get_data_dtype() == np.int16
        assert img.shape == (12, 14, 10)
        for field in ("descrip", "db_name", "aux_file", "intent_name"):
            assert bytes(img.header[field]).strip(b"\x00") == b""
        original = case.volumes[slot].get_fdata(dtype=np.float32)
        step = float(img.dataobj.slope)
        assert np.abs(img.get_fdata(dtype=np.float32) - original).max() <= step


def test_nan_is_rejected(tmp_path):
    d = make_case(tmp_path)
    data = np.asarray(nib.load(d / "case_01_vol_A.nii.gz").dataobj).copy()
    data[0, 0, 0] = np.nan
    rewrite_volume(d, "A", data=data)
    with pytest.raises(prep.CaseError, match="NaN"):
        prep.repack_case(prep.read_case(d))


@pytest.fixture(scope="module")
def testkit_output(tmp_path_factory):
    out = tmp_path_factory.mktemp("prepared") / "out"
    prep.prepare_batch(TESTKIT, out)
    return out


@needs_testkit
def test_testkit_volumes_have_equal_size_within_case(testkit_output):
    manifest = json.loads((testkit_output / "manifest.json").read_text())
    assert len(manifest["cases"]) == 8
    for c in manifest["cases"]:
        sizes = {(testkit_output / "volumes" / f"{v['opaque_id']}.nii").stat().st_size for v in c["volumes"]}
        assert len(sizes) == 1, c["case"]


# ---- T1.3 / T1.4: opaque ids, manifest and leak scan ----

def test_manifest_content_and_opaque_names(tmp_path):
    make_case(tmp_path / "in")
    manifest = prep.prepare_batch(tmp_path / "in", tmp_path / "out")
    (case,) = manifest["cases"]
    assert set(case) == {"case", "dataset", "sequence", "volumes"}
    assert [v["slot"] for v in case["volumes"]] == list(prep.SLOTS)
    assert len({v["opaque_id"] for v in case["volumes"]}) == 5
    for v in case["volumes"]:
        assert set(v) == {"slot", "opaque_id", "shape", "spacing"}
        assert v["shape"] == [12, 14, 10]
        assert (tmp_path / "out" / "volumes" / f"{v['opaque_id']}.nii").is_file()
    uuid_name = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.nii$")
    assert all(uuid_name.match(p.name) for p in (tmp_path / "out" / "volumes").iterdir())


def _forbidden_words():
    words = set(FORBIDDEN)
    if ANSWER_KEY:
        with open(ANSWER_KEY, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                words.update(w for w in re.split(r"[^a-z0-9]+", row["source"].lower()) if len(w) > 2)
    return words


def _scan_output(out: Path):
    """Names, paths, manifest text and NIfTI headers (the image data is not text)."""
    texts = []
    for p in out.rglob("*"):
        texts.append(str(p.relative_to(out)).lower())
        if p.name == "manifest.json":
            texts.append(p.read_text(encoding="utf-8").lower())
        elif p.suffix == ".nii":
            texts.append(p.read_bytes()[:prep.NIFTI1_VOX_OFFSET].decode("latin-1").lower())
    return texts


def test_no_leak_in_synthetic_output(tmp_path):
    make_case(tmp_path / "in")
    prep.prepare_batch(tmp_path / "in", tmp_path / "out")
    blob = "\n".join(_scan_output(tmp_path / "out"))
    assert [w for w in _forbidden_words() if w in blob] == []


@needs_testkit
def test_no_leak_in_testkit_output(testkit_output):
    blob = "\n".join(_scan_output(testkit_output))
    assert [w for w in _forbidden_words() if w in blob] == []


@needs_testkit
def test_answer_key_is_never_opened(tmp_path, monkeypatch):
    opened = []
    orig_open, orig_bytes, orig_text = Path.open, Path.read_bytes, Path.read_text

    def spy(orig):
        def wrapper(self, *a, **k):
            opened.append(str(self))
            return orig(self, *a, **k)
        return wrapper

    monkeypatch.setattr(Path, "open", spy(orig_open))
    monkeypatch.setattr(Path, "read_bytes", spy(orig_bytes))
    monkeypatch.setattr(Path, "read_text", spy(orig_text))
    prep.prepare_batch(TESTKIT, tmp_path / "out")
    assert opened and not [p for p in opened if "answer_key" in p.lower() and "pytest" not in p.lower()]


def test_cli_refuses_existing_output_and_reports_errors(tmp_path, capsys):
    make_case(tmp_path / "in")
    out = tmp_path / "out"
    assert prep.main([str(tmp_path / "in"), str(out)]) == 0
    assert prep.main([str(tmp_path / "in"), str(out)]) == 1
    assert prep.main([str(tmp_path / "in"), str(out), "--force"]) == 0
    rewrite_volume(tmp_path / "in" / "case_01", "C", data=np.zeros((3, 3, 3), np.float32))
    assert prep.main([str(tmp_path / "in"), str(out), "--force"]) == 1
    assert "shape of slot C" in capsys.readouterr().err
    assert not out.exists()
