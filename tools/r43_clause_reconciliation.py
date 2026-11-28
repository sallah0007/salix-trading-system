"""R43: generates docs/closeout/TRK-STAGE-A-R43-CLAUSE-RECONCILIATION.md, the ONE current reconciliation of TR-01..15, B01-B24, D1-D18/D12', A07-1..4 into EXACTLY ONE of five statuses (Manager completeness response, Sat 2026-11-28 14:25).
SF  = SOURCE_SUPPLIED (source id + range cited, never copied; remaining instance named)
IA  = IMPLEMENTATION_ACTIONED (reachable callpath + test evidence; remaining instance/decision named)
SD  = SOURCE_DESIGN_DECISION_REQUIRED (smallest explicit options / recommendation / consequence)
OP  = OPERATIONAL_INSTANCE_OR_QUALIFICATION_REQUIRED
MR  = MANAGER_REVIEW_OR_RECORDING_REQUIRED
A status is the PRIMARY blocker of the row; the remaining column names everything else. 'Source owner' means the responsible FUNCTION, not an appointed person. Reference-only helpers are never called integrated. NOT a gate, acceptance or appointment.
Run: python tools/r43_clause_reconciliation.py > docs/closeout/TRK-STAGE-A-R43-CLAUSE-RECONCILIATION.md"""
STATUS = {"SF": "SOURCE_SUPPLIED", "IA": "IMPLEMENTATION_ACTIONED", "SD": "SOURCE_DESIGN_DECISION_REQUIRED",
          "OP": "OPERATIONAL_INSTANCE_OR_QUALIFICATION_REQUIRED", "MR": "MANAGER_REVIEW_OR_RECORDING_REQUIRED"}
# id, source (S-id + range), status, code/callpath, tests (file stems), remaining: input | FUNCTION | consequence | recommendation
ROWS = [
("B01", "S4 Reg p99; S3", "SD", "core/tracker_core.admit_observation (Core only; no pipeline caller)", "test_r24_core", "per-object wire layout of the observation | Registry/Spec function | ingestion stays unreachable from pipeline.run | supply layout (D13), then wire"),
("B02", "S4 Reg p97-101", "SF", "core/time_family; snapshot min-fields/per-TF watermark NOT built in R43", "test_r24_core", "registry/calendar instance + per-timeframe vintage watermark carrier | Registry function | watermark stays caller-supplied | build carrier on supplied fields next"),
("B03", "S4 Reg p104-124; S5", "SF", "tracker/registry_semantics.TrackerSnapshotManifest; snapshot_binding (standalone)", "test_r38_relationship_snapshot", "9 UNBOUND field instances + manifest bytes | Registry function | binding not on the separated path | supply instances"),
("B04", "S4/S3 s6", "SD", "tracker/quant_intake_adapter.admit (prototype contract)", "test_pipeline", "governed field-set typing + discriminator battery | Spec function | prototype only | options: (a) Spec supplies battery (recommended) (b) keep prototype labelled"),
("B05", "S3 s6 p6-8", "MR", "core advance_epoch/reresolve; epoch_reresolution", "test_r24_core", "Owner approval reserved for a planned irreversible downgrade | Owner | downgrade path unapproved | Manager records the reservation"),
("B06", "S4 Reg p129", "SD", "tracker/accepted_manifest; storage/byte_primitives", "test_r38_composition; test_r41_separated_caller", "D3 numeric ENUM/REF_TYPE/opcode assignments + D13 layouts | A02/Spec function | hashes are candidate | supply normative bytes"),
("B07", "S4 Reg p130-134,194-195", "IA", "composer/expression (no future-reading operator admitted)", "test_expression", "fit-manifest object instance | Composer function | fit refs only checked vs supplied generations | supply instance"),
("B08", "S4 Reg p133-136,167-170,192-199", "SD", "tracker/verification (harness shell)", "test_verifier_independence", "similarity detector definition + governed battery | Research/Registry function | detector absent | options: define metric (recommended) or keep detector HELD"),
("B09", "S4 Reg p137-165,322,377", "SD", "version_diff; relationship_store (not on the pipeline callpath)", "test_r38_relationship_snapshot", "Gateway response-package reference (p322) + Health sub-surface | Spec function | relationship store reference-only | define reference"),
("B10", "S4 Reg p234-253", "IA", "registry_gate on COMP (R40 scope-bound)", "test_r40_registry_integrity; test_r38_composition", "registry-entry bytes + survivor slot encoding | Registry function | candidate encoding | supply bytes"),
("B11", "S4 Reg p201-233,267-279", "SD", "coordination/lifecycle_framework (12 states + intake path exist)", "test_r38_lifecycle_framework", "transition edge matrix + subject->MV mapping | Spec function | edges unsourced; none invented | options: Spec supplies matrix (recommended)"),
("B12", "S4 Reg p219-222", "SD", "evidence_truth.eligible_asof; lifecycle_eligibility over the ledger", "test_r42_lifecycle_eligibility; test_r41_historical_eligibility", "ADD-4 ledger schema | ADD-4 function | ledger bytes unspecified | supply schema"),
("B13", "S4 Reg p260-287", "IA", "core quarantine/clear_reason/reactivate; lifecycle_eligibility; maintenance (R43)", "test_r43_maintenance_recovery; test_r42_lifecycle_eligibility", "subject->MV mapping | Spec function | quarantine acts on supplied subjects | supply mapping"),
("B14", "S4 Reg p203-212,254-259", "IA", "composition L2 + l2_scope; run_stored_value_pass (R43 all-segment maintenance)", "test_r38_stored_values_scope; test_r43_maintenance_recovery", "admitted scope instances; provider proof | Registry function | required scopes only | supply instances"),
("B15", "S4 Reg p367-381; S9", "SD", "health/envelope; health/expectation (payload-bound)", "test_r40_health_expectation; test_health_envelope", "per-subject/profile/threshold assertions (D17/D18) | Health function | EXPECTATION unadmitted | supply profile home"),
("B16", "S4 Reg p382-408", "SD", "health/blast_radius; subject_coverage", "test_r12_blast_radius", "rule for UNDETERMINED non-required consumer | Spec function | fails closed | decide"),
("B17", "S10 (located)", "MR", "replay.py (invoked)", "test_foundations", "release-identity coupling object in the Blueprint body | Manager review of S10 | coupling unaudited | review body"),
("B18", "S4 Reg p394-399; S3 s4/s21", "OP", "core plane identity; restore via lifecycle_eligibility; planes/read-model rebuild on the separated path NOT built in R43", "test_r24_core; test_r43_maintenance_recovery", "provider qualification for restore/split-brain | Platform function | SQLite/flock are not provider proof | qualify provider"),
("B19", "S4 Reg p185-188", "OP", "evidence_resolver; evidence_truth (receipt API)", "test_r34_health_subjects", "admitted evidence store + restricted writer | Registry/provider | not authority-transition integration | qualify"),
("B20", "S4 Reg p173-180", "OP", "research_lineage; news_hub_v2.resolve_context", "test_r38_composition", "governed battery definitions/currentness/revocation | Research function | counts are not authority | supply instance"),
("B21", "S4 Reg p301-323; S6", "IA", "SimulatedGateway; durable_final_store; e05 owning sources; separated caller FW+ML (R41-R43)", "test_r42_consumer_path; test_r42_e05_owning_sources; test_r43_ml_integration", "real provider + response-package reference | Platform function | simulation only | qualify provider"),
("B22", "S4 Reg p353-366", "MR", "core accept_finding", "test_r24_core", "principal admission (D2) | Owner | no appointment | Owner appoints"),
("B23", "S4 Reg p431-433,469,481-482; S9 MLHealth", "IA", "ml/consumer_path (R43): dataset manifest->generation/union/request->reverse-H1, six joins, writer/finalizer; qualified always False", "test_r43_ml_integration; test_r42_consumer_path", "grants/principals; era/ledger instances | ML function | rows unqualified | supply instances"),
("B24", "S10", "MR", "-", "-", "LOCATED / BODY REVIEW PENDING (Blueprint 1xf9Lv0q) | Manager | row unauditable until read | review body"),
("D1", "S6", "MR", "tracker/construction_binding (qualified resolver ALWAYS False); callsite = claims authorizes()", "test_r22_construction_binding", "install point + principal/source admission | Manager | not installed | Manager records"),
("D2", "-", "MR", "principals.GRANT_EVIDENCE_FIELDS (shape only)", "-", "appointment | Owner | nobody appointed | Owner appoints"),
("D3", "S2 s6.2/6.3; S5 SQE_OPSET_V1_1; Annex I", "SD", "schema/candidate_code_tables (candidates)", "-", "numeric ENUM/REF_TYPE/opcode assignments + program grammar (formats ARE supplied) | A02/Spec function | all assignments candidate | supply tables"),
("D4", "-", "MR", "verification/independent_* (same author)", "test_verifier_independence", "independent oracle re-derivation | Manager/Codex | independence limited | Codex re-derives"),
("D5", "S6", "OP", "tests/provider_conformance (tooling)", "-", "provider qualification | provider | SQLite/in-memory/flock are not provider proof | qualify"),
("D6", "S7", "SD", "docs/proposals/D6_composer_s27_mapping.md", "-", "prose-only s27 fields (re-read of S7 27/28 + 7-field admission NOT completed in R43) | Composer function | not enforced | answer fields"),
("D7", "-", "MR", "-", "-", "certified-ABSENT certifier role/scope/interval | Manager | none | name function"),
("D8", "S3/S4 manifest", "SF", "explicit flag used today; derive routing from the exact admitted manifest not yet coded", "-", "code derivation from admitted manifest | Coder | explicit flag stays | implement next"),
("D9", "-", "MR", "dependency-direction test (delta noted in closeout)", "test_dependency_direction", "Manager mapping stage_a -> tracker_component | Manager | exists unrecorded | record"),
("D10", "S2 R3 E01-H1 p1021-1026; E01-M1", "OP", "ONE owning journal/HEAD (ObjectStoreJournal); no cross-head atomicity claimed; unknown-commit/CAS recovery tested; separated processes are NOT single process", "test_r41_separated_caller; test_r43_maintenance_recovery", "provider qualification of the object store (flock/SQLite/in-memory are TEST adapters) | provider | not provider proof | qualify"),
("D11", "S2/S6", "SF", "PACKAGE_CLASS FW_PACKAGE|ML_PACKAGE|NEUTRAL_GOVERNED_PACKAGE", "test_r42_consumer_path", "lane-name instances | Spec function | prototype labels | map"),
("D12", "source text", "SF", "code follows", "-", "- (not a gate clearance)"),
("D12'", "-", "SD", "unknown reasons REJECTED", "-", "new-request trigger | Spec function | fails closed | define trigger"),
("D13", "-", "SD", "labelled candidate hashes", "test_r35_durable_final_store", "per-object wire layouts FINAL_RESOLUTION/PACKAGE/Event/Context | Spec function | durable record encoding CANDIDATE | supply layouts"),
("D14", "S8", "SF", "strict half-open boundary retained, two-stage validation (news_hub_v2)", "test_r14_event_causality", "- (decision text supplied)"),
("D15", "S6", "IA", "stage_a/gateway/v038.py:14-19 category rules", "test_r42_consumer_path", "reason->status extension | Manager | unknown reasons REJECTED | decide on extension"),
("D16", "S6", "OP", "SETTLEMENT_DELAY defined, no value", "-", "measured value | Manager/Owner | none | measure"),
("D17", "S9", "SD", "-", "-", "News profile home | Manager | proposed only | decide"),
("D18", "S9", "SD", "-", "-", "Health thresholds/registry | Health function | unsupplied | supply"),
("A07-1", "A07 ZIP 6e599c5d / extract fd594244 (recomputed match)", "MR", "tools/a07_r43_oracle_association.py; docs/a07 R42/R43 readings; V230/V232/V235 oracles withhold acceptance", "-", "ML source owner adjudication of the 21 disagreement qualifiers + 12 loss-listed QUALIFIERS (3 units: NL0087, NL0180, NL0184; NL0178 at wider scope) | Manager | hash parity is not semantics | adjudicate"),
("A07-2", "R06 candidate 1V5bv2Qr (fetch empty, not absence)", "MR", "docs/a07 R04/R06", "-", "R06 V03 reconciliation | Manager | open | reconcile"),
("A07-3", "-", "OP", "-", "-", "Drive Activity export not obtained | Drive admin | external | supply"),
("A07-4", "-", "MR", "-", "-", "QC34 ALERT(HOLD) | Manager | open | decide"),
("TR-01", "S2 s27", "SD", "composer/expression", "test_expression", "D3 normative bytes | A02/Spec function | candidate | supply"),
("TR-02", "S2 s27", "MR", "quant_intake_adapter + tracker_component", "test_pipeline", "D1/D2 | Manager/Owner | held | record"),
("TR-03", "S2 s27", "SD", "composer/expression/canonical_encoding", "test_r38_tr_dod", "D3/D13 | Spec | candidate | supply"),
("TR-04", "S2 s27", "SD", "accepted_manifest; expression/manifest", "test_r38_tr_dod", "frozen QuantManifest normative bytes | Spec | prototype | supply"),
("TR-05", "S2 s27; S7", "MR", "composer/request_record; build_output_check", "test_r29_intake_order", "Composer producer (LATER); package/report + 7-field admission upstream not re-read in R43 | Manager | unaudited | review"),
("TR-06", "S2 s27; Manager input", "SF", "request_classification; SimulatedGateway (explicit flag)", "test_r38_tr_dod", "derive routing from exact manifest | Coder | explicit flag stays | implement"),
("TR-07", "S2 s27; S6", "IA", "gateway/*; fw/receiver; ml/receiver; separated caller", "test_r42_consumer_path; test_r43_ml_integration", "real Gateway/status principal | Owner | held | appoint"),
("TR-08", "S2 s27; S9", "SD", "health/*", "test_health_envelope", "D17/D18 | Health | unsupplied | supply"),
("TR-09", "S5", "MR", "verification/stateful_verifier; quant_certification", "test_verifier_independence", "Parent V1.2 s3 independence | Manager | open | review"),
("TR-10", "S2 s27", "SF", "currentness; context; time_family; lifecycle_eligibility; absent filename gateway/dependency_resolution.py is already MAPPED, not missing authority", "test_r42_lifecycle_eligibility", "- (mapping recorded)"),
("TR-11", "S2 s27", "OP", "coordination/*; storage/e05_*; ops/separated_*", "test_r41_separated_caller; test_r42_e05_owning_sources", "D1; provider (D5/D10) | provider | simulation | qualify"),
("TR-12", "S2 s27; S8", "IA", "context/event_context_store (R43) on a supplied encoding interface; e05 source HELD without it", "test_r43_event_context_store", "encoding interface + D13 layouts | Spec function | HELD without interface | supply"),
("TR-13", "S2 s27; S6", "IA", "fw/* after separated acceptance", "test_r42_consumer_path", "H1/H3 field instances; CBID issuer | Spec function | simulation | supply"),
("TR-14", "S2 s27; S9", "IA", "ml/consumer_path (R43)", "test_r43_ml_integration", "grants/principals | Owner | unqualified | appoint"),
("TR-15", "S2 s27", "IA", "identifiers; storage/keys", "test_registration_atomicity", "no cross-instrument consumer exists | Spec | none | confirm LATER"),
]
CROSS = [
("BEFORE (upstream feeding the Tracker)", "Composer V9 (S7) 27/28 + 7-field admission, Frozen Parent/Annex (S5), Registry (S4), BuildPlan 11-14/14A/27/29A (S2), Contract H1/H3 (S6): consumed only as already-read candidates; R43 did NOT re-read them end to end (named per row)."),
("AFTER (downstream consumers)", "ML consumer path (R43), FW consumer (R42), Gateway/Health (S6/S9) consume Tracker outputs; every ML row is qualified=False; no Engine/Stage B/live/AI-body work."),
("Handoffs", "Tracker->Gateway (separated acceptance, R41), Tracker->ML (reverse-H1 link, R43), Core->Health (gateway_health), Registry->Core (scope resolver). Each is SIMULATION only."),
]
def main():
    print("# TRK Stage A: R43 clause reconciliation (TR-01..15, B01-B24, D1-D18/D12', A07-1..4)\n")
    print("Generated by `tools/r43_clause_reconciliation.py`. Supersedes the R42 clause status as the CURRENT view (R42 kept for history). NOT a gate, acceptance or appointment; a merge, CI run or test clears nothing. DERIVATION_CLASS: AUTHOR-RUN/REPORTED; sources cited by S-id and range, never copied. 'Source owner' = responsible FUNCTION, not an appointed person. Statuses: " + "; ".join("%s=%s" % kv for kv in STATUS.items()) + ".\n")
    counts = {}
    for r in ROWS: counts[r[2]] = counts.get(r[2], 0) + 1
    print("Counts: " + ", ".join("%s=%d" % (STATUS[k], counts.get(k, 0)) for k in STATUS) + ".\n")
    print("| Row | Source (cite only) | Status | Code / callpath | Tests (file stems) | Remaining: input / FUNCTION / consequence / recommendation |\n|---|---|---|---|---|---|")
    for r in ROWS: print("| %s | %s | %s | %s | %s | %s |" % (r[0], r[1], STATUS[r[2]], r[3], r[4], r[5]))
    print("\n## Dependencies and handoffs\n")
    for k, v in CROSS: print("- **%s**: %s" % (k, v))
    print("\nFull Tracker is NOT complete. Held: A02 Class B HOLD; A07/COVERAGE OPEN; A07/P12/N2 UNSATISFIED; QC34 ALERT(HOLD); A08 READY_TO_CODE NO; Stage A HOLD.")
if __name__ == "__main__": main()
