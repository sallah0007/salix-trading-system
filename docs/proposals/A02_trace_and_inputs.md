# A02/SPEC recovery trace and the four remaining-input groups (R11)

Status: Coder analysis; proposals only. Nothing here clears A02 Class B HOLD, the Build Plan "Confirm Class B analytical closure" gate, QC34, A07 or Stage A. A merge/CI pass is a code event.

## A. Arithmetic authority (recovered; code aligned in commit 31a2509)
Sources (directly read): Parent V1.2 (Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM) lines 116-204 SQE_OPSET_V1_1; Annex V1.2 (Drive 13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA) lines 84-121.
Implemented: `log` removed (profile-only, refused `OPCODE_NOT_ADMITTED_SQE_OPSET_V1_1`); domain failures refuse (`DOMAIN_DIV_ZERO`, `DOMAIN_SQRT_NEGATIVE`); canonical +0 for zeros; independent reference mirrors it. Tests: `test_r11_arithmetic.py`; mutation sweep r11 16/16 killed, 3 documented equivalents.
Not implemented (absent in source read, not invented): numeric opcode assignments, program byte grammar, K3 invocation; comparison/select/vector/matrix/FIXED_DOT operators; capability-emulation refusal beyond the existing `check_declared`.
Flagged defect class: source requires PROGRAM_CAPABILITY_CLASS and RESOURCE_CEILING_REF (seven ceilings, no silent defaults). `schema.py` hard-codes `MAX_NODES=512` and `MAX_WINDOW=10000` as silent infrastructure defaults. They are UNGOVERNED implementation defaults, not source values; they must be replaced by a governed ceiling reference once one exists.

## B. Four-way trace (kept separate)
| Item | Finding | Held? |
|---|---|---|
| Build Plan A02 "Confirm Class B analytical closure" gate | not addressed by code or doc; stays held | HELD |
| C22 A02 revision label | not resolved by any source read; label identity open | OPEN |
| D3/D4 | companion D02 labels "D4/D7" collide with repo numbering; not used as authority | OPEN |
| operator/arithmetic/program source and K3 instance | arithmetic recovered (A); program grammar and K3 instance not found | PARTLY OPEN |

## C. Remaining-input groups (per row: missing input / source searched / role / proposed resolution / blocked action)
Group 1 - A02/SPEC recovered authority:
- numeric opcode codes + program byte grammar | Parent V1.2, Annex V1.2, Build Plan, Composer | Manager (source owner) | cite governing section or issue governed delta | canonical program encoding; cross-implementation byte identity
- K3 instance and invocation | same | Manager | name instance | K3 conformance
- governed resource ceilings (seven) + PROGRAM_CAPABILITY_CLASS | Parent V1.2 SQE_OPSET | Manager | supply ceiling reference | replacing MAX_NODES/MAX_WINDOW
- C22 revision label | Matrix, Build Plan | Manager | record label | A02 revision claim
Group 2 - Composer section 27 / payload definitions:
- section 27 field definitions, FW/ML payload definitions, ML manifest writer declaration | Composer V9 export, mapping A04, companion D02 | Manager/Composer owner | supply or confirm field lists | FW return lineage, ML lineage rows (E-03 map)
Group 3 - D13 byte layouts and D14-D18:
- D13 PACKAGE_HASH / FINAL_PACKAGE_HASH bytes | Connected Contract V0.37/V0.38 as carried, Build Plan | Manager | supply layout | recomputing H1 hashes (now only inequality check)
- D14 cutoff vs fence; D15 reason->status list; D16 settlement delay; D17/D18 Health profile home/registry | Build Plan, Matrix, companion | Manager | record existing authoritative answers or decide | `check_settlement` value, status mapping, Health registry
Group 4 - provider/clock/host/grants:
- qualified provider, clock, host, grants | Build Plan E-01/E-06, R7 | Owner/Manager | qualify provider (D10) | real-world qualification, REAL connection status; NOT component authoring
I did not recover D14-D18 answers in this segment; reading for them is INSUFFICIENT_EVIDENCE, not an absence.

## R12 update
- Ceilings: `composer/expression/ceilings.py` validates RESOURCE_CEILING_REF + the seven ceilings at intake (absence refuses, nothing defaulted); `MAX_NODES`/`MAX_WINDOW` removed from schema.py. Not enforced, exact missing rules: MAX_STATE_ELEMENTS count for lag/rolling prototype constructs; class-to-structure compatibility (Annex req. 3); canonical ascending opcode CODE order (no code table).
- Operators: `composer/expression/sqe_opset.py` implements comparison, EQ_CANONICAL, SELECT (two branches, lazy), VECTOR_/MATRIX_ELEMENTWISE_*, FIXED_SUM, FIXED_DOT as reference semantics. Not wired to manifest admission (no numeric opcode table, no program byte grammar). Multi-branch CASE tie rule is missing. This is NOT a full SQE_OPSET_V1_1 implementation.
- D13/D14-D18 recovery: a Drive full-text search returned Build Plan versions V206-V213 only; their relevant clauses were not read in this segment. Status: INSUFFICIENT_EVIDENCE (search incomplete), not absence.

## R13 update: per-row inputs after reading the CURRENT sources first
Source order used: current Build Plan (Drive 1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo, read in full as text), Composer V9 s27/s28, Decision Context V4, News Hub V2; V206-V213 were NOT used. Section 27/28 and A1/H/9.0/9.2A definitions are RECOVERED (implemented, see R13 return).
| Row | Exact named source gap (after reading) | Responsible source-owner function | Blocks |
|---|---|---|---|
| D13 PACKAGE_HASH / FINAL_PACKAGE_HASH byte layout | Current Build Plan 5.x says CONSUMER_BINDING_ID is derived from "the canonical binding hash under the frozen contract" and the object binds FINAL_PACKAGE_HASH; the byte layout is in the frozen Annex/Contract, not in the Build Plan text. Annex DeliveredFeatureEntry hash exists in `schema/` (delivered_hash); the PACKAGE-level layout was not found. | Connected Contract / Annex owner (Manager) | recomputing H1 package hashes (currently inequality only) |
| D14 cutoff vs fence | Build Plan 11.2: eligibility is strict AVAILABLE_ASOF < SNAPSHOT_FENCE_TS. News Hub V2 uses `<= decision cutoff` for its own causal view. Not reopened: the Gateway strict rule controls binding. No source defines the conversion between "decision cutoff" and the fence. | Manager (time-semantics owner) | none for Gateway; resolver keeps its own wording |
| D15 reason -> status list | No `reason -> status` list found in the current Build Plan (REASON_CODE appears only as an index column). Decision Context H maps event class -> domain only. | Manager | automatic status derivation from reason codes |
| D16 settlement delay value | Build Plan 11.4: delay is visibility-only and never widens the fence; no duration given. | Manager / time-semantics | `check_settlement` input value |
| D17/D18 Health profile home/registry | Build Plan lists "A24 missing Health profiles" as pending documentary work; no profile registry or critical-set registry found. | Manager / Health owner | blast-radius thresholds (not needed for structural traversal), aggregate critical set |
| Numeric opcode codes, program byte grammar, CASE tie rule, MAX_STATE_ELEMENTS counting, class-structure compatibility | not defined by any admitted source read | A02/SPEC owner | canonical encoding/admission of new operators |
Group 4 (provider/clock/host/grants): unchanged; blocks real-world qualification only.
