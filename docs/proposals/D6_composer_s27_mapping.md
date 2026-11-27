# D6 — Composer §27 BUILD_OUTPUT_PACKAGE: 27 absent fields, implementation-ready mapping (PROPOSED)

STATUS: PROPOSAL for Manager / Composer source-owner review. NOT runtime authority, NOT a binding, NOT an acceptance. Source: Composer V9 §27 field list (Drive export, read in full; cited by section, not copied). Producer: Composer, which has NO operative seven-field producer binding (C25 register: 0 actual operational bindings), so every row is UNSATISFIED until a binding is admitted.

Governed field/type: the §27 list names fields only; types are NOT specified in the sources read, so the 'proposed attribute' column is a Tracker-side PROPOSAL. Byte layouts: D13 (pending).

Minimum admission for every row (NOT sufficient by itself): a seven-field producer binding (scope, interface_id, version, content_hash, source_authority, acceptance_record, validity/supersession) for the Composer BUILD_OUTPUT_PACKAGE interface, accepted in the governed record by the Manager. Proposed record for it is at the end. A seven-field shape/acceptance reference does NOT supply: the actual field definitions, types and values (the §27 list names fields only); source applicability; correctness evidence; the byte layouts (D13); the clock domain for BUILT_AT (E4); or any producer's real payload. Those residuals remain with the Composer source owner.

Temporal/lineage column: Coder PROPOSALS unless a source is cited in the row; none is a verified source rule, and none is adopted by this document.

| # | §27 field | Producer | Consumer | Proposed Tracker attribute / derivation | Temporal / lineage rule | Tracker-side validation implementable now |
|---|---|---|---|---|---|---|
| 1 | CLAIM_ID | Composer (claim registry) | Tracker intake; Matrix V5 | new `claim_id` text; cross-check against the order's claim reference | bound at order issue; immutable for the attempt | shape only (non-empty text, equals order claim ref once an order record is bound) |
| 2 | REQUEST_SCHEMA_VERSION | Composer | Tracker intake | new `request_schema_version`; must equal a version in the admitted request-schema record | frozen at request time | membership in supplied version table |
| 3 | research mode | Composer | Tracker classification (route) | new `research_mode` enum from supplied versioned table | frozen at request time | enum membership only; enum numbering not invented |
| 4 | PURPOSE_PROFILE_ID/HASH | Composer / profile owner | Tracker intake | new `purpose_profile_ref` = (id, sha256) | hash must be recomputed from the admitted profile bytes (not available) | shape + hex only |
| 5 | SIMULATION_OR_AUTHORITY_CLASS | Composer | Tracker acceptor (class gate); Gateway | new `authority_class` enum; SIM class never counts as REAL | frozen at build | enum membership; SIM refused for acceptance paths |
| 6 | SOURCE_CONFIG_ID/HASH | Composer | Tracker intake | new `source_config_ref` (id, sha256) | config version fixed at build; hash over config bytes | shape only |
| 7 | BUILDER_VERSION/HASH | Composer | Tracker intake | new `builder_ref` (version, sha256); distinct from BUILDER_BUILD_ID (R7 RD4a) | fixed per build | shape only |
| 8 | TRACKER_CATALOG_SNAPSHOT_ID/HASH | Tracker catalog | Composer; Tracker verifier | new `catalog_snapshot_ref` (id, sha256) | snapshot must be at or before the order's issue point (relation undefined, see D14-class) | shape only; equality with Tracker's own current snapshot checkable once a snapshot exists |
| 9 | CATALOG_WATERMARK | Tracker catalog | Composer; verifier | new `catalog_watermark` (monotone token) | non-decreasing across builds for one lineage | monotonic check vs previous accepted watermark |
| 10 | exact input IDs/versions/hashes | Composer | Tracker verifier (lineage) | new `inputs` tuple of (id, version, sha256) | each input AVAILABLE_ASOF strictly before the fence (V0.38 rule where it applies) | shape + duplicate refusal |
| 11 | resolved feature identities/versions | Composer resolving against Tracker catalog | Tracker verifier | new `resolved_features` tuple of (FEATURE_ID, FEATURE_VERSION) | must be members of catalog snapshot | membership against supplied catalog |
| 12 | dependency graph/closures | Composer | Tracker verifier | new `dependency_closure` (sorted ids + closure hash) | closure must be complete over inputs; hash recomputed by independent encoder (D13 layout pending) | closure completeness (every dependency present); hash layout unavailable |
| 13 | source/vintage/time semantics | Composer | Tracker verifier; Gateway | new `time_semantics` (vintage ref, AVAILABLE_ASOF, KNOWABLE_AT) | identity timestamp != causal/finalization timestamp (hard-won lesson) | type separation only; KNOWABLE_AT mapping MISSING in source |
| 14 | operation/grammar versions | Composer | Tracker verifier | new `grammar_version`, `operation_versions` | frozen at build | membership in supplied table |
| 15 | parameters | Composer | Tracker verifier | new `parameters` canonical (name,value-type,value) tuple | fixed at build; part of declared_graph_hash | canonical-order and duplicate checks |
| 16 | search/candidate set/exclusions | Composer | Tracker verifier; multiple-testing accounting | new `candidate_set_ref` (id, sha256, count) | exclusions recorded, not dropped | count consistency only |
| 17 | OUTCOME_INFORMATION_ACCESS declaration and fitting/holdout contract reference | Composer | Tracker verifier (leakage gate) | new `outcome_information_access` enum + `fitting_holdout_ref` | declared before fit; absent => fail closed | presence + enum membership; semantics (leakage) not provable here |
| 18 | bounded materialization/query policy reference | Composer | Tracker materializer | new `materialization_policy_ref` | fixed at build | shape only |
| 19 | intermediate nodes/hashes | Composer | Tracker verifier | new `intermediate_nodes` tuple of (node id, sha256) | each node hash recomputable from graph | shape + duplicate refusal |
| 20 | fitted/learned state | Composer | Tracker verifier | new `fitted_state_ref` (id, sha256) or explicit NONE marker | fit window must precede holdout; absent must be explicit NONE, never omitted | presence-or-explicit-NONE |
| 21 | UPSTREAM_MODEL_ID and UPSTREAM_GENERATION_ID plus generation authority class | ML Gateway / generation owner | Tracker verifier; ML §29B recertification | new `upstream_model_id`, `upstream_generation_id`, `generation_authority_class` | revoked generation must not be revived (restore path open) | shape; revocation status needs generation registry (absent) |
| 22 | missingness and quality behavior | Composer | Tracker verifier | new `missingness_policy_ref` | fixed at build | shape only |
| 23 | environment/code/config | Composer | Tracker verifier | new `environment_ref` (code hash, config hash, runtime id) | BOM per Build Plan E-10 | shape only |
| 24 | output hash | Composer | Tracker verifier | new `output_hash` sha256 | recomputed from authoritative output bytes by verifier | hex shape; recompute needs bytes |
| 25 | BUILT_AT | Composer clock | Tracker verifier | new `built_at` timestamp (clock domain per E4) | identity vs causal timestamp separation; must not exceed order deadline | timestamp shape; clock domain unavailable (E4) |
| 26 | TEST/EVIDENCE REFERENCES | Composer | Tracker acceptor | new `evidence_refs` tuple (id, sha256) | plural field maps to refs, not a single ref (ML Health V2 alias rule analogue) | shape + duplicate refusal |
| 27 | warnings/unresolved constraints | Composer | Tracker acceptor | new `warnings` tuple of text; any unresolved constraint blocks acceptance | fail closed on non-empty unresolved set | non-empty unresolved => refuse |

## Already mapped (8 of 35), for completeness
| §27 field | BuildPackage attribute | Status |
|---|---|---|
| CREATION_REQUEST_ID | creation_request_id | DIRECT (same concept) |
| ORDER_ID | order_id | DIRECT (same concept) |
| construction graph ID/hash | declared_graph_hash | DIRECT (same concept) |
| manifest ID/hash | declared_manifest_hash | DIRECT (same concept) |
| BUILDER_BUILD_ID | attempt_id | CANDIDATE (needs Composer-owner confirmation) |
| purpose/hypothesis | semantic_definition | CANDIDATE (needs Composer-owner confirmation) |
| INSTRUMENT_PROFILE_ID/HASH | expected_instrument | CANDIDATE (needs Composer-owner confirmation) |
| request context | request_id | CANDIDATE (needs Composer-owner confirmation) |

## Proposed seven-field producer binding record (values to be supplied by source owner; none invented)
```
scope:                 Composer -> Tracker BUILD_OUTPUT_PACKAGE (Composer V9 section 27)
interface_id:          <to be assigned by Manager>
version:               <Composer contract version in force>
content_hash:          <sha256 of the admitted interface text; to be recomputed from authoritative bytes>
source_authority:      <governed document id + section range>
acceptance_record:     <Manager acceptance record id>
validity/supersession: <valid-from + supersedes/superseded-by>
```
`stage_a.binding.producer_binding.check_shape` validates only the SHAPE of such a record. Passing is not admission.

Drift guard: tests/trk_stage_a/test_r09_proposal_docs.py asserts this table lists exactly the 27 ABSENT fields.
