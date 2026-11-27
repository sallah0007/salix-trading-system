# Stage A Tracker - combined requirement closeout (R17, working draft, NOT a completion claim, NOT pre-approved sign-off)

CODER FINDING != SALIX DECISION. A merge, CI pass or this file clears no gate, hold or acceptance. A02 Class B HOLD, A07/COVERAGE OPEN, P12/N2 UNSATISFIED, QC34 ALERT(HOLD), A08 READY_TO_CODE NO and Stage A HOLD are unchanged. Authority: CLAUDE.md 2A (this repository only; Drive read-only). No SALIX AI, Stage B or live work; no principal/provider/host/grant appointment; no provider acceptance, probe or credential is inferred. The Tracker is the sole order issuer. No governing-source text is copied: sources are cited by ID/section and paraphrased. Every row below stays open until independent review and Manager recording in Drive.

How to read a row: STATE is one of INVOKED (the production path `tracker/pipeline.TrackerPipeline.run` reaches it by import AND the call is visible in the called-names ledger), REFERENCE_ONLY (exercised by tests and simulated counterparts; no production call path), NOT_BUILT, LATER (counterpart-owned, not Tracker code), OPEN (decision/source input). Import reachability is not invocation, invocation is not correctness, correctness is not operational qualification (the R16 `check_outcome_access` counterexample). `tests/trk_stage_a/test_r15_integration_ledger.py` pins reachability and which helpers the intake path actually CALLS; `test_r17_closeout_completeness.py` pins that every row named below exists here and that every cited code path exists.

## 0. R17 changes (Manager assignment Sat 03:51, items a-f)
a. OUTCOME_INFORMATION_ACCESS is mandatory on the ORDER (Composer V9 s7A ORDER_READY; s27 "where applicable" does not waive it). `composer/request_record.check_request_record(stage="ORDER")` refuses a missing declaration (ORDER_OUTCOME_ACCESS_DECLARATION_MISSING) or any value outside FORBIDDEN | PERMITTED_UNDER_DECLARED_FITTING_CONTRACT (..._UNKNOWN); PROPOSAL stage is unaffected. `build_output_check.check_conformance(bo, evidence, order_declaration)` binds the returned package to the governed order: the package must carry the declaration (BUILD_OUTPUT_OUTCOME_ACCESS_DECLARATION_MISSING) and it must equal the order's (OUTCOME_ACCESS_DECLARATION_CONFLICT, both directions). Nothing defaults to FORBIDDEN and the package is never trusted over the order. FORBIDDEN still needs Tracker-originated determined "not consulted" evidence (none/undetermined HELD, consulted FAILED). PERMITTED_UNDER_DECLARED_FITTING_CONTRACT is HELD (PERMITTED_FITTING_CONTRACT_NOT_VERIFIABLE): no read source defines a verifiable reference to the declared fitting contract. The no-quant path keeps its semantics because the declaration is demanded only where a quant build was requested (TR-06 row). Tests `test_r16_conformance_wiring.py` (order seam, binding, evidence, pipeline, labels), sweeps r16 (26/26 killed) and r17 (21/21 killed).
b. Finding 3 helper-only checks stay OPEN with their exact meaning. `check_inputs_resolve`: Composer s27 names the exact input IDs in prose fields that still impose semantic duties, and no key carries them; the absence of a token name is not permission to certify. `check_reproduction`: the pipeline independently recomputes manifest/graph/program hashes (real, domain-limited), which is NOT a build-output reproduction claim. Both are NOT called by intake, pipeline or build_output_check (pinned by `FunctionInvocation` tests). Full s28 conformance is NOT_ASSESSED_BOUNDARY and must not be called integrated or certified: every `Outcome.limits` carries `("S28_FULL_CONFORMANCE","NOT_ASSESSED_BOUNDARY")`.
c. Capability-emulation firewall (Parent V1.2; Annex certification requirements 3-6): class-to-structure verification is mandatory, and enum membership is not it. The prototype cannot determine compatibility (no read source defines the semantics), so `admit` carries `("CAPABILITY_CLASS_STRUCTURE","NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE")` in `Admission.unverified` and `Outcome.limits`; certification of the class must be labelled/held by any reader; an ambiguous classification belongs to GENERIC_EXTENSION review (source-owner step). Named source-owner input: the compatibility semantics.
d. This file now carries every TR, every E-03 path, D1-D18 and D12', A07-1..4, the 100-qualifier disposition and the baseline duties (sections 2-8).
e. Recovery facts, independently recomputed from the Drive bytes in an earlier pass (DERIVATION_CLASS = INDEPENDENTLY_DERIVED; reproducible by Manager = YES): mapping A04 (Drive 12h77ZuFRezmZr4_8Zrs1BDyYUtpnoMlI) = 61967 bytes, SHA256 ea9e7949397dd1e9ad001334425fdfeb96706d7eadca67bd043496d6ec91dfc0; C25 (Drive 1GuI4R58P3G8x9mo5NY9fGurA_Cq-lNjG) = 162037 bytes, SHA256 cd47a366f4cd49bef008bc97bfb8fcf04c5bb49f50fbd883cd875bcc82d20013. C25 has 41 total rows (13 planning + 14 producer requirements + 1 baseline gap + 5 broader groups + 8 source next-actions), which is NOT the companion's 39 selected pairs; all actual operational bindings are false. Feature-graph source triage (assessed, not assumed): the frozen Annex INPUT_DEPENDENCIES and `schema.objects.QuantManifest.input_dependencies` are source-PRESENT. Distinct states: (1) normative mapping present; (2) persistence/adapter MISSING (the pipeline admits the expression `Manifest` and journals hashes only; no QuantManifest is persisted or read back); (3) instances MISSING (no real manifest instance exists here); (4) D3 REF_TYPE vocabulary OPEN (which ref types denote a feature identity). New `tracker/feature_lineage.feature_deps_from_quant_manifests(manifests, feature_ref_types)` derives feature->feature dependencies from supplied QuantManifests, requires the ref types explicitly (empty refuses), refuses non-QuantManifest and self-dependency, and feeds `health/blast_radius` (a dependency target with no supplied manifest stays UNDETERMINED, never "unaffected"). REFERENCE_ONLY: it cannot prove the supplied manifests are the ACCEPTED ones. No graph is invented from prototype input names. Tests `test_r17_feature_lineage.py`.
f. E-01 harness and branches (section 9): harness integrated under `tests/provider_conformance/` (test/evidence tooling only, PROVIDER_ACCEPTED = NO); one concrete incompatibility found and fixed; claims.py diff inspected.

## 1. Integration ledger (derived from the actual import graph and called names)
Reachable from `TrackerPipeline.run` by non-test imports: authority, clocks, identifiers, errors, replay, storage/{byte_primitives,keys}, composer/request_record, composer/expression/{manifest,schema,canonical_encoding,hashing,opcodes,capability,evaluator,fit_generation,artifacts,ceilings}, coordination/{transition_record,recovery}, tracker/{quant_intake_adapter,build_output_check,quant_certification}, tracker/materialization/stateful_materializer, tracker/verification/{stateful_verifier,verification_result,independent_*}. Called by the intake path (visible in the called-names ledger): check_build_output, check_conformance, check_capability_declaration, check_request_record, check_fit_refs, check_declared, check_ceilings. Called by the pipeline: admit, certify, materialize, verify_materialization, validate_body/check_transition, resolve_unknown_commit.
REFERENCE_ONLY (no production call path; pinned absent from pipeline calls by test): context/news_hub_v2 (resolve_context), tracker/{lifecycle_status_event,status_projection,feature_lineage,publication}, health/{blast_radius,envelope,evidence}, gateway/{v038,contracts} (SIMULATED), fw/{receiver,return_lineage,descriptor_crosswalk,lanes}, ml/receiver, composer/expression/sqe_opset. The Tracker core does not import FW/ML/Gateway/Health consumers by architecture (dependency-direction test); their validators are exercised at the boundary against the simulated Gateway with really issued Bindings. Actual callers/adapters at the boundary: none are real. No real Composer, Gateway, FW, ML, Health, News Hub provider, clock or host is connected anywhere in this repository.

## 2. TR-01..TR-15 (Build Plan E03 s27 matrix; row = source / callpath / test / gap)
| Row | Requirement (paraphrase) | STATE | Implementation and callpath | Tests / review state | Exact gap, owner, consequence, recommended decision |
|---|---|---|---|---|---|
| TR-01 | Generic runtime execution of admitted expressions (stateful materializer + evaluator + capability) | INVOKED | `tracker/materialization/stateful_materializer.StatefulMaterializer.materialize` <- `pipeline.run`; `composer/expression/evaluator.evaluate` | test_expression, test_pipeline, test_r11_arithmetic; mutation sweeps r11/r12 | Numeric opcode table, program byte grammar, binary64 rule are A02/SPEC inputs (D3); SQE_OPSET (`sqe_opset`) not wired to admission. Consequence: execution is correct to the prototype grammar only. Owner: A02/SPEC. |
| TR-02 | Lifecycle and identity (intake adapter + tracker identity) | INVOKED | `tracker/quant_intake_adapter.admit` (dimensions incl. REQUEST_RECORD, RESOURCE_CEILING, CAPABILITY_DECLARATION, BUILD_OUTPUT_CONTRACT, BUILD_CONFORMANCE) -> identity reserve/lookup via tracker_component | test_pipeline, test_r11_intake_request, test_r12_ceilings, test_tracker_component | Identity assignment stays Owner/Manager governed (D2). Policy hash e5fbe7d3631a... pins the dimension list. |
| TR-03 | Keyed canonical ordering | INVOKED (prototype encoding) | `composer/expression/canonical_encoding`, `storage/byte_primitives`, `storage/keys` | test_expression, test_foundations; independent oracle `tracker/verification/independent_encoding` | Sort rule and wire layouts are D3/D13 inputs; the independent oracle is a second implementation by the same author (D4). |
| TR-04 | Manifest identity | INVOKED | `composer/expression/{manifest,hashing}`; intake recomputes graph/program/manifest hash and checks against declared | test_expression, test_verifier_independence | Correct hashing does not prove correct identity: field semantics of the manifest schema are D3/D6. |
| TR-05 | Composer boundary (package/order seam) | INVOKED (Tracker side); Composer producer LATER | `composer/request_record`, `request_classification`, `tracker/build_output_check`; seam `admit` | test_r10/r11/r13/r16 | Composer-side producer is the Composer owner's. Prose-only s27 items not enforced (D6). R17: ORDER_READY declaration answered by V9 s7A and enforced. |
| TR-06 | NO_QUANT_FEATURE semantics (request classification + Gateway dependency resolution) | PARTLY INVOKED | Classification: `request_classification.route_from_adapter`, `request_record` (REVIEW_REQUIRED on UNKNOWN consumer); Gateway dependency resolution is SIMULATED (`gateway/contracts`) | test_r11_intake_request (NO_QUANT_FEATURE path, QUANT_FEATURE path, FAILED_REQUESTED_BUILD) | D8: routing predicate is an explicit flag, not a source-defined predicate; Gateway-side resolution has no real implementation. No-quant semantics preserved: no outcome-access declaration is demanded where no quant build is requested. |
| TR-07 | Gateway-only delivery to FW/ML | REFERENCE_ONLY (SIMULATED) | `gateway/v038` (check_h1, check_both_separation, check_settlement, FinalResolutionStore), `gateway/contracts.SimulatedGateway`; `fw/receiver.receive`; `ml/receiver` | test_v038_conformance, test_r11_both, test_r13_fw_return, test_r12_ml_augmented | D13 hash/byte layouts, D14 cutoff vs fence, D15 reason->status, D16 delay value; real Gateway absent; FinalResolutionStore is single-process in-memory (D10). |
| TR-08 | Health / B0 containment | REFERENCE_ONLY | `health/envelope` (derive_silence, aggregate_state, attribute_failure), `health/evidence`, `health/blast_radius` | test_health_envelope, test_r12_blast_radius | D17/D18 profile home, thresholds, registry; real Health provider absent. Blast radius never writes a health state (14A). |
| TR-09 | Operator-set certification | INVOKED | `tracker/verification/stateful_verifier.verify_materialization`, `composer/expression/{opcodes,capability}.check_declared`, `tracker/quant_certification.certify` | test_verifier_independence, test_expression | Class-to-structure verification NOT VERIFIED (R17 item c); certification requirements 3-6 for the class not determinable here. Owner: source (Parent V1.2/Annex). |
| TR-10 | Causality / currentness | PARTLY | `currentness.resolve_asof`, `context/decision_context.as_of_visible`, `news_hub_v2.event_consumable` (REFERENCE_ONLY); gateway dependency resolution SIMULATED | test_foundations, test_r14_event_causality, test_context_contracts | D14 relation of cutoff to fence undecided (resolver must not feed the Gateway); D12' REQUEST_AFTER_CUTOFF trigger. |
| TR-11 | Durable claim / coordination | INVOKED (in-memory/object-store journal) | `coordination/{interface,object_store_journal,fencing,recovery,scheduler,transition_record}`, `tracker_component/claims` (ClaimService) | test_pipeline, test_tracker_component, test_registration_atomicity | D1 install ClaimService.authorizes into baseline authority; D10 cross-journal atomicity; real object store/lease provider absent (D5/E-01 harness is tooling only). |
| TR-12 | Event/Context side edge | REFERENCE_ONLY | `context/edge.assert_declared`, `context/decision_context`, `context/news_hub_v2` | test_context_contracts, test_r13_context_resolver, test_r14_event_causality | D13 encodings for Event/Context objects; COVERAGE_BASIS key spellings; ingestion glue is the News Hub component's. |
| TR-13 | FW baseline / model / confluence | REFERENCE_ONLY | `fw/{receiver,lanes,descriptor_crosswalk,return_lineage}` | test_r09_boundaries, test_r13_fw_return | Mapping A04: five H3 carriers map directly, five partial/missing/internal; FW payload fields undefined; all real bindings false. |
| TR-14 | ML standalone / augmented | REFERENCE_ONLY | `ml/receiver` (ancestry, check_generation, check_fw_augmented -> AugmentedCheck, require_verified) | test_r16_ml_ancestry, test_r12_ml_augmented | ML writer/finalizer/manifest declaration and six joins null in source; revoked-generation revival and Gateway restore unresolved. A07-1 qualifiers. |
| TR-15 | EURUSD isolation (instrument-qualified keys) | INVOKED | `identifiers.FeatureKey/Scope`, `storage/keys` namespace-qualified keys | test_foundations, test_registration_atomicity | Isolation is structural (key qualification); no cross-instrument consumer exists to test against. |

## 3. E-03 module tree (57 paths; alias/responsibility mapping, no gratuitous rename)
EXACT = same path exists. ALIAS = responsibility lives under another path (renaming is a Manager mapping decision). NOT_BUILT = no Tracker code, with exact missing input.
| # | E-03 path | Repo location | STATE | Gap |
|---|---|---|---|---|
| 1 | stage_a/authority.py | `stage_a/authority.py` (AuthorityRef) EXACT | INVOKED | D1/D2 |
| 2 | stage_a/identifiers.py | `stage_a/identifiers.py` EXACT | INVOKED | - |
| 3 | stage_a/errors.py | `stage_a/errors.py` EXACT | INVOKED | - |
| 4 | stage_a/clocks.py | `stage_a/clocks.py` EXACT | INVOKED | real clock/provider (E-01/E-06) |
| 5 | stage_a/currentness.py | `stage_a/currentness.py` EXACT | REFERENCE_ONLY | D14 |
| 6 | stage_a/replay.py | `stage_a/replay.py` EXACT | INVOKED | - |
| 7 | stage_a/observability.py | `stage_a/observability.py` EXACT | REFERENCE_ONLY | no real sink |
| 8 | composer/request_classification.py | `stage_a/composer/request_classification.py` EXACT | INVOKED | D8 |
| 9 | composer/governed_order_adapter.py | none; order issuance in tracker_component/order + `tracker/authority_bridge.py` | LATER (Composer side) | Tracker remains sole order issuer |
| 10 | composer/build_executor.py | none | LATER | Composer-owned |
| 11 | composer/refit_executor.py | none | LATER | Composer-owned |
| 12 | composer/build_output.py | ALIAS `stage_a/tracker/build_output_check.py` (Tracker-side check only) | INVOKED | producer LATER; D6 |
| 13 | expression/manifest.py | `stage_a/composer/expression/manifest.py` EXACT | INVOKED | D3 |
| 14 | expression/schema.py | `.../expression/schema.py` EXACT | INVOKED | D3 |
| 15 | expression/canonical_encoding.py | `.../expression/canonical_encoding.py` EXACT | INVOKED | D3/D13 |
| 16 | expression/hashing.py | `.../expression/hashing.py` EXACT | INVOKED | D13 |
| 17 | expression/opcodes.py | `.../expression/opcodes.py` EXACT | INVOKED | numeric opcode table D3 |
| 18 | expression/capability.py | `.../expression/capability.py` EXACT | INVOKED | class-to-structure NOT VERIFIED |
| 19 | expression/evaluator.py | `.../expression/evaluator.py` EXACT | INVOKED (via materializer) | binary64/sort D3 |
| 20 | expression/fit_generation.py | `.../expression/fit_generation.py` EXACT | INVOKED | - |
| 21 | expression/artifacts.py | `.../expression/artifacts.py` EXACT | INVOKED | - |
| 22 | tracker/quant_intake_adapter.py | `stage_a/tracker/quant_intake_adapter.py` EXACT | INVOKED | - |
| 23 | tracker/quant_certification.py | `stage_a/tracker/quant_certification.py` EXACT | INVOKED | D7 |
| 24 | tracker/publication.py | `stage_a/tracker/publication.py` EXACT | REFERENCE_ONLY | no pipeline call |
| 25 | materialization/stateful_materializer.py | `stage_a/tracker/materialization/stateful_materializer.py` EXACT | INVOKED | - |
| 26 | verification/stateful_verifier.py | `stage_a/tracker/verification/stateful_verifier.py` EXACT | INVOKED | D4 |
| 27 | verification/verification_result.py | `.../verification/verification_result.py` EXACT | INVOKED | - |
| 28 | context/event_identity.py | ALIAS `stage_a/context/decision_context.py` (domain_for_event, check_envelope) | REFERENCE_ONLY | identity key derivation not verified (D13) |
| 29 | context/coverage.py | ALIAS `stage_a/context/news_hub_v2.py` (check_dimensions) | REFERENCE_ONLY | COVERAGE_BASIS keys |
| 30 | context/applicability.py | ALIAS `stage_a/context/news_hub_v2.py` | REFERENCE_ONLY | APPLICABILITY_MAP_ID/VERSION keys |
| 31 | context/resolver.py | ALIAS `stage_a/context/news_hub_v2.py` (resolve_context, consumer_events) | REFERENCE_ONLY | governed revision rule; D14 |
| 32 | context/causal_gate.py | ALIAS `news_hub_v2.event_consumable` + `decision_context.as_of_visible` | REFERENCE_ONLY | AVAILABLE_ASOF formula (derived floor only) |
| 33 | gateway/dependency_resolution.py | ALIAS `stage_a/gateway/contracts.py` (DependencyEntry, SimulatedGateway) | REFERENCE_ONLY (SIMULATED) | real Gateway absent |
| 34 | gateway/binding.py | ALIAS `stage_a/gateway/v038.py` (check_h1, check_both_separation, check_binding_matches_identity), `contracts.Binding` | REFERENCE_ONLY | D13 |
| 35 | gateway/non_delivery.py | ALIAS `v038.NonDeliveryResolutionV038`, `to_v038`, `FinalResolutionStore` | REFERENCE_ONLY | D15, D12' |
| 36 | gateway/settlement.py | ALIAS `v038.check_settlement`, `classify_late` | REFERENCE_ONLY | D16 |
| 37 | gateway/health_snapshot.py | ALIAS `contracts.HealthSnapshot` | REFERENCE_ONLY | real Health provider |
| 38 | fw/request_adapter.py | ALIAS `stage_a/fw/receiver.py` (receive) | REFERENCE_ONLY | FW payload fields |
| 39 | fw/input_binding.py | ALIAS `stage_a/fw/lanes.py`, `fw/descriptor_crosswalk.py` | REFERENCE_ONLY | A04 bindings false |
| 40 | fw/return_lineage.py | `stage_a/fw/return_lineage.py` EXACT | REFERENCE_ONLY | FW return payload fields |
| 41 | ml/dataset_binding.py | ALIAS `stage_a/ml/receiver.py` (build_row) | REFERENCE_ONLY | six joins null |
| 42 | ml/standalone_ancestry.py | ALIAS `ml/receiver.ancestry/check_generation` (transitive FW ancestry refused) | REFERENCE_ONLY | - |
| 43 | ml/fw_augmented_rebind.py | ALIAS `ml/receiver.check_fw_augmented` | REFERENCE_ONLY | content of FW refs; binding-to-parent join undefined |
| 44 | ml/generation_lineage.py | ALIAS `ml/receiver.py` | REFERENCE_ONLY | writer/finalizer undeclared |
| 45 | health/b0_adapter.py | ALIAS `stage_a/health/envelope.py` | REFERENCE_ONLY | D17/D18 |
| 46 | health/quant_evidence.py | ALIAS `stage_a/health/evidence.py` | REFERENCE_ONLY | D17/D18 |
| 47 | health/blast_radius.py | `stage_a/health/blast_radius.py` EXACT (+ `tracker/feature_lineage.py` source of deps) | REFERENCE_ONLY | persistence/adapter + instances + D3 ref types; action for UNDETERMINED non-required consumer has no source rule |
| 48 | health/expectation.py | none (health/envelope.derive_silence covers silence only) | NOT_BUILT | expectation rule undefined in read sources; D17/D18 |
| 49 | coordination/interface.py | `stage_a/coordination/interface.py` EXACT | INVOKED | - |
| 50 | coordination/transition_record.py | `.../transition_record.py` EXACT | INVOKED | D12 resolved by V0.38 text |
| 51 | coordination/object_store_journal.py | `.../object_store_journal.py` EXACT | INVOKED | real provider absent (D10) |
| 52 | coordination/fencing.py | `.../fencing.py` EXACT | INVOKED | - |
| 53 | coordination/recovery.py | `.../recovery.py` EXACT | INVOKED | - |
| 54 | coordination/scheduler.py | `.../scheduler.py` EXACT | REFERENCE_ONLY | no pipeline call |
| 55 | storage/object_store.py | `stage_a/storage/object_store.py` EXACT | INVOKED (in-memory) | real store (E-01) |
| 56 | storage/postgres_read_model.py | `stage_a/storage/postgres_read_model.py` EXACT | REFERENCE_ONLY | no real DB |
| 57 | storage/keys.py | `stage_a/storage/keys.py` EXACT | INVOKED | - |
The tests/stage_a/ tree (unit, integration, concurrency, replay, mutants, reference_evaluator, golden_mirrors, e2e) is mapped to `tests/trk_stage_a/` (unit/integration/mutation sweeps) and `tests/provider_conformance/`; concurrency, golden_mirrors and e2e directories are NOT_BUILT as such (no real counterparts to mirror).

## 4. Decisions D1..D18 and D12'
| Row | Subject | State | Exact missing input / owner / consequence / recommended decision |
|---|---|---|---|
| D1 | Install ClaimService.authorizes into baseline authority | OPEN (Manager) | authorization is exercised in tests only; baseline path authority lacks the hook. Recommend: record install point. |
| D2 | Order-signer / TrustAnchor / principal-grant appointment | OPEN (Owner appointment) | `principals.GRANT_EVIDENCE_FIELDS` is a shape only; appoints nobody. |
| D3 | A02 SPEC manifest schema, ENUM and REF_TYPE code tables, opcodes, binary64, sort rule | OPEN (A02/SPEC owner) | prototype tables in `schema/candidate_code_tables.py` are candidates, not governed. Blocks feature-graph ref types, opcode table. |
| D4 | Independent expected-bytes oracle | OPEN (reviewer/Manager) | `tracker/verification/independent_*` is a second implementation by the same author; an independent oracle is a separate commission. |
| D5 | R5 provider qualification | OPEN | `tests/provider_conformance` is evidence tooling only; PROVIDER_ACCEPTED = NO. |
| D6 | Composer s27/s7A/s28 field mapping | OPEN (partly answered) | `docs/proposals/D6_composer_s27_mapping.md`; R17 answers the OUTCOME_INFORMATION_ACCESS element; prose-only fields remain. |
| D7 | Certified-ABSENT producer/certifier | OPEN (M/S) | certifier role/scope/interval not named by source. |
| D8 | TR-06 routing predicate | OPEN | explicit flag used; source predicate unread. |
| D9 | stage_a depends on tracker_component | OPEN (Manager mapping) | dependency exists in code and is allowed by the dependency-direction test; needs recording. |
| D10 | Cross-journal atomicity | OPEN | single-process journals; real provider needed. |
| D11 | Lane names non-canonical | OPEN (reframed) | lane names are prototype labels. |
| D12 | (resolved by V0.38 text) | RESOLVED IN SOURCE TEXT; code follows | not a gate clearance. |
| D12' | REQUEST_AFTER_CUTOFF trigger | OPEN (S) | trigger undefined; unknown reasons are REJECTED in code (fail closed). |
| D13 | Byte encodings for FINAL_RESOLUTION/PACKAGE/FINAL_PACKAGE hashes and Event/Context objects | OPEN (S) | inequality checks only; no layout invented. |
| D14 | News cutoff `<=` vs Gateway fence `<` | OPEN RISK | Manager did not adopt cutoff == fence; the resolver must not feed the Gateway until recorded; tests pin the divergence. |
| D15 | NON_DELIVERY reason -> status | OPEN (M) | candidate list in D_decision_package; unknown reasons REJECTED. |
| D16 | SETTLEMENT_DELAY value / certified lag | OPEN (M/O) | no measurement exists. |
| D17 | News/Context Health profile home | OPEN (M) | proposed home only. |
| D18 | Health thresholds/registry | OPEN (S) | thresholds, flap limits, critical set unsupplied. |

## 5. A07-1..4
| Row | Subject | State | Note |
|---|---|---|---|
| A07-1 | 100 ML s26.S qualifiers | OPEN: all 100 remain RAISE_FOR_SOURCE_OWNER_DISPOSITION | hashes 100/100 reproduced, refs 100/100 resolved, 65 cite no current line; none awarded or accepted; files `docs/a07/V232_26S_*.csv`. Owner: ML source owner. |
| A07-2 | R06 V03 three-role vs Owner staffing | OPEN (Owner) | meet or waive in writing. |
| A07-3 | R06 V10 whole-domain history | OPEN (Owner/Manager) | Drive Activity export or a bounded-history waiver scoped to A07; revisions alone insufficient. |
| A07-4 | A01 currentness (21 ASSERTED_UNBOUND, 510 reference sets), QC34, D19/D22 effectiveness, D23/D24/D26/Q03 | OPEN (named source owners) | QC34 ALERT(HOLD) unchanged. |

## 6. The 100 ML qualifiers (disposition)
Every one remains RAISE_FOR_SOURCE_OWNER_DISPOSITION. Evidence floor: hashes 100/100 reproduced and refs 100/100 resolved in an earlier pass (INDEPENDENTLY_DERIVED; reproducible by Manager = YES); 65 cite no current ref. Semantic dispositions are proposals only (`docs/proposals/ML_joins_and_qualifiers.md`), none awarded. Per-qualifier text is private governing source and is not reproduced.

## 7. Full-Tracker baseline duties
| Duty | State | Evidence / gap |
|---|---|---|
| Identity / registration atomicity | INVOKED | tracker_component + test_registration_atomicity; real store absent |
| Intake admission (seven-field-style + ceilings + request record + build-output + conformance + capability) | INVOKED | `admit`; policy hash pinned |
| Composer s28 23-field report | INVOKED with limits | OUTCOME_INFORMATION_ACCESS_VERDICT NOT_ASSESSED_BOUNDARY (pinned); `Outcome.limits` carries unverified duties |
| Independent verification of hashes/materialization | INVOKED (domain-limited) | covers manifest/graph/program recomputation only |
| Journal/replay/recovery | INVOKED (in-memory) | provider absent |
| Status projection -> Gateway | REFERENCE_ONLY | needs status-origin principal and record->StatusFact mapping (no StatusFact field is a journal body field; pinned) |
| Blast radius / feature lineage | REFERENCE_ONLY | see R17 item e |
| Tracker -> FW (ten fields / H3 ownership) | REFERENCE_ONLY | A04 bindings false |
| Tracker -> ML (writer/finalizer/manifest/generation/lineage) | REFERENCE_ONLY | transitive ancestry and verified rebind enforced structurally; writer undeclared |
| Health blast radius containment | REFERENCE_ONLY | D17/D18 |

## 8. Honest limits that survive this pass
No real conformance-evidence provider exists (only SIMULATED test evidence), so in real use every package is HELD; PERMITTED is HELD; helper checks `check_inputs_resolve`/`check_reproduction` are NOT connected; full s28 conformance NOT_ASSESSED_BOUNDARY; class-to-structure compatibility NOT_VERIFIED; feature lineage is not persisted or wired. Incomplete search is not absence: this pass did not re-open the full Build Plan, Composer V9, Decision Context V4, News Hub V2 or governance documents beyond the E03 tree and TR matrix text; clauses carried from earlier reads are cited by section only.

## 9. E-01 harness, branches and preservation (read-only inspection; nothing deleted or rebased)
E-01: `origin/e01/conformance-harness` (DC-037/038/039; 13 files) integrated into `tests/provider_conformance/` (77 tests). It has no `stage_a` imports. One incompatibility: `NonProductionBoundary.test_harness_creates_no_stage_a_runtime_tree` asserted the `stage_a` directory was absent (true only before stage_a existed); replaced by `test_no_stage_a_runtime_module_imports_the_harness` (reverse-import scan: no stage_a module imports the harness). Harness is test/evidence tooling only; it qualifies no provider.
`tracker-component-construction-layer`: claims.py diff shows main has MORE (claim/consumed_record/authorizes); no unique retained work. `e01-conformance-harness` (README only) is superseded by `e01/conformance-harness`. `stage-a/tracker/full-component` is an older snapshot. annex-conformance, boundaries, consolidated-r03/05/06, review-r04 have no commits beyond main. docs/*, pr6-*, type1/* are other work lines. Everything stays recoverable on GitHub.

## 10. Next dependency
(1) Manager records D14 relation, the status-origin principal, and (D3) the REF_TYPE vocabulary. (2) Source-owner compatibility semantics for the capability class. (3) A real Tracker verification path that produces outcome-access evidence, or a Manager decision on PERMITTED. (4) FW payload fields, ML writer/finalizer declaration. (5) Independent review.
