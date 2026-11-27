# Preservation index — Stage A Tracker work (sallah0007/salix-trading-system only)

PRESERVATION IS NOT ACCEPTANCE. A merge or this index clears no gate, hold or stage (CLAUDE.md §2A). Drive is the canonical record.
Snapshot taken 2026-11-27 after PR #30. Verify against git, not this text: `git ls-remote --heads origin`.

## 1. Merged into main (code/test/evidence; author-only, no independent review)
| PR | Branch (kept on remote) | Tip | Content |
|---|---|---|---|
| #24–#26 | `stage-a/tracker/annex-conformance`, `.../boundaries` | a3cf798, 33672f6 | Annex V1.2 schema layer, boundaries, simulated Gateway/FW/ML, contract objects, A07 package |
| #27 | `stage-a/tracker/consolidated-r03` | 069bdf7 | V0.38 conformance, News Hub/Decision Context validators, 100-qualifier reconciliation |
| #28 | `stage-a/tracker/review-r04` | de427f3 | R04: encoder hardening, Health B0, Q9 slice, §28 coverage, 106 boundary mutants |
| #29 | `stage-a/tracker/consolidated-r05` | 329c2f8 | R05 tests (D14/D15/store controls) and return |
| #30 | `stage-a/tracker/consolidated-r06` | e3dec9d | R06: FinalResolutionStore request-id reservation fix, forced-interleaving controls, §27 coverage map |
| this | `stage-a/tracker/preservation-r07` | see git | this index + reproducible R05/R06 mutation sweep |

## 2. Published on remote, NOT merged into main (candidate/historical; not merged by this checkpoint)
- `stage-a/tracker/full-component` (695199c) and `tracker-component-construction-layer` (2de875e): earlier component drafts by this Coder. Every file path they contain exists on main (checked with `git diff --name-status`); content was NOT diffed line by line, so "superseded" is not claimed.
- Pre-existing branches from earlier sessions, not touched here: `type1/*` (8), `docs/*` (2), `e01-conformance-harness`, `e01/conformance-harness`, `pr6-universal-transition-history`.

## 3. Unresolved (no code can close these; see coder_returns)
D1–D18 and A07-1..4 open items, 100 qualifier dispositions, Composer §27 field gap (27 of 35 absent from BuildPackage), provider/restart qualification, REQUEST_AFTER_CUTOFF trigger, R7 effectiveness. Detail: `coder_returns/TRK-STAGE-A-TRACKER-R06.md` (latest), `-R05.md`, `-R04.md`; `docs/a07/`.

## 4. Where things are
| Need | Path |
|---|---|
| Latest return, decision trace, issue closure | `coder_returns/TRK-STAGE-A-TRACKER-R06.md` |
| Decisions D1–D16 table, 100-qualifier CSV | `docs/a07/A07_CONSOLIDATED_DECISIONS_AND_SOURCE_RECONCILIATION_R03.md`, `docs/a07/V232_26S_QUALIFIER_RECONCILIATION_R02.csv` |
| Requirement/§28 and §27 coverage | `tests/trk_stage_a/test_boundaries.py` (§28), `tests/trk_stage_a/test_composer_s27_coverage.py` (§27) |
| FinalResolutionStore | `stage_a/gateway/v038.py`; tests `tests/trk_stage_a/test_v038_conformance.py`, `test_r05_consolidated.py` |

## 5. Reproduce (Python 3.13, no network)
```
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests -q
python3 -B -m unittest discover -s tests          # does not collect pytest-style tests
python3 -B tests/trk_stage_a/mutation_sweep.py
python3 -B tests/trk_stage_a/mutation_sweep_boundaries.py
python3 -B tests/trk_stage_a/mutation_sweep_r05_r06.py   # R05/R06 manual mutants, now scripted
```
Each sweep restores the mutated file in a `finally` block; run on a clean tree.

## 6. Intentional exclusions (never committed)
Private governing-source exports and Drive text copies (Governance, Connected Contract, Composer, Matrix, Build Plan, MLCore etc.; session scratch under `/home/claude/*`), Governance/Drive-reconstruction scripts (`v09x`–`v103` build/reconstruct scripts: Manager-document work, not repo code), `tracker_component_DRAFT_R01.zip` (earlier draft archive; its files are superseded by branches above, not diffed), `.pytest_cache/`, `__pycache__/`. No credentials were found or staged. Cite sources by ID and range only.
