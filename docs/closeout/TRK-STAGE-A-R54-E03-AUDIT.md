# R54 E-03 module-map audit (57 paths; NOT a gate; nothing adopted)

DERIVATION_CLASS = INDEPENDENTLY_DERIVED. EXACT_INPUTS = Build Plan 1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo, section 'E-03 FINAL REPOSITORY MODULE MAP' (re-read live; the tree lists 57 .py paths) and the current tree. METHOD = compare each path with `stage_a/<path>`; absent paths are mapped by hand to the symbols that implement the responsibility, and this generator FAILS if a named symbol is missing. Filename equality is not closure: 'exists' rows show the module's own first docstring line only; whether the content discharges the E-03 responsibility is the Coder reading in the last column of the manual audit (TRK-STAGE-A-R54-MANUAL-AUDIT.md).

Result: 36 exist, 21 absent (R11 had 32/25). Every absent path has a verified mapping or a LATER/counterpart class.

| E-03 path | State | Where the responsibility lives (verified symbols) / first docstring line | Class |
|---|---|---|---|
| authority.py | EXISTS | Authority is a reference to an accepted journal transition, never a caller assertion. | FILE |
| identifiers.py | EXISTS | Instrument/timeframe-scoped identifiers (TR-15). Equal feature id/version in different | FILE |
| errors.py | EXISTS | Fail-closed error types. A Refusal is a normal, typed negative outcome; it never means 'try again unqualified'. | FILE |
| clocks.py | EXISTS | Identity timestamps and causal/finalisation timestamps are different things and are typed apart. | FILE |
| currentness.py | EXISTS | AVAILABLE_ASOF resolution. Two query modes that must never be confused (Q21-Q23): | FILE |
| replay.py | EXISTS | Deterministic replay of a feature-namespace journal into lifecycle state. The journal is the only authority; | FILE |
| observability.py | EXISTS | Evidence/log sink. Emitting an event never creates authority, Health state or delivery. | FILE |
| composer/request_classification.py | EXISTS | Request classification routing at the Tracker<->Composer boundary (Build Plan 3.1; home stage_a/composer/request_classification.py). | FILE |
| composer/governed_order_adapter.py | ABSENT | tracker/authority_bridge.py - Composer-side order adapter; the Tracker is sole order issuer | LATER |
| composer/build_executor.py | ABSENT | none (counterpart) - Composer build execution is counterpart work; Tracker consumes BuildPackage in quant_intake_adapter | LATER |
| composer/refit_executor.py | ABSENT | none (counterpart) - Composer refit execution; fit generations are consumed via expression/fit_generation + check_fit_refs | LATER |
| composer/build_output.py | ABSENT | tracker/build_output_check.py::check_build_output; tracker/build_output_check.py::section27_status - Tracker-side check/report of a SUPPLIED package (producer LATER); s27 33 groups / s28 compared in TRK-STAGE-A-R54-S27-S28-COMPARISON.md | EQ |
| composer/expression/manifest.py | EXISTS | (no docstring) | FILE |
| composer/expression/schema.py | EXISTS | Manifest schema SALIX_EXPR_MANIFEST_V1 (implementation-defined; source admission OPEN). Strict: exact field | FILE |
| composer/expression/canonical_encoding.py | EXISTS | Canonical bytes for a validated manifest. Keyed canonical ordering: object keys sorted, nodes by id, inputs and | FILE |
| composer/expression/hashing.py | EXISTS | (no docstring) | FILE |
| composer/expression/opcodes.py | EXISTS | Admitted opcode table. ALIGNED (R11) to SQE_OPSET_V1_1 (Parent V1.2 Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM lines 116-204; | FILE |
| composer/expression/capability.py | EXISTS | Operator-set and capability extraction (TR-09). Declared == extracted, both ways; provider must support all. | FILE |
| composer/expression/evaluator.py | EXISTS | Generic evaluator. No branch depends on feature id/version/model name (TR-01; enforced by a static test). | FILE |
| composer/expression/fit_generation.py | EXISTS | Immutable fit-generation references (Q9/Q10 boundary; no fitting happens here). A reference names a generation and | FILE |
| composer/expression/artifacts.py | EXISTS | (no docstring) | FILE |
| tracker/quant_intake_adapter.py | EXISTS | Tracker quant intake: SAFE INTAKE -> ADMISSIBILITY -> FEATURE IDENTIFICATION -> CLASSIFICATION. | FILE |
| tracker/quant_certification.py | EXISTS | Component-side certification: checks the producer-side kernel itself can make. It is NOT independent evidence; | FILE |
| tracker/publication.py | EXISTS | PUBLISHABLE / WITHDRAWN status transitions. Publication status is eligibility evidence only: nothing here calls, | FILE |
| tracker/materialization/stateful_materializer.py | EXISTS | Stateful materializer: stores the content-addressed artifact and records what it computed on the verifier-authored | FILE |
| tracker/verification/stateful_verifier.py | EXISTS | Independent verification of a materialization record against the bytes actually stored. | FILE |
| tracker/verification/verification_result.py | EXISTS | Typed, scope-qualified verification result. A reader that ignores the scope fails closed: the result has no | FILE |
| context/event_identity.py | ABSENT | context/decision_context.py::check_envelope; context/decision_context.py::domain_for_event - event identity key derivation not source-defined beyond the envelope | EQ-partial |
| context/coverage.py | ABSENT | context/news_hub_v2.py::check_dimensions - coverage dimensions | EQ |
| context/applicability.py | ABSENT | context/news_hub_v2.py::check_dimensions - applicability relation to the consumer requirement class is a named source gap | EQ-partial |
| context/resolver.py | ABSENT | context/news_hub_v2.py::resolve_context; context/news_hub_v2.py::event_consumable - market Event/Context resolver (News Hub V2 9.0/9.2A/9.3); NOT consulted by Composition.deliver | EQ |
| context/causal_gate.py | ABSENT | context/decision_context.py::as_of_visible; context/news_hub_v2.py::actual_available_asof - as-of visibility | EQ |
| gateway/dependency_resolution.py | ABSENT | gateway/contracts.py::DependencyEntry; gateway/contracts.py::SimulatedGateway - resolution is SIMULATED, not a real Gateway | EQ-SIMULATED |
| gateway/binding.py | EXISTS | R27 Build Plan s13A: the ONE owner of the DeliveredFeatureEntry (frozen Typed Annex V1.2 section XII; hash coverage in the Annex hash sectio | FILE |
| gateway/non_delivery.py | ABSENT | gateway/v038.py::NonDeliveryResolutionV038; gateway/v038.py::FinalResolutionStore - structured omissions; one final per identity | EQ |
| gateway/settlement.py | ABSENT | gateway/v038.py::check_settlement; gateway/v038.py::classify_late - delay value D16 unsupplied | EQ |
| gateway/health_snapshot.py | ABSENT | gateway/contracts.py::HealthSnapshot - Core gateway_health composes it in Composition | EQ-SIMULATED |
| fw/request_adapter.py | ABSENT | fw/receiver.py::receive_verified; fw/outcome_desk.py::OutcomeSeriesDesk - request/return generic; FW payload fields unbound | EQ-partial |
| fw/input_binding.py | ABSENT | fw/descriptor_crosswalk.py::require_real_binding; fw/descriptor_binding.py - ten-field bindings undeclared (documentary) | EQ-partial |
| fw/return_lineage.py | EXISTS | FW return and ML-input origin checks (Build Plan sections 12-13, current). Structural only; the FW return record's PAYLOAD fields are not de | FILE |
| ml/dataset_binding.py | ABSENT | ml/receiver.py::build_row; ml/consumer_path.py::MLConsumerPath - dataset manifest registry/authority are ML-owned ports (tests only) | EQ-partial |
| ml/standalone_ancestry.py | ABSENT | ml/receiver.py::check_generation - standalone ancestry; closure record consumption absent | EQ-partial |
| ml/fw_augmented_rebind.py | ABSENT | ml/receiver.py::check_fw_augmented; ml/augmented_desk.py::AugmentedDesk - association HELD until reverse-H1 mapping | EQ-partial |
| ml/generation_lineage.py | ABSENT | ml/generation_lifecycle.py; ml/receiver.py::check_generation - writer/finalizer facade is ML-owned | EQ-partial |
| health/b0_adapter.py | ABSENT | health/adapters.py - B0 evidence adapters; B0_HELD_SLOTS named, none invented | EQ |
| health/quant_evidence.py | ABSENT | health/evidence.py; health/adapters.py - quant evidence observations | EQ |
| health/blast_radius.py | EXISTS | Blast radius (Build Plan 14A R1 + OB2): derived from governed dependency/consumption lineage and exact bindings, NOT by copying an upstream  | FILE |
| health/expectation.py | EXISTS | R40: generic per-subject EXPECTATION carry/validation (Master Health V3 B0 p60: EXPECTED / NOT_EXPECTED / EXPECTATION_UNKNOWN; p80 validity  | FILE |
| coordination/interface.py | EXISTS | Coordination port. Acceptance = a successful conditional compare-and-swap of the namespace HEAD. | FILE |
| coordination/transition_record.py | EXISTS | Feature lifecycle transitions as accepted-journal records, with the state machine that governs them. | FILE |
| coordination/object_store_journal.py | EXISTS | Journal over an ObjectStore with conditional writes. | FILE |
| coordination/fencing.py | EXISTS | Fencing helpers. The fence is the epoch held in HEAD; a writer is current only while HEAD still carries its epoch. | FILE |
| coordination/recovery.py | EXISTS | Unknown-commit resolution, orphan discovery, cold rebuild. | FILE |
| coordination/scheduler.py | EXISTS | Bounded, deterministic replay scheduling (Q16 boundary). Correlated replay of many namespaces cannot starve | FILE |
| storage/object_store.py | EXISTS | ObjectStore port: strong read-after-write, conditional create, conditional replace. | FILE |
| storage/postgres_read_model.py | EXISTS | Derived read model. NAME follows the plan; the engine here is stdlib sqlite3 because no Postgres provider is | FILE |
| storage/keys.py | EXISTS | Object-store key layout. Journal records are content-addressed per (seq, hash) so an orphan from a | FILE |
