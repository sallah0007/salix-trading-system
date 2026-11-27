# FW outcome-descriptor crosswalk — source status, ownership, and exact residuals (CORRECTED in R10; documentary, NOT an interface)

STATUS: documentary restatement of mapping A04 (Drive 12h77ZuFRezmZr4_8Zrs1BDyYUtpnoMlI; 61,967 B; stated SHA-256 ea9e7949397dd1e9ad001334425fdfeb96706d7eadca67bd043496d6ec91dfc0 hash-verified by the Manager; not recomputed by the Coder). It creates NO interface, adopts NO type, and is not a binding.

CORRECTIONS to the R09 draft (withdrawn): (1) direction 'FW -> Tracker' and 'FW producer' assignments were wrong; (2) ADMISSIBILITY_STATE is FW-owned, not Tracker-derived; (3) 'single missing admission' was too strong; (4) 'END < fence' was asserted as a universal descriptor rule without source: withdrawn.

SCOPE (source `FW_crosswalk_scope`): outcome/target-label-series class under Connected Contract V0.38 H3 ONLY. Feature-view/package delivery keeps its distinct contract. Status labels are documentary classifications, not source enums.

DIRECTION/OWNERSHIP (source FW V1.2 N-2 and every crosswalk row): FW_INTERNAL_OUTCOME_DESCRIPTOR is internal to FW and is NOT the Tracker->FW consumer contract. The versioned Tracker->FW request payload is adapted into the descriptor at the FW boundary. Owner of every row: 'Tracker payload function / FW boundary adapter'. All actual payload bindings: UNDECLARED_REAL_PAYLOAD_BINDING.

| # | Descriptor field | Source status | H3 source fields | Owner (source) | Source-stated gap |
|---|---|---|---|---|---|
| 1 | OBSERVATION_REF | PARTIAL_SOURCE_CARRIER | OUTCOME_OR_TARGET_SERIES_ID / VERSION_OR_HASH; OBSERVATION_TIME_ORIGIN | Tracker payload function / FW boundary adapter | Series/origin identity only; not shown to identify one observation. Observation-level reference or governed derivation missing. |
| 2 | DEPENDENCY_INTERVAL_START | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | DEPENDENCY_INTERVAL_START | Tracker payload function / FW boundary adapter | Units/profile, actual values, completeness unbound. |
| 3 | DEPENDENCY_INTERVAL_END | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | DEPENDENCY_INTERVAL_END | Tracker payload function / FW boundary adapter | Same units/domain as start; boundary convention (open/closed) must come from governed time/profile. NO relation to the snapshot fence is asserted here: this H3-class source rows do not establish END < fence. |
| 4 | HORIZON_ID | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | HORIZON_ID | Tracker payload function / FW boundary adapter | Source-owned horizon semantics; never private wall-clock or bar count. |
| 5 | HORIZON_VERSION | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | HORIZON_VERSION | Tracker payload function / FW boundary adapter | Exact governed version/hash resolution required. |
| 6 | SEGMENT_REF | MISSING_EXACT_SOURCE_MAPPING | (none) | Tracker payload function / FW boundary adapter | H3 carries the authorization set/stage, not a per-observation SEGMENT_REF; authorized set cannot substitute for observation membership. Real profile/payload mapping missing. |
| 7 | AUTHORIZED_SEGMENT_SET | DIRECT_SCHEMA_CARRIER_NOT_INSTANCE | AUTHORIZED_SEGMENT_SET / STAGE; CONSUMER_STAGE | Tracker payload function / FW boundary adapter | Resolve exact currently authorized segments and applicable stage/unseal evidence. |
| 8 | KNOWABLE_AT | MISSING_EXACT_SOURCE_MAPPING | (none) | Tracker payload function / FW boundary adapter | AVAILABLE_ASOF is the binding decision cutoff, not each observation's knowability; CAUSAL_POLICY_ID names a policy, not a timestamp. Exact causal lineage/derivation missing. |
| 9 | ADMISSIBILITY_STATE | INTERNAL_DERIVATION_UNBOUND | (none; internal N-2 enum) | FW (internal N-2 enum); row owner as source | FW-OWNED internal N-2 enum (ADMISSIBLE | MASKED | REFUSED_OUT_OF_SEGMENT | REFUSED_HOLDOUT | UNKNOWN); derived only under FW causal/segment/holdout rules from admitted evidence; no default ADMISSIBLE. Tracker does not own or derive it. |
| 10 | VINTAGE_REF | PARTIAL_SOURCE_CARRIER | SOURCE / VINTAGE / CAUSAL_POLICY_ID; DATA_VINTAGE_MODE | Tracker payload function / FW boundary adapter | Policy/mode references are constraints, not per-observation vintage identity; exact source/vintage refs and coherence evidence required. |

## Exact residuals that a seven-field shape/acceptance reference does NOT supply
A seven-field record (scope, interface_id, version, content_hash, source_authority, acceptance_record, validity/supersession) identifies and accepts an interface. For these rows it would still leave, per source `closure` text:
1. the exact real payload / schema / version / hash / profile (not yet declared);
2. the authoritative field or a justified derivation per descriptor field (KNOWABLE_AT, SEGMENT_REF, OBSERVATION_REF, VINTAGE_REF have none);
3. actual field definitions and values (types, units, domain, interval convention) from governed trading/session/time/profile semantics;
4. source applicability (H3 outcome/target-label-series only) and correctness evidence;
5. units/domain/interval, causal, segment, holdout and vintage validation;
6. separately commissioned positive and refusal evidence.
Tracker-side validation implementable now is limited to shape checks (`stage_a.binding.producer_binding.check_shape`) and refusal of MISSING/INTERNAL fields (`descriptor_crosswalk`). No type is proposed here; any proposed type needs source-owner adoption, not Manager approval alone.

Drift guard: tests/trk_stage_a/test_r09_proposal_docs.py checks all ten names and their source statuses appear.
