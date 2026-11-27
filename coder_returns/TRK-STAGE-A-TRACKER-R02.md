# TRK-STAGE-A-TRACKER-R02 — full-component coverage/gap matrix and D1–D10

Author: Claude (Trading Bot 7), CLAUDE.md §2A. CODER FINDING != SALIX DECISION. No gate, hold, acceptance or stage is cleared. Drive untouched.
**Correction to R01:** R01 called the component "built". It is AUTHORING-INCOMPLETE: the merged expression layer does not conform to Annex V1.2 (see A07 package §7) and several boundaries are unbuilt.
Evidence state: AUTHORING COMPLETE = NO · COMPONENT VERIFIED = NO (author-tested only; no independent oracle) · PROVIDER-DEPENDENCY QUALIFIED = NO · INTEGRATED/OPERATIONAL = NO.

## Evidence floor
DERIVATION_CLASS = INDEPENDENTLY_DERIVED (run this session). EXACT_INPUTS = branch `stage-a/tracker/annex-conformance` on main 5fbe576e758a487175b50532283809e12da54c57.
METHOD: `python3 -m pytest tests -q` → 505 passed; schema mutants: 8 injected into stage_a/schema, 8 caught. REPRODUCIBLE_BY_MANAGER = YES.
Not re-run since compaction: tests/trk_stage_a/mutation_sweep.py (22 mutants; last result was 22/22 killed in R01).

## Coverage matrix (Build Plan §27 TR-01..15; §§20–22 families)
Status key: PROTO = built against non-conformant prototype · ANNEX-PART = Annex objects/encodings only · NOT BUILT · BLOCKED = needs source/decision.
| Req | Code | Meaningful test evidence | Integration | Gap / authority |
|---|---|---|---|---|
| TR-01 generic execution, no model dispatch | tracker/materialization/stateful_materializer.py, composer/expression/evaluator.py | test_no_model_name_dispatch_in_evaluator_source (Q15); batch==incremental bit-exact | none | PROTO; Annex SQE_OPSET_V1_1 arithmetic BLOCKED on A02 SPEC (D3) |
| TR-02 existing Tracker lifecycle | tracker/quant_intake_adapter.py, pipeline.py, authority_bridge.py | pipeline tests (44), baseline-seam test | uses baseline `tracker_identity` in-process; seam hard-False | resolver NOT installed (D1); certified ABSENT producer missing (D7) → production happy path unreachable |
| TR-03 keyed canonical ordering | expression/canonical_encoding.py; schema/objects.sort_keyed | Q1/Q2 on prototype; schema order/duplicate tests | — | PROTO + ANNEX-PART; "canonical bytes" sort-key interpretation is mine (D3) |
| TR-04 manifest identity | expression/manifest.py; schema/objects.manifest_hash | Q1 invariance, field-sensitivity (Annex objects) | — | hashes provisional until code tables admitted (D3) |
| TR-05 Composer boundary | composer/* | boundary/dependency-direction tests (3), test_kinds_not_interchangeable | — | §27/§7A, §28 mapping is author judgement (D6); Q19 only structural |
| TR-06 NO_QUANT_FEATURE semantics | pipeline request classification | failed_requested_build_never_becomes_no_quant_feature; explicit no-quant tests | Gateway resolution NOT BUILT | predicate is a flag (D8) |
| TR-07 Gateway-only delivery | stage_a/gateway,fw,ml = empty packages | none | none | NOT BUILT (Gateway/FW/ML delivery); Q18/Q19/Q20/F4 NOT RUN |
| TR-08 Health/B0 containment | observability event sink only | none | none | NOT BUILT; Q17 NOT RUN; Health contract not admitted |
| TR-09 operator-set certification | verification/stateful_verifier.py, opcodes.py, capability.py | independence tests (17), neutered-check tests, evaluator-defect tests | none | PROTO; Q3–Q8 not at Annex level (D3, D4) |
| TR-10 causality/currentness | currentness.py, replay.py | AS_KNOWN vs EVENTUAL, technical-latest-not-authority | Gateway fence NOT BUILT | G1/G2/G7 NOT RUN (need Gateway) |
| TR-11 durable claim/coordination | coordination/* | fencing, orphan, unknown-commit, concurrency, restart tests | object_store_journal on in-memory/stand-in store | unqualified provider (D5); cross-journal atomicity by ordering (D10) |
| TR-12 Event/Context edge | none | none | none | NOT BUILT; contract not read to admission |
| TR-13 FW baseline/model/confluence | none | none | none | NOT BUILT; F1–F3, Q13 NOT RUN |
| TR-14 ML standalone/augmented | none | none | none | NOT BUILT; F4–F6, M1–M4 NOT RUN |
| TR-15 EURUSD isolation | keys instrument-qualified (storage/keys.py) | test_scope_isolation_keys_differ, same-id-different-instrument | none | key-level only; cross-instrument behavioural tests NOT RUN |
Families not run: Q9/Q10 fit-generation generation (fit production NOT BUILT), Q16 replay-storm, Q21–Q23, G1–G9, OB1/OB2, F1–F6, M1–M4, Annex-level Q6/Q8.

## D1–D10 with exact authority needed
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

## Unblocked work remaining (continuing, within authority)
Independent verifier-side composition for Annex objects; status/speculation state machines (Q21/Q22); Gateway/FW/ML/Health contract *objects* only where sources define fields;
replay-storm fairness test (Q16); cross-instrument behavioural tests (TR-15). Blocked items are not built around.

## Seven lenses
MATHEMATICAL=YES · DATA_SCIENCE=NA (no fitting/data) · SOFTWARE_ARCHITECTURE=YES · ADVERSARIAL=YES · TRADING_MICROSTRUCTURE=NA (no market data/execution) · GOVERNANCE=YES · FALSIFICATION=YES.

## Independent review
Not obtained. Request packet for the Manager (via Owner relay): this file, docs/a07/A07_RECONCILIATION_AND_CLOSURE_EVIDENCE_R01.md, branch diff.
No review is claimed complete.
