# Radiologist grading test kit

Test fixture for the "rank most -> least realistic" grading site (see
`docs/ic-tasks.md`). **Not the real radiologist dataset** -- just enough real
material to build and test the site's display/ranking flow against actual
brain MRI volumes before recruiting radiologists.

## Contents

8 cases (`case_01` .. `case_08`), each a real BraTS/IXI validation subject.
Every case has 5 volumes, `<case>_vol_A.nii.gz` .. `<case>_vol_E.nii.gz`:

- 1 real (ground-truth) volume
- 4 autoencoder reconstructions of that same volume, one per trained arm:
  `resblock` (MAISI control), `matched_mednext`, `matched_segresnet`,
  `matched_swin`

The 5-to-slot mapping is **randomized independently per case** (seed 20260821)
so slot letter never correlates with source -- vol_A isn't "always the real
one" or "always the same architecture". `case_XX/info.txt` gives the dataset
and modality (safe to show; the same for all 5 volumes in a case) but not
which volume is which.

All 8 cases are the same underlying subjects across all 4 architectures
(same `--seed 42 --num-samples 8` on `reconstruct.py`, verified by matching
per-dataset counts across arms before assembly) -- so a real vs. reconstructed
comparison is meaningful within a case.

**`_answer_key_do_not_share_with_radiologists/answer_key.csv`** maps every
`(case, slot)` to its true source. Use it to verify the site displays and
records things correctly; strip it out before anyone outside the project sees
the kit, and obviously never expose it in the site's UI.

## Known checkpoint gotcha

`matched_segresnet`'s reconstructions here come from `checkpoints/epoch_0080.pt`
(state-dict export), not `best_model.pt` -- `best_model.pt` there is a known-bad
checkpoint (~epoch 192) that rots background reconstruction. See
`docs/benchmark-design.md` if you need to regenerate this kit and re-derive
checkpoint choices.

## Regenerating / making a bigger batch

```bash
for name_cfg_ckpt in \
  "resblock configs/benchmark/track1_resblock.yaml ../outputs/validation/control200_resblock/best_model.pt" \
  "matched_mednext configs/benchmark/track1_matched_mednext.yaml ../outputs/bench/t1_matched_mednext/best_model.pt" \
  "matched_segresnet configs/benchmark/track1_matched_segresnet.yaml ../outputs/bench/t1_matched_segresnet/checkpoints/epoch_0080_state_dict.pt" \
  "matched_swin configs/benchmark/track1_matched_swin.yaml ../outputs/bench/t1_matched_swin/best_model.pt" ; do
  set -- $name_cfg_ckpt
  /opt/venv/bin/python auto_encoders/reconstruct.py --config "$2" --weights "$3" \
    --split val --num-samples <N> --seed 42 --no-lpips --no-figures \
    --save-nifti --nifti-max -1 --output-dir /tmp/testkit_raw/"$1"
done
```

Keep `--seed`, `--split` and `--num-samples` **identical** across all four
runs -- that's what guarantees the same subjects land in each arm's output
(verified here by checking the per-dataset sample counts match across arms
before trusting the alignment; `--num-samples -1` does NOT give the same
subjects as a finite `--num-samples`, they use different selection code paths
in `reconstruct.py::_build_loader`). Then re-run the assembly/shuffle step
(ask Claude, or see this session's `assemble_testkit.py` pattern) to
anonymize into cases.
