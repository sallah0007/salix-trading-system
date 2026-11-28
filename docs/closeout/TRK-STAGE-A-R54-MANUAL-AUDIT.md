# R54 MANUAL source audit (62 rows; every row has a verdict; NOT a gate; nothing adopted)

SRC=Y means the governing source passage was re-read from the live document in the R54 resume; SRC=N means code-side audit only and the source-side reading stays the recorded one (INSUFFICIENT_EVIDENCE for anything new). Evidence columns are counted from the cited test files (negative-control count = assertRaises/refusal-code assertions, an upper bound on meaningful negatives). Rows marked MR carry the precise review question.

| Row | Status | SRC re-read | Audit (verified this pass) | Tests (pos/neg) | Remaining | Review question |
|---|---|---|---|---|---|---|
| B01 | SD | N (S4 p99 recorded) | Core.admit_observation exists with nine NAMED candidate facts, available_asof, vintage; no pipeline caller; R54 ObservationSnapshotAdapter consumes recorded observations (test_r54_observation_snapshot, 8-mutant sweep) | 64/74 | payload/fact byte encoding, DATA_VINTAGE_MODE values, required-vs-optional facts (R54_DECISION_PACK s2); ingestion caller needs a provider | - |
| B02 | IA | N | per-timeframe vintage/watermark from sealed Core records; watermark slot HELD when unbound; mixed-vintage default-deny (R44/R54) | 68/83 | watermark source = source-owned slot | - |
| B03 | IA | N | TrackerSnapshotManifest + snapshot_carrier candidate hash (authoritative=False) | 15/35 | seven held manifest field instances + byte layout | - |
| B04 | SD | N | admit() prototype contract; battery fixtures exist as tests; no source battery content | 44/20 | approve battery content (Spec function) | - |
| B05 | MR | N | advance_epoch/reresolve present; planned irreversible downgrade path unapproved by design (S4 s10 re-read: 'Planned irreversible reconstructability downgrade remains Owner-authority') | 64/74 | Owner reservation record | Does the Owner's reservation of planned irreversible downgrade need a recorded approval object, or is the absence of any downgrade path the intended state? |
| B06 | SD | N | accepted_manifest candidate bytes | 20/28 | D3/D13 normative bytes | - |
| B07 | IA | N | expression operators exercised by parity tests R45-R47; invoked through intake/verification | 56/67 | program grammar + opcode codes + ceilings | - |
| B08 | SD | N | harness shell only; detector absent | 17/8 | similarity detector decision (R54_DECISION_PACK) | - |
| B09 | SD | N | version_diff/relationship_store/version_relationship are NOT called by intake or the report producer (CANONICAL_SURVIVOR and FEATURE_VERSION_RELATIONSHIP_REF always null; s28 comparison) | 11/26 | Gateway response-package reference (p322), Health sub-surface, survivor/relationship producer | - |
| B10 | IA | N | registry_gate on COMP scope-bound (R40) | 25/32 | registry-entry bytes + survivor slot encoding | - |
| B11 | SD | Y S4 s8 workflow + s10 states re-read (live document) | lifecycle framework applies a SUPPLIED policy via the lifecycle= parameter; twelve states in registry_semantics; source says the list INCLUDES them 'as applicable' and names DISCARDED as a terminal resolution in the Builder path; terminal_identity reports the stored state string | 22/36 | allowed-edge list; DISCARDED status (R54_DECISION_PACK s4) | Registry function: is DISCARDED a thirteenth state, an alias or a resolution label? |
| B12 | SD | N | evidence_truth.eligible_asof, lifecycle_eligibility never rewrites history | 18/23 | ADD-4 ledger schema | - |
| B13 | IA | Y S4 s10 re-read: multiple simultaneous quarantine reasons, clearing one does not clear all, reactivation = all blockers resolved AND current reconstructability | Core quarantine/clear_reason/reactivate match those three rules; restart + restoration cycle exercised on the shared assembly (test_r53_real_assembly_base) | 12/21 | subject->MV mapping | - |
| B14 | IA | N | composition L2 + all-segment maintenance on both consumers (R52/R53) | 33/50 | none generic | - |
| B15 | SD | N | health envelope/expectation payload-bound | 10/12 | D17/D18 thresholds/profile registry | - |
| B16 | SD | N | blast_radius.consumer_use refuses undetermined+required; non-required unknown only named | 29/12 | rule for non-required undetermined (Spec function) | - |
| B17 | MR | N (Blueprint prefix only; Manager evidence) | replay.py invoked; release-identity coupling object not recovered | 34/48 | the coupling wire object | Codex/Manager: which Blueprint section after Appendix A or S3 s18 defines the release-identity coupling object? A bounded read of that span, not the whole Blueprint, answers it. |
| B18 | OP | N | four source-named planes enforced across restart; E05 rebuild on the shared assembly (R54 test_r54_shared_rebuild) | 68/86 | provider qualification (SQLite/in-memory are test adapters) | - |
| B19 | OP | N | evidence_resolver/evidence_truth receipt API exercised by tests; no restricted writer | 4/4 | admitted store + writer instance (provider) | - |
| B20 | OP | N | research_lineage; news_hub_v2.resolve_context; counts are not authority | 17/26 | governed battery definitions/currentness/revocation | - |
| B21 | IA | Y S6 final resolution identity (4 fields) + structured missing-dependency evidence re-read | FinalResolutionIdentity has the four source fields; NonDeliveryResolutionV038 carries StructuredOmission and NOT_READY requires omissions; retry returns the stored outcome; E05 rebuild + cold restart exercised | 28/67 | identity byte encoding (D13), H1/H3 instances, real Gateway counterpart | - |
| B22 | MR | N | accept_finding records only 4 named fields; authorizes nothing | 64/74 | principal admission D2 | Owner: which identities may submit findings? |
| B23 | IA | N (callsite analysis in R54_ROW_AUDIT) | ml/consumer_path exercised over the real Composition Gateway in tests only; no owning caller | 48/99 | ML-owned instances (schedule, event id, reverse-H1, grants) | - |
| B24 | MR | N (Blueprint prefix only) | no code claim | 0/0 | bounded prefix reviewed by Manager | Manager: confirm no further Blueprint obligation outside the prefix for the Tracker (Appendix A and AI spans unread). |
| D1 | MR | N | construction_binding qualified resolver always False; callsite authorizes() | 50/63 | principal/grant appointment | Owner/Manager: which principal class may issue and which may certify construction authority, and is the replica role pair in R7 s1-6 the intended authority split? |
| D2 | MR | N | GRANT_EVIDENCE_FIELDS shape only; replica role names only | 7/2 | Owner appointment | Owner: name the principals for acceptance-origin and replica-commit-service? |
| D3 | SD | N (S2/S5 recorded; not re-opened) | candidate_code_tables has no caller (tests only) by design; lazy select vs RPN reconciled in the pack | 0/0 | numeric code assignments/program grammar (R54_DECISION_PACK s1) | - |
| D4 | MR | N | verification/independent_* share an author (Claude); staffing = Claude authors / Codex reviews | 17/8 | independent oracle re-derivation | Codex: re-derive A02 arithmetic oracle and first case independently; supply the K3 instance. |
| D5 | OP | N | provider conformance tooling only | 0/0 | provider qualification | - |
| D6 | SD | Y Composer s27 (33 groups) and s28 (23 entries) re-read | see TRK-STAGE-A-R54-S27-S28-COMPARISON.md; 3 generic report gaps fixed with tests failing on the unfixed adapter | 46/20 | applicability predicate, keys for 11 keyless groups, closure record consumption, zero admitted bindings | - |
| D7 | MR | N | no code | 0/0 | certified-ABSENT certifier role/scope/interval | Manager: which function certifies ABSENT lookups and over what interval? |
| D8 | SD | N | route_from_adapter maps QUANT/NO_QUANT; DIRECT_TRACKER_FEATURE has no producer; FAILED_BUILD_NOT_ROUTABLE refusal verified in code | 0/0 | DIRECT_TRACKER_FEATURE selector | - |
| D9 | MR | N | dependency-direction test | 3/0 | Manager mapping stage_a -> tracker_component | Manager: record the mapping or confirm the delta stays code-side. |
| D10 | OP | N | status emitter and lifecycle apply are parameter-supplied callers; shadow publisher has NO caller (R54 withdrawal) | 29/54 | provider/time primitive; governed shadow caller | - |
| D11 | SF | N | PACKAGE_CLASS labels | 2/5 | lane-name instances | - |
| D12 | SF | N | code follows source text | 0/0 | - | - |
| D12' | SD | N | unknown reasons REJECTED | 0/0 | new-request trigger | - |
| D13 | SD | N | candidate JSON codecs; per-object gaps table (R54_DECISION_PACK s2) | 8/15 | byte layouts per object incl. observation | - |
| D14 | IA | Y S6 re-read: strict AVAILABLE_ASOF < fence; settlement never widens it | half-open fence only Gateway/Tracker rule (test_r44_d14_boundary); check_settlement refuses delay below certified lag and does not widen eligibility (verified in v038.py) | 31/23 | none for the strict rule | - |
| D15 | IA | N | v038 category rules; unknown REJECTED | 2/5 | closed reason list | - |
| D16 | OP | Y S6 SETTLEMENT_DELAY passages located | check_settlement takes delay and certified lag as arguments; no default value in the tree (grep: only contracts.py/v038.py references) | 0/0 | measured value and certification (Manager/Owner) | - |
| D17 | SD | N | no code | 0/0 | News profile home | - |
| D18 | SD | N | no code | 0/0 | Health thresholds/registry | - |
| A07-1 | MR | N (ML source owner readings) | R47 reconciliation tool + CSV; all 100 UR | 3/0 | per-qualifier semantic adjudication | ML source owner: confirm or reject each of the 12 loss and 21 disagreement readings. |
| A07-2 | MR | N | R06 candidate V240 record; V03 staffing reconciliation | 0/0 | Manager reconciliation | Manager: does V03 reconcile with Claude-authors/Codex-reviews without a third actor? |
| A07-3 | OP | N | no code; external | 0/0 | Drive Activity export | - |
| A07-4 | MR | N | no code | 0/0 | QC34 decision | Manager: decide QC34 ALERT(HOLD). |
| TR-01 | SD | N | operators per B07 | 35/30 | D3 bytes | - |
| TR-02 | MR | N | single registry/lifecycle path asserted; baseline connection held in qualified mode (unresolved_mandatory) | 44/20 | D1/D2 record | Manager/Owner: record the single-path decision. |
| TR-03 | SD | N | canonical_encoding candidate | 6/12 | D3/D13 | - |
| TR-04 | SD | N | accepted_manifest/manifest candidate bytes | 6/12 | normative QuantManifest bytes | - |
| TR-05 | MR | Y Composer s27/s28 re-read | s27 33-group comparison and s28 23-entry comparison done; check_build_output/check_conformance wired; producer bindings zero | 13/17 | producer binding admissions; applicability predicate | Codex: confirm the group classification (TOKEN/MANIFEST/PROSE) in TRK-STAGE-A-R54-S27-S28-COMPARISON.md against s27 and the applicability handling (report-not-refuse). |
| TR-06 | SF | N | FAILED_BUILD_NOT_ROUTABLE refusal verified; explicit simulated flag | 6/12 | none | - |
| TR-07 | IA | N | gateway/fw/ml receivers on the real assembly; counterparts none | 8/15 | real Gateway/status principal | - |
| TR-08 | SD | N | health/* generic | 5/7 | D17/D18 | - |
| TR-09 | MR | N | stateful_verifier/quant_certification same author | 17/8 | independence | Codex: does independent re-derivation of the verifier by Codex satisfy Parent V1.2 s3, or is a different mechanism required? |
| TR-10 | SF | N | currentness/context/time_family/lifecycle_eligibility; gateway/dependency_resolution mapped to contracts | 10/17 | - | - |
| TR-11 | OP | N | coordination/* and e05 simulated; provider unqualified | 13/19 | provider | - |
| TR-12 | IA | N (callsite analysis) | context/event_context_store tests only; encoding ports caller-supplied | 10/24 | D13 layouts + consumer requirement class relation | - |
| TR-13 | IA | N | typed H1 + OutcomeSeriesDesk via Composition.outcome_desk (R54), fw association via Composition.fw_association | 19/57 | H1/H3 instances; CBID issuer | - |
| TR-14 | IA | N (callsite analysis) | ML shadow/augmented tests only | 46/94 | ML-owned instances | - |
| TR-15 | IA | N | identifiers/keys | 11/0 | confirm LATER | - |
