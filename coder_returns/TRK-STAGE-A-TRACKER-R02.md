# TRK-STAGE-A-TRACKER-R02 — full-component coverage/gap matrix and D1–D10

Author: Claude (Trading Bot 7), CLAUDE.md §2A. CODER FINDING != SALIX DECISION. No gate, hold, acceptance or stage is cleared. Drive untouched.
**Correction to R01:** R01 called the component "built". It is AUTHORING-INCOMPLETE: the merged expression layer does not conform to Annex V1.2 (see A07 package §7) and several boundaries are unbuilt.
Evidence state: AUTHORING COMPLETE = NO · COMPONENT VERIFIED = NO (author-tested only; no independent oracle) · PROVIDER-DEPENDENCY QUALIFIED = NO · INTEGRATED/OPERATIONAL = NO.

## Evidence floor (rev 2, 27 Nov 2026)
DERIVATION_CLASS = INDEPENDENTLY_DERIVED (run this session). EXACT_INPUTS = branch `stage-a/tracker/boundaries` on main 9473939ae8c1d56e2cf57071a57ac7ff7fd629f0.
METHOD: `python3 -m pytest tests -q` → 538 passed · `python3 tests/trk_stage_a/mutation_sweep.py` → 22/22 killed · `python3 tests/trk_stage_a/mutation_sweep_boundaries.py` → 46/46 killed
(+ test_schema_annex: 8 hand-injected mutants killed earlier). REPRODUCIBLE_BY_MANAGER = YES.
Connection vocabulary used below: **REAL** = executes against the real counterpart · **SIM** = tested against an in-memory simulation written by me ·
**CONTRACT** = typed objects/validators only · **NONE**. No row is REAL except in-process use of baseline `tracker_identity`.

## Coverage matrix (Build Plan §27 TR-01..15; §§20–22 families) — current
| Req | Code | Test evidence | Connection | Gap / authority |
|---|---|---|---|---|
| TR-01 | materializer + expression evaluator (PROTO); `schema/*` (Annex objects) | Q15 source scan; batch==incremental | NONE (kernel) | Annex SQE_OPSET_V1_1 arithmetic BLOCKED on A02 SPEC (D3) |
| TR-02 | quant_intake_adapter, pipeline, authority_bridge | 44 pipeline tests; baseline-seam test | REAL (in-process baseline `tracker_identity`; seam hard-False) | resolver not installed (D1); certified ABSENT producer missing (D7) |
| TR-03 | canonical_encoding (PROTO); `schema/objects.sort_keyed` | Q1/Q2 + annex order/duplicate tests | CONTRACT | sort-key interpretation mine (D3) |
| TR-04 | manifest (PROTO); `schema/objects.manifest_hash`; **`schema/independent.py`** | producer==independent hash on row/transition/status/delivered; manifest hash order-insensitivity/field-sensitivity | CONTRACT | independent composition for MANIFEST not yet written (row/transition/status/delivered done); tables provisional (D3) |
| TR-05 | composer/* | dependency-direction tests; **composer imports no fw/ml/gateway** (test) | CONTRACT | §27/§7A/§28 mapping author judgement (D6) |
| TR-06 | pipeline classification | failed-requested-build ≠ NO_QUANT_FEATURE tests | SIM via `SimulatedGateway` dependency resolution | predicate mine (D8) |
| TR-07 | **`gateway/contracts.py` (SimulatedGateway), `fw/receiver.py`, `ml/receiver.py`** | G1–G9, OB1/OB2, F1–F6, M1–M4 (see below) | **SIM** — real Gateway/FW/ML not in repo | NOT connected; D12 |
| TR-08 | **`health/evidence.py`** | Q17: sink has only `emit/evidence`; evidence cannot change a binding; sub-schema validation | CONTRACT | no Health service in repo |
| TR-09 | stateful_verifier (PROTO), opcodes, capability | independence + neutered-check + defect-injection tests | NONE | Annex-level Q3–Q8 need opcode spec (D3) and oracle (D4) |
| TR-10 | currentness, replay, **chain_status** | half-open fence; AS_KNOWN/EVENTUAL; status machine Q22 | SIM | — |
| TR-11 | coordination/* (+ prioritized scheduler) | fencing/orphan/unknown-commit/concurrency/restart/Q16 | SIM (in-memory object store) | provider unqualified (D5); atomicity (D10) |
| TR-12 | **`context/edge.py`** declared-edge guard | undeclared edge refused; no composer/materializer import | CONTRACT | field layouts BLOCKED — owned by News Hub Event/Context V2, Decision Context V4, Connected Contract V0.38 H2 (not admitted) |
| TR-13 | **`fw/lanes.py`, `fw/receiver.py`** | F1 baseline, F2 model-specific, F3 confluence, M3 closure | SIM/CONTRACT | lane predicate mine (D11) |
| TR-14 | **`ml/receiver.py`** | F4–F6, M1, M2, M4, EVENTUAL look-ahead, fills, silent drop, mixed-era | SIM/CONTRACT | — |
| TR-15 | instrument-qualified keys | key difference; XAUUSD HALT does not affect EURUSD; unknown instrument leaks nothing | SIM | — |
Families: Q1/Q2/Q3 PROTO+annex-part · Q4–Q8 NOT RUN at Annex level · Q9/Q10 NOT BUILT (fit production) · Q11/Q12 pipeline tests · Q13 confluence = lane classification only (no confluence evidence merge built) ·
Q14 `HIDDEN_QUANT_ANCESTOR` test · Q15 done · Q16 round-robin + **P0/P1/P2 priority** tests · Q17 done · Q18–Q20 import-direction tests only (structural, not runtime) ·
Q21 speculation admission tests · Q22 status machine tests · Q23 vintage-mode tests in Gateway/ML (AS_KNOWN/EVENTUAL separation in currentness) ·
G1–G9 SIM · OB1/OB2 SIM · F1–F6 SIM · M1–M4 SIM (M4 positive control = OB2).
Candidate (proposed, not adopted): `stage_a/tracker/epoch_reresolution.py` (D25), `stage_a/schema/candidate_code_tables.py` (D3).

## Still not built
Independent manifest hash composition; fit production (Q9/Q10); confluence evidence handling; any REAL connection to Gateway/FW/ML/Health/Context; real provider adapter;
Event/Context fields. Reasons are in docs/a07/A07_PROPOSED_RESOLUTIONS_AND_RECORD_EDITS_R01.md §4.

## D1–D10 with exact authority needed (proposals and exact record edits: docs/a07/A07_PROPOSED_RESOLUTIONS_AND_RECORD_EDITS_R01.md; D11/D12 added there)
| D | Decision | Exact authority needed | Default until decided |
|---|---|---|---|
| D1 | Install `ClaimService.authorizes` resolver into baseline `_governed_construction_authority` | Manager-recorded acceptance of the admitted integration design (current assessment says claim-only/callback paths are rejected); Owner only if governance reserves it | stays hard-False |
| D2 | Order-signer role record / TrustAnchor | Manager record naming the signer role | tests assume MANAGER only |
| D3 | Admit manifest schema, ENUM/REF_TYPE code tables, opcode set, binary64 spec, sort-key rule | A02 SPEC source admission (Manager; A02 stays separate) | PROVISIONAL tables, refuse canonical |
| D4 | Independent expected-bytes oracle (COV-R02 successor) | Manager/Codex review of expected vectors (Owner: no third party; limitation stated) | author-only vectors |
| D5 | R5 provider qualification for object_store_journal | Manager provider acceptance | unqualified |
| D6 | Composer §27/§7A and §28 field mapping | Composer-source-owner disposition | my mapping, flagged |
| D7 | Certified-ABSENT producer | Governed amendment defining Era-0 resolution/absence certification | refuse ERA_1 absence |
| D8 | TR-06 predicate | Source-owner statement of the routing predicate | explicit flag |
| D9 | stage_a depends on tracker_component | Manager note accepting dependency (plan said tracker_identity only) | present, documented |
| D10 | Cross-journal atomicity | Manager note accepting ordering+witness, or a provider transaction design | ordering+witness |

## Seven lenses
MATHEMATICAL=YES · DATA_SCIENCE=NA (no fitting/data) · SOFTWARE_ARCHITECTURE=YES · ADVERSARIAL=YES · TRADING_MICROSTRUCTURE=NA (no market data/execution) · GOVERNANCE=YES · FALSIFICATION=YES.

## Independent review
Not obtained. Request packet for the Manager (via Owner relay): this file, docs/a07/A07_RECONCILIATION_AND_CLOSURE_EVIDENCE_R01.md, branch diff.
No review is claimed complete.
