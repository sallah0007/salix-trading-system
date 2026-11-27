# E-03 responsibility -> existing file/function map (R11)

Status: PROPOSAL / reviewer judgment (Coder). A proposed mapping delta, not a governed decision. Nothing is renamed; current candidate paths are retained.
DERIVATION_CLASS = INDEPENDENTLY_DERIVED for the counts; the classification column is reviewer judgment from reading function names and docstrings, not an equivalence proof.
EXACT_INPUTS = Build Plan "E-03 FINAL REPOSITORY MODULE MAP" (57 paths, text lines 4522-4720 of the Drive read) vs `git ls-files 'stage_a/**.py'` (non-`__init__`) at the R11 branch head.
METHOD = parse the E-03 tree; set-compare to repo paths. Result: 57 map paths, 32 exist, 25 map-only, 29 repo-only. REPRODUCIBLE_BY_MANAGER = YES.
A missing filename is not a missing behaviour. Classes: EQ = behaviour exists under another path; MISSING = Tracker-owned behaviour genuinely absent; LATER = counterpart (Composer/FW/ML/Health-provider) work, not Tracker-owned; INT = internal helper placed elsewhere on purpose.

| E-03 path (absent) | Responsibility | Where it lives now | Class |
|---|---|---|---|
| composer/governed_order_adapter.py | Composer-side order adapter | none; Tracker is sole order issuer (journal-verified claim in `tracker/authority_bridge.py`) | LATER (Composer side) |
| composer/build_executor.py, refit_executor.py, build_output.py | Composer build/refit execution and output package | none; Tracker consumes `BuildPackage` in `tracker/quant_intake_adapter.py` | LATER (Composer side) |
| context/event_identity.py | event identity | `context/decision_context.py` (`check_envelope`, `domain_for_event`) | EQ (partial; identity key derivation not verified) |
| context/coverage.py, applicability.py | coverage / applicability dimensions | `context/news_hub_v2.py` (`check_dimensions`) | EQ (partial) |
| context/resolver.py | context resolution | none found | MISSING (only to the extent a source defines it; not invented) |
| context/causal_gate.py | as-of visibility | `decision_context.as_of_visible`, `news_hub_v2.actual_available_asof` | EQ |
| gateway/dependency_resolution.py | dependency resolution | `gateway/contracts.py` (`DependencyEntry`, `SimulatedGateway`) | EQ but SIMULATED, not REAL |
| gateway/binding.py | consumer binding (H1) | `gateway/v038.py` (`check_h1`, now `check_both_separation`), `contracts.Binding` | EQ (field-presence only; hash bytes D13) |
| gateway/non_delivery.py | non-delivery resolution | `v038.NonDeliveryResolutionV038`, `to_v038`, `FinalResolutionStore` | EQ |
| gateway/settlement.py | settlement | `v038.check_settlement`, `classify_late` | EQ (delay value D16 open) |
| gateway/health_snapshot.py | health snapshot | `contracts.HealthSnapshot` | EQ (simulated) |
| fw/request_adapter.py, input_binding.py, return_lineage.py | FW request, input binding, return lineage | `fw/receiver.py` (`receive`), `fw/lanes.py`, `fw/descriptor_crosswalk.py` | EQ partial; return lineage not found -> MISSING until FW payload definitions (group 2) |
| ml/dataset_binding.py, standalone_ancestry.py, fw_augmented_rebind.py, generation_lineage.py | ML dataset/ancestry/rebind/lineage | `ml/receiver.py` (`build_row`, `check_generation`, `AugmentedInput`) | EQ partial; ML manifest writer declaration open (group 2) |
| health/b0_adapter.py, quant_evidence.py, blast_radius.py, expectation.py | Health adapter, evidence, blast radius, expectation | `health/envelope.py` (`derive_silence`, `aggregate_state`, `attribute_failure`), `health/evidence.py` | EQ partial; blast-radius computation not found -> MISSING (Health profile home D17/D18 open) |

Repo-only paths (29) include the R7/R9/R10 additions (`security/principals.py`, `coordination/provider_contract.py`, `binding/producer_binding.py`, `composer/request_record.py`), the identity-adjacent Tracker files (`tracker/pipeline.py`, `registry.py`, `chain_status.py`, `epoch_reresolution.py`, `speculation.py`, `stateful_*`, `independent_*`) and `schema/*`. Placement of these is an INT/mapping-delta question for the Manager; none is claimed as governed.

Proposed mapping delta (for Manager recording in Drive): add the repo-only Tracker files above under their current paths; mark the Composer-side rows LATER; mark `context/resolver.py`, FW return lineage, ML-side lineage declarations and Health blast radius as the only rows with possibly absent Tracker-owned behaviour, each blocked on a named source (see A02_trace_and_inputs.md groups 2-3). Not implemented: building them now would invent field definitions.

## R12 update (after Manager review of PR #35)
- health/blast_radius.py: IMPLEMENTED at `stage_a/health/blast_radius.py` (structural traversal over supplied lineage; closure probe injected because Health may not import FW/ML). Verdicts AFFECTED_PROVEN_DEPENDENCY / NOT_AFFECTED_NO_PROVEN_DEPENDENCY / UNDETERMINED_LINEAGE_UNREAD. Missing semantic rule: the ACTION for an UNDETERMINED consumer (block/deliver/review). Profile thresholds are not used.
- ml/fw_augmented_rebind.py + generation_lineage.py: structural part IMPLEMENTED as `ml/receiver.check_fw_augmented` (declared FW parent, Gateway rebind present, no hidden quant ancestor). Missing: FW return/lineage PAYLOAD field definitions (Composer section 27 / FW-ML payload definitions, group 2) and the rule that "preserves FW generation identity, uncertainty/OOD/support, dependency interval, research exposure" beyond ref presence.
- fw/return_lineage.py: NOT implemented as a module; the Build Plan names the rule (FW-derived predictive input returns via governed lineage then Gateway rebind) but no source read defines the FW return record fields. Exact blocker: FW return record field list.
- context/resolver.py: NOT implemented. Exact missing semantic rule: the resolver's input and output contract (which context facts are resolved, for which key, with which fail-closed outputs). The Build Plan lists the filename only; News Hub V2 checks (`context/news_hub_v2.py`) and decision-context checks exist but do not define a resolver.
- Status projection: `tracker/status_projection.py` (committed-journal replay; see STATUS_EVENT_OWNERSHIP.md R12 note).

## R13 update (recovered sources)
- context/resolver.py: market Event/Context resolver now implemented in `context/news_hub_v2.py` (`check_event_record` 9.0, `check_daily_record` 9.2A, `resolve_context`, `event_consumable`) from News Hub V2 (Drive 1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw). It is distinct from governance Decision Context. Remaining exact bindings: COVERAGE_BASIS component key names (source defines the components, not keys); the IO glue that supplies records from ingestion (News Hub component, not in this repo); prose-only EVENT_RECORD entries have no key names. Revision tie (`MULTIPLE_CANDIDATES`) comes from the native Tracker reference (navigation only until compared with the frozen DOCX 15mPi14mG5MAOerZTnhbWfWXwcOIpzWsA).
- composer/build_output.py: the Tracker-side check of a supplied BUILD_OUTPUT_PACKAGE is `tracker/build_output_check.py` (Composer V9 s27/s28); the Composer-side producer stays LATER.
- fw/return_lineage.py: `fw/return_lineage.py` (return classes Evidence/Request/Lineage; FW-derived predictive input needs lineage+rebind). Payload fields remain undefined (mapping A04 bindings null).
- ml/fw_augmented_rebind.py: `AugmentedInput` now also requires FW generation identity and research exposure refs (Build Plan 13.2).
- health/blast_radius.py: `consumer_use` applies 13.1/14A/OB2 (undetermined + required -> refuse; proven independent -> allow; undetermined + non-required: no source rule, named).

## R14 update (PROPOSAL; Codex-reproduced causal-time gap, withdrawn R13 claim)
`context/news_hub_v2.py`: `event_consumable` now gates on every stamp (REVISION_AVAILABLE_AT, PUBLICLY_AVAILABLE_AT, SALIX_RECEIVED_AT, AVAILABLE_ASOF, ACTUAL_AVAILABLE_ASOF, per-value CONSENSUS/PREVIOUS stamps) and validates the record itself; `resolve_context` validates the daily record via `check_daily_record`. Malformed/missing stamps and cutoff raise. Revision selection requires a caller-supplied governed rule (only `HIGHEST_REVISION_SEQ` implemented); default is MULTIPLE_CANDIDATES.
Named gaps (not invented): governed revision-selection rule ref/version; GOVERNED_DAY/GOVERNED_SCOPE-to-cutoff binding; SCHEDULE_VINTAGE availability evidence; relation of CONTEXT_REQUIREMENT_CLASS in a daily record to the consumer's requirement; SUPERSEDES_REF value format; formula for general AVAILABLE_ASOF (only the derived fail-closed floor max(PUBLIC, RECEIPT) is applied, labelled DERIVATION).
