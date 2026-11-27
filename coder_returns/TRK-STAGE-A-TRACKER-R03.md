# TRK-STAGE-A-TRACKER-R03 — consolidated pass: real-source conformance, 100-qualifier reconciliation, decision table

Author: Claude (Trading Bot 7), CLAUDE.md §2A. CODER FINDING != SALIX DECISION. No gate, hold, acceptance or stage is cleared; Drive read-only. Supersedes R02 where they differ. Decisions: docs/a07/A07_CONSOLIDATED_DECISIONS_AND_SOURCE_RECONCILIATION_R03.md.
Evidence state: AUTHORING COMPLETE = NO · COMPONENT VERIFIED = NO (author-tested; no independent oracle) · PROVIDER-DEPENDENCY QUALIFIED = NO · INTEGRATED/OPERATIONAL = NO.
All Tracker code remains **unreleased candidate work** (A08 READY_TO_CODE = NO, QC34 ALERT(HOLD)); PR #26 is retained as such.

## Evidence floor
DERIVATION_CLASS = INDEPENDENTLY_DERIVED (run this session). EXACT_INPUTS = branch `stage-a/tracker/consolidated-r03` on main 059b7cefeb815b800433a0a7e14ccf7e76f39a60.
METHOD / RESULTS: `python3 -m pytest tests -q` → 556 passed · `python3 -m unittest discover -s tests` → 453 OK · `tests/trk_stage_a/mutation_sweep.py` → 22/22 killed · `tests/trk_stage_a/mutation_sweep_boundaries.py` → 83/83 killed (now run with bytecode disabled: a stale `.pyc` once made a test fail spuriously after a mutation run). REPRODUCIBLE_BY_MANAGER = YES.
Connection vocabulary: REAL / SIM / CONTRACT / NONE. Only in-process baseline `tracker_identity` is REAL.

## Changes in this pass
* `stage_a/gateway/v038.py` (new) + `contracts.observed_at`: Connected Contract V0.38 delivery-failure model. Tests: `test_v038_conformance.py` (9). Mutants: 15.
* `stage_a/context/news_hub_v2.py`, `decision_context.py` (new): legality and envelope validators from the News Hub V2 and Decision Context V4 field lists. Tests: `test_context_contracts.py` (6). Mutants: 15.
* `stage_a/schema/independent.py`: independent MANIFEST_HASH; 2 tests; 7 mutants.
* `docs/a07/V232_26S_QUALIFIER_RECONCILIATION_R02.csv`: all 100 qualifiers (hash reproduced, current refs resolved, lexical screen).
* Corrected: D12 (answered by the V0.38 text). Withdrawn: "Event/Context fields are blocked because the sources are not admitted" — the sources exist in Drive and were read; what remains blocked is byte encoding and production (D13).

## Coverage matrix delta (rows not listed are unchanged from R02)
| Req | Now | Connection | Gap |
|---|---|---|---|
| TR-04 | independent composition now covers row, transition, status, delivered **and manifest** | CONTRACT | tables PROVISIONAL (D3) |
| TR-07 | `gateway/v038.py` field/rule conformance to V0.38; resolver still `SimulatedGateway` | SIM + CONTRACT | no real Gateway in repo; D13, D15, D16 |
| TR-10 | settlement delay, watermark, forensic classification | SIM | D16 |
| TR-12 | News Hub V2 legality + Decision Context V4 validators | CONTRACT | no ingestion/mirror producer; D13, D14 |

## Still not built
Fit production (Q9/Q10); confluence evidence merge; REAL connections to Gateway/FW/ML/Health/Context; real provider adapter; byte encodings for FINAL_RESOLUTION_HASH, PACKAGE_HASH and Context objects; REQUEST_AFTER_CUTOFF trigger; Drive-mirror comparison.

## Seven lenses
MATHEMATICAL=YES · DATA_SCIENCE=NA (no fitting/data) · SOFTWARE_ARCHITECTURE=YES · ADVERSARIAL=YES · TRADING_MICROSTRUCTURE=NA (no market data/execution; the half-open/settlement rules are tested as logic only) · GOVERNANCE=YES · FALSIFICATION=YES (105 mutants across the two sweeps killed (22 + 83); one surviving mutant found and killed this pass).

## Independent review
Not obtained; none claimed. Request packet for the Manager via the Owner relay: this file, the R03 decisions doc, the CSV, the branch diff.
