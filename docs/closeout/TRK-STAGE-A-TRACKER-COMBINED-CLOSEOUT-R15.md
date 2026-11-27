# Stage A Tracker - combined requirement closeout (R15, working draft, NOT a completion claim)

CODER FINDING != SALIX DECISION. A merge, CI pass or this file clears no gate, hold or acceptance. A02 Class B HOLD, A07/COVERAGE OPEN, P12/N2, QC34 ALERT(HOLD), A08 READY_TO_CODE NO, Stage A HOLD are unchanged. Authority: CLAUDE.md 2A (this repository only; Drive read-only). No SALIX AI, Stage B, live work, principal/provider/host/grant appointment. No governing-source text is copied; sources are cited by ID/section. Rows below stay open until independent review and Manager recording in Drive.

## 0. Exact state
Base main f7b10079d4dc42649e3e5c6a7eac36168f9db6db (PRs #35 a3ac165, #36 1655a94, #37 d4a595b, #38 f7b1007). Local R14 branch head 5b00e88 had an EMPTY tree diff against main (squash-merged), so tested == merged. No stashes, no uncommitted work existed before this pass. Remote branches (annex-conformance, boundaries, consolidated-r03/05/06, review-r04, full-component, e01/*, type1/* etc.) were left untouched. Work in this pass: branch stage-a/tracker/full-pass-r15 (this PR).

## 1. Integration vs reference-only (derived from the actual import graph, enforced by tests/trk_stage_a/test_r15_integration_ledger.py)
INTEGRATED (reachable by non-test imports from `tracker/pipeline.TrackerPipeline.run`): quant_intake_adapter (seven-field-style admission dimensions incl. REQUEST_RECORD, RESOURCE_CEILING, CAPABILITY_DECLARATION, BUILD_OUTPUT_CONTRACT), build_output_check, ceilings, request_record, transition_record, quant_certification, stateful_materializer/verifier, authority.
REFERENCE_ONLY (exercised only by tests; no production call path; NOT to be described as integrated): context/news_hub_v2 (resolver), tracker/lifecycle_status_event, tracker/status_projection, health/blast_radius, gateway/v038 and gateway/contracts (SIMULATED gateway), fw/receiver, fw/return_lineage, fw/descriptor_crosswalk, ml/receiver, composer/expression/sqe_opset, health/envelope, health/evidence, tracker/publication.
Reachability is not correctness and not operational qualification. No real counterpart (Composer, Gateway, FW, ML, Health, News Hub provider, clock, host) is connected anywhere in this repository.

## 2. Before/after targeted checks (BEFORE = main f7b1007 worktree, AFTER = this branch; passed counts)
1 Composer package/conformance + admission 84 -> 84; 2 Tracker->FW 44 -> 44; 3 Tracker->ML 46 -> 46; 4 committed-journal status projection->Gateway 15 -> 15; 5 Health blast radius 17 -> 17; 6 context resolver 36 -> 41 (+5 R15 tests). Full-suite rerun and mutation sweeps on changed code are in the PR evidence. Unchanged-area tests were reused, not rewritten.

## 3. Changes in this pass
- news_hub_v2 `resolve_context`: verdict is now typed. MULTIPLE_CANDIDATES (REQUIRE_EXPLICIT_SELECTION) and NON_AUTHORITATIVE_SELECTION are never "USABLE". The `governed_revision_rule` argument is a caller NAME, never proof; `selection_rule_verified` is always False; `admission` states STRUCTURAL_ONLY_NOT_PROVIDER_OR_SOURCE_ADMITTED. `consumer_events(result)` is the sole sanctioned consumer path and refuses anything but plain USABLE. A REQUIRED consumer still needs a verified provider/source admission this module cannot supply.
- Integration ledger test + journal->status-fact gap test (below).

## 4. Requirement rows (source / commit / call path / test, or exact missing input + owner function + consequence + recommended Sallah decision)
| Row | State | Evidence or exact gap |
|---|---|---|
| Composer s27 BUILD_OUTPUT_PACKAGE (Composer V9 s27) | INTEGRATED (Tracker-side check) | #37; admit -> BUILD_OUTPUT_CONTRACT; test_r13_build_output. Composer-side producer is LATER (Composer owner). Prose-only s27 items not enforced (no key names in source). |
| Composer s28 conformance + 23-field report | INTEGRATED | tracker_component/report via pipeline; test_pipeline. Cross-field validation beyond existing rules = reviewer judgement, not source. |
| E03 composer/governed_order_adapter, build_executor | LATER | Composer-side; Tracker stays sole order issuer (authority_bridge). Owner function: Composer. |
| E03 context/resolver | REFERENCE_ONLY | #37/#38 + this PR; no ingestion/Gateway wiring. Missing: News Hub ingestion glue (News Hub component), COVERAGE_BASIS key structure, governed revision-selection rule ref/version, GOVERNED_DAY/SCOPE-to-cutoff binding, daily-class vs consumer-requirement relation. Consequence: no consumer may rely on resolver output. Decision for Sallah/Manager: name the governed revision rule (or state none exists, so ambiguity always needs explicit selection). |
| E03 context cutoff vs Gateway fence (D14) | OPEN RISK | The frozen architecture (raw DOCX 15mPi14mG5MAOerZTnhbWfWXwcOIpzWsA, sec 5) excludes equality at the fence and forbids a per-source rule from inverting it; the News Hub resolver uses <= its own cutoff. Relation cutoff<->fence is undefined (D14). Until recorded, the resolver MUST NOT feed the Gateway. Owner function: Connected Contract + News Hub owners. Recommended: record cutoff == fence for consumption so strict < applies. |
| E03 gateway/binding, non_delivery, settlement | REFERENCE_ONLY (simulated) | v038 BOTH/H1 separation, replay/rebinding tests (#36). Missing: D13 hash byte layout (Contract/Annex owner), D16 delay value. |
| E03 gateway/health_snapshot | REFERENCE_ONLY (simulated) | contracts.HealthSnapshot; real Health provider absent. |
| Status projection -> Gateway | REFERENCE_ONLY | status_projection + contracts refuse non-committed status (#36). Exact missing mapping: no StatusFact field (mv, sequence, status, available_asof, correction_marked) is a journal body field, and lifecycle kinds are not chain statuses (pinned by test_r15). Missing: status-origin principal (R7 names none) and record->StatusFact mapping. Owner function: Manager/R7 owner. Consequence: Gateway cannot consume real status. Decision: appoint (or decline to appoint) the status-origin principal; supply the kind->status mapping. |
| Lifecycle status event (Decision Context V4 A1) | REFERENCE_ONLY | lifecycle_status_event (#37). Residual fields from boundary evidence listed in docs/proposals/STATUS_EVENT_OWNERSHIP.md. Same principal decision as above. |
| E03 fw/request_adapter, input_binding | REFERENCE_ONLY | fw/receiver, lanes, descriptor_crosswalk. Mapping A04: five H3 carriers map directly (outcome/target-label series), five partial/missing/internal; all real payload bindings unbound. Owner: FW/Mapping owner. |
| E03 fw/return_lineage | REFERENCE_ONLY (structural) | fw/return_lineage (#37). Missing: FW return record payload fields. |
| E03 ml/dataset_binding, standalone_ancestry, fw_augmented_rebind, generation_lineage | REFERENCE_ONLY (structural) | ml/receiver incl. check_fw_augmented (#36, #37). Missing: ML writer/finalizer/manifest declaration (ML owner), actual manifest/lineage joins; ML 29B recertification present in source but revoked-generation revival/Gateway restore unresolved. |
| E03 health/blast_radius | REFERENCE_ONLY | blast_radius.consumer_use (#36,#37): required unknown ancestry refuses, proven-independent allowed (tests). Missing real input: no committed object carries a feature->feature dependency graph (journal bodies have manifest/graph hashes only), so feature_deps cannot be derived from real data. Owner: Feature Registry / Composer manifest owner. Plus D17/D18 Health profile home/registry. |
| E03 health b0_adapter, quant_evidence, expectation | REFERENCE_ONLY/LATER | health/envelope, evidence; Health provider (D17/D18). |
| SQE_OPSET operators (Parent/Annex V1.2) | REFERENCE_ONLY | sqe_opset (#36); not wired to manifest admission. Missing: numeric opcode table, program byte grammar, K3 instance, multi-branch CASE tie, MAX_STATE_ELEMENTS counting, class-structure compatibility. Owner: A02/SPEC. Not invented. |
| D2 principal/grant/trust anchor | OPEN (Owner appointment) | principals.GRANT_EVIDENCE_FIELDS shape only. Appoints nobody. |
| D7 certifier | OPEN (M/S) | needs certifier role/scope/interval; source names none. |
| D13 wire layouts / hash bytes | OPEN (S) | not defined in Build Plan; Contract/Annex owner. Inequality checks only. |
| D14 cutoff vs fence | OPEN (see risk row) | Gateway strict < unchanged. |
| D15 reason -> status | OPEN (M) | no list found in current Build Plan; candidate list in D_decision_package. |
| D16 SETTLEMENT_DELAY | OPEN (M/O) | visibility-only per Build Plan 11.4; value requires measured lag + Owner margin; no measurement exists. |
| D17/D18 Health profile/registry | OPEN (M/S) | A24 missing Health profiles; thresholds/flap limits/critical set unsupplied. |
| A07 / P12 / QC34 / A08 / Stage A | UNCHANGED | Manager governance gates; nothing in code can close them. |
| Provider/clock/host/grants (D10, E-01/E-06) | OPEN (Owner/Manager) | block operational qualification only, not reusable implementation. FinalResolutionStore is single-process in-memory. |

## 5. Search completeness statement
This pass re-read, from the supplied files, only the Contract V0.38 H3/ten-descriptor summary text; it did NOT re-read the full Build Plan E03/sections 11-14, Matrix, Composer 27/28, Decision Context V4 or the A04/C25 mappings after the R13/R14 reads, and did not open governance 1gzUPf4... Those clauses are carried from earlier reads. Incomplete search is not absence: any row above marked "not found" is INSUFFICIENT_EVIDENCE.

## 6. Next dependency
(1) Manager records D14 relation and the status-origin principal decision (unblocks Gateway/status wiring). (2) Feature->feature dependency graph source (unblocks real blast radius). (3) FW return payload fields and ML writer/finalizer declaration (unblocks FW/ML lineage). (4) Independent review of this PR.
