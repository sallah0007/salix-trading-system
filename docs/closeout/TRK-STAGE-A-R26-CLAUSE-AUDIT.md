# TRK Stage A — R26 clause-level audit against the CURRENT BUILD PLAN (Coder, non-governing)
No governing-source text is copied; sources are cited by Drive ID and section. Build Plan = `1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo` (downloaded as text in R26, 2712 lines, sha256 `5c0a02d510aaf5dc986138fd2b899e447e25d97b19b476a104fa02854249c5cf`; Coder-read sections: 3/3.2A (placement), 9/9A, 10.1, 11, 12, 13/13A, 14/14.2/14A, 15/15.1/16/16.1, 17, 18/18A, 27 TR-01..TR-15, 28, 29A E-03 final map + R2-L1 cleanup). Registry `1eZThdektQNUc5uCNOM96K_rquZYOBoPMonjI3kX4CHo` (downloaded, 580 text lines; read: authority-transition evidence truth, causal imputation firewall, multi-stream snapshot clause, request/response manifest clause, test-control lines).
DERIVATION_CLASS = INDEPENDENTLY_DERIVED for reachability (tool `tools/audit_e03_callpaths.py`, static ast) and for the code facts cited (read in this repository); the clause text was read by the Coder. NOT re-opened in R26 (named, not guessed): Connected Contract V0.38 `1neiQsQ9AG-QKdyMgOqJxXE026D0uY___yhfGaTlIJ8Y` H1-H3, frozen Typed Annex V1.2 delivered-entry schema, MLCore, MasterHealth V3, DecisionContext V4, News Hub V2, Matrix paras 1068-1096, Composer V9 s7A/27/28. Rows whose conformance depends on those say so. Row presence and import reachability are NOT semantic conformance.

## A. TR matrix (Build Plan s27) — clause / callpath / tests / verdict
| TR | Build Plan clause (DoD) | Repo callpath (R26) | Tests / negatives | Verdict | Remaining (engineering vs source-owned) |
|---|---|---|---|---|---|
| TR-01 | generic execution; zero runtime model-name branches | `StatefulMaterializer.materialize` <- `tracker/pipeline.run`; `evaluator`; `reverify_pinned` re-runs the independent verifier | test_expression, test_pipeline, test_r11_arithmetic, R25/R26 reverify tests | IMPLEMENTED for the prototype grammar | byte-level program grammar/golden-vector contents are source-owned (A02/SPEC); Parent V1.2 is a governed Matrix-pinned adjunct per Matrix 1068-1096 (as reported; not re-opened) |
| TR-02 | quant intake adapter over existing Tracker lifecycle; no second registry/order/currentness | `tracker/quant_intake_adapter`, `tracker/pipeline` | test_r10/r11/r13/r16, pipeline | IMPLEMENTED (Tracker side); `tracker_identity` does not import `stage_a` (grep: zero hits) | real tracker_identity surface binding is Tracker-owned E-01 work |
| TR-03 | keyed canonical ordering; permutation invariant; duplicates rejected | `composer/expression/canonical_encoding`, `hashing` | test_expression, Q1/Q2 families | IMPLEMENTED | none located |
| TR-04 | manifest identity; exact frozen MANIFEST_HASH coverage | `manifest`, `hashing`, independent `manifest_digest`; R25 `materialization_hash` recomputed | verifier-independence tests, R25 B1 negatives | IMPLEMENTED for prototype hash domains | normative byte layout/domain tags source-owned; `accepted_manifest.read_accepted_manifest` is NOT accepted QuantManifest persistence |
| TR-05 | Composer boundary; no identity/certification/delivery authority in Composer | `tracker/build_output_check`, `composer/request_classification` (REFERENCE_ONLY: not on pipeline closure) | test_r10/r11/r13 | PARTIAL: classification module exists but no in-repo caller | wire request classification into intake once Composer V9 s27 mapping (D6) is admitted |
| TR-06 | NO_QUANT_FEATURE: failed requested build cannot become baseline-only/NONE | request_classification + `SimulatedGateway.resolve` (REQUIRED absent -> NON_DELIVERY) | boundary tests G3 | PARTIAL (Gateway half tested; classification half not wired) | same as TR-05 |
| TR-07 | Gateway-only delivery; no direct private connector | `gateway/contracts` (simulated), `fw/receiver`, `ml/receiver` consume only Binding objects | Q18/Q19/Q20/F4 tests | IMPLEMENTED against a SIMULATED Gateway | real Gateway/Contract V0.38 integration absent (E-01/E-02) |
| TR-08 | Health/B0 containment; profile evaluator evidence only | `health/envelope`, `health/evidence`; Core Health consumed by Gateway (R25/R26) | Q17 tests | PARTIAL: validators + Core callpath; no Health service | AntiReplay has no packet-consuming Health boundary in-repo (test asserts); MasterHealth V3 not re-opened |
| TR-09 | exact opcode equality and capability firewall | `stateful_verifier` (opcode/capability declaration equality), `opcodes`, `capability` | Q3-Q6 families, sweeps | IMPLEMENTED for the prototype opcode table | governed opcode table (D3) source-owned |
| TR-10 | half-open fence; technical latest never authority | `gateway/contracts.resolve` (G1 equality excluded, G7 stale watermark); `core/time_family` (as-of strict, ties held, per-timeframe snapshot R26) | G1/G2/G7, R25/R26 time-family tests | IMPLEMENTED for logic; calendar/instance UNBOUND | `stage_a/currentness.py` is REFERENCE_ONLY (no caller); D14 |
| TR-11 | one winner/fail closed; stale epoch fenced; rebuild proof | `coordination/*`, `object_store_journal`, Core `_commit` | concurrency/restart tests | IMPLEMENTED in-memory | real provider (E-01) absent; `fencing.py` and `interface.py` not on a pipeline closure |
| TR-12 | declared edge only; independent context route preserved | `context/decision_context`, `news_hub_v2` | context tests | REFERENCE_ONLY (no in-repo caller) | News Hub V2/Decision Context V4 field sections not re-opened (R26) |
| TR-13 | FW baseline/model/confluence: separate manifests/results/lineage | `fw/receiver`, `fw/lanes`, `fw/return_lineage` | F1-F3 | REFERENCE_ONLY (no caller from pipeline/Core) | FW ten-field/H3 payload fields (Contract V0.38 H3) not re-opened; wiring held individually |
| TR-14 | ML standalone/augmented; no hidden FW ancestry laundering | `ml/receiver` (ancestry, check_fw_augmented) | F4-F6, M1-M4 | REFERENCE_ONLY | six-join ML writer/finalizer/manifest-generation inputs: MLCore not re-opened |
| TR-15 | all keys instrument-qualified; no cross-instrument mutable state | `identifiers.Scope`, `storage/keys`, `tracker/registry`, `gateway.contracts` (rows keyed by instrument) | TR-15 isolation tests | IMPLEMENTED for key shape | provider-side isolation proof absent |

## B. E-03 rows (57) — clause mapping and verdict (reachability from `tools/audit_e03_callpaths.py`, PIPE/CORE/REVERIFY entry closures)
Legend: IMPL = implemented and on a callpath; IMPL-SIM = implemented against a simulation; REF = module exists, no in-repo caller; ALIAS = responsibility under another path (Manager mapping decision, not a rename); NOT_BUILT = no repo module.
| # | E-03 path | Clause (Build Plan) | Repo / callpath | Verdict | Irreducible input or engineering next |
|---|---|---|---|---|---|
| 1 | authority.py | s3.1, s9 no second authority | `AuthorityRef` (PIPE) | IMPL | D1/D2 principal admission is Owner/Manager |
| 2 | identifiers.py | s27 TR-15 instrument-qualified keys | Scope/FeatureKey (PIPE, REVERIFY) | IMPL | - |
| 3 | errors.py | s17 no generic exception creates authority | typed Refusal/IntegrityFailure (all closures) | IMPL | - |
| 4 | clocks.py | s18 replay pins; s11.4 settlement | `clocks` (PIPE) | IMPL | real clock/provider E-01/E-06 |
| 5 | currentness.py | s18, TR-10 | module exists; NO caller | REF | engineering: bind to Core/Gateway currentness (D14 decides authority source) |
| 6 | replay.py | s18 historical replay never substitutes latest | `replay` (PIPE); Core `_replay` | IMPL | - |
| 7 | observability.py | s25 | module only | REF | no real sink (E-06) |
| 8 | composer/request_classification.py | s3.2A routing only | module, 1 test, NO caller | REF | wire at Tracker/Composer boundary; D6 |
| 9-11 | governed_order_adapter / build_executor / refit_executor | s8 Composer-owned | none | NOT_BUILT (LATER, Composer side) | Composer owner; Tracker stays sole order issuer |
| 12 | composer/build_output.py | s8, TR-05 | ALIAS `tracker/build_output_check` (PIPE) | IMPL (Tracker check only) | producer is Composer's |
| 13-21 | expression/{manifest,schema,canonical_encoding,hashing,opcodes,capability,evaluator,fit_generation,artifacts}.py | s6, s7, TR-01/03/04/09 | all resolved by suffix; PIPE/REVERIFY closures | IMPL (prototype tables) | D3 governed code tables, byte grammar |
| 22 | tracker/quant_intake_adapter.py | s9 path, TR-02 | PIPE | IMPL | - |
| 23 | tracker/quant_certification.py | s9, s17 capability mismatch | PIPE | IMPL | - |
| 24 | tracker/publication.py | s9/9A (PUBLISHABLE is a row transition) | no caller | REF | engineering: call from pipeline accept path; blocked by 9A status-kind mapping |
| 25 | materialization/stateful_materializer.py | s7, TR-01 | PIPE, REVERIFY | IMPL | - |
| 26 | verification/stateful_verifier.py | s7, TR-09, s18A independence | REVERIFY; R25/R26 hardened (hash recomputation, FAIL/profile/version binding) | IMPL (author-independent, not appointed) | D4 independent oracle |
| 27 | verification/verification_result.py | s7 typed scoped result | PIPE/CORE/REVERIFY | IMPL | - |
| 28 | context/event_identity.py | s10.1 immutable event identity | ALIAS `context/decision_context` (CORE closure: fail-closed helper) | PARTIAL | identity key derivation from Decision Context V4 not re-opened |
| 29-31 | context/{coverage,applicability,resolver}.py | s10.1 | ALIAS `context/news_hub_v2` (no caller) | REF | News Hub V2 sections (9.0/9.2A) not re-opened |
| 32 | context/causal_gate.py | s10 completion verdict adapter | no module (derived helpers elsewhere) | NOT_BUILT | AVAILABLE_ASOF formula (source-owned) |
| 33 | gateway/dependency_resolution.py | s11.1-11.5, G1-G9 | ALIAS `gateway/contracts` (CORE/REVERIFY closure via Core.gateway_health); R26 (OVERCLAIM, withdrawn in R27: see closeout section 15): Core snapshots default-deny without exact feature/version/instrument/timeframe binding | IMPL-SIM | real Gateway absent |
| 34 | gateway/binding.py | s13A one DeliveredFeatureEntry object owned here | ALIAS `gateway/v038` + `contracts.Binding`; no single exact-schema DeliveredFeatureEntry owner module | PARTIAL | frozen Typed Annex V1.2 delivered-feature schema not re-opened; engineering: one owner module |
| 35 | gateway/non_delivery.py | s11.3 exactly one final outcome | ALIAS `v038.NonDeliveryResolutionV038`, `FinalResolutionStore` (no pipeline caller) | REF | D15/D12' |
| 36 | gateway/settlement.py | s11.4 settlement never widens fence | ALIAS `v038.check_settlement/classify_late` | REF | D16 |
| 37 | gateway/health_snapshot.py | s14, s17 Health unresolved -> no binding | ALIAS `contracts.HealthSnapshot`; R26 typed `CoreHealthSnapshot` + `HealthBinding` | IMPL-SIM | admitted external binding/provenance is a separate input |
| 38 | fw/request_adapter.py | s12 FW receives only Gateway packages | ALIAS `fw/receiver.receive` (receive-only; NOT request construction) | REF | request construction needs FW payload fields (Contract H3) |
| 39 | fw/input_binding.py | s12/13A read-only consumption | ALIAS `fw/lanes`, `descriptor_crosswalk` | REF | A04 bindings are false/unadmitted |
| 40 | fw/return_lineage.py | s12 Evidence/Requests/Lineage only | exact module | REF | FW return payload fields |
| 41 | ml/dataset_binding.py | s13/13A | ALIAS `ml/receiver.build_row` | REF | six joins null (A04/C25 producer bindings unadmitted) |
| 42 | ml/standalone_ancestry.py | s13.1 no direct/transitive FW ancestry; unknown fails closed | ALIAS `ml/receiver.ancestry/check_generation` | REF (logic tested) | no caller |
| 43 | ml/fw_augmented_rebind.py | s13.2 | ALIAS `ml/receiver.check_fw_augmented` | REF | FW ref contents; parent-binding join |
| 44 | ml/generation_lineage.py | s13.3 baseline/model/confluence lineage | ALIAS `ml/receiver` | REF | writer/finalizer/manifest-generation undeclared in readable sources |
| 45 | health/b0_adapter.py | s14 | ALIAS `health/envelope` (R25 AntiReplay full subject scope) | REF (validators) | no Health boundary consumes packets |
| 46 | health/quant_evidence.py | s14 Health subjects | ALIAS `health/evidence` | REF | profile instances |
| 47 | health/blast_radius.py | s14A (derived from lineage; carried evidence never overwrites LOCAL) | exact module, deps from `tracker/feature_lineage` | REF | adapter/persistence; D3 ref types |
| 48 | health/expectation.py | s14 | none (silence derivation only) | NOT_BUILT | expectation rule undefined in read sources |
| 49 | coordination/interface.py | s15.1 pluggable interface | exact module (0 test imports, no callpath) | REF | claim/commit/revoke/resolve_unknown_commit/read/advance/rebuild surface not mapped to a provider; E-01 |
| 50 | coordination/transition_record.py | s15 | PIPE | IMPL | - |
| 51 | coordination/object_store_journal.py | s15.1 fencing on every write, unknown-commit | PIPE/CORE/REVERIFY | IMPL-SIM | real provider (E-01/D10) |
| 52 | coordination/fencing.py | s15.1 mandatory fencing on every authority write | no caller (journal embeds epoch checks) | REF | engineering: single enforcement point |
| 53 | coordination/recovery.py | s15 rebuild | PIPE | IMPL | - |
| 54 | coordination/scheduler.py | s16/16.1 P0/P1/P2, anti-starvation, ceilings | exact module, no callpath; `tracker/reverify_scheduler` is a separate bounded pass (not this) | REF | QUANT_EXECUTION_SCHEDULING_POLICY_REF instance, ceilings: source-owned |
| 55 | storage/object_store.py | s4 | PIPE/CORE/REVERIFY | IMPL-SIM | real store E-01 |
| 56 | storage/postgres_read_model.py | s4/s15.1 non-canonical rebuildable read model | no caller | REF | no real DB |
| 57 | storage/keys.py | TR-15 | PIPE/CORE/REVERIFY | IMPL | - |
Summary (derived): IMPL/IMPL-SIM rows are on a callpath; REF rows are engineering to wire or source-gated; NOT_BUILT rows 9-11 are Composer-owned, 32/48 are source-gated.

## C. D1-D18 / D12' and A07 programme obligations (R26 state)
Decision rows D1-D18/D12' keep the section 4 states in the combined closeout (re-derived against the Build Plan only where a clause is cited above: D3 prototype tables, D4 oracle (s18A), D10/E-01 provider (s15.1), D13-D16 Gateway/settlement (s11), D17/D18 Health (s14)). They are NOT re-derived against Connected Contract V0.38 / Annex in R26: named blockers above. A07's four programme obligations and the 41 units/100 qualifiers stay OPEN; NL-0187 has a proposed delta only (`docs/a07/A07_NL0187_QUALIFIER_COMPARISON_PROPOSED_DELTA_R25.md`, wording tightened in R26).
