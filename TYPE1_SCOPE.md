# SALIX Tracker Identity Surface — Type 1 Scope

This branch is a **Type 1 — pre-freeze reference/candidate implementation**.

## Authorized surface
- canonical feature-definition identity metadata store;
- Tracker safe-intake assignment of newly built identities to the verified active canonical era boundary;
- versioned search-policy identity/hash;
- versioned normalizer identity/hash and declared equivalence classes;
- enumerable search scopes and governed exclusions;
- IDENTITY_LOOKUP_RESULT;
- deterministic lookup evidence hash;
- stale-state hygiene checks;
- universal governed authority-state transition-history record shape as applied to Tracker Type 1;
- safe-intake creation provenance for the initial authority state.

## Era-scoped absence invariant
- ERA_1_ONLY no-match may emit only ABSENT_IN_ERA_1.
- ALL_ERAS remains INCOMPLETE_LOOKUP while Era 0 coverage is unresolved.
- At the era-blind Composer boundary, ABSENT_IN_ERA_1 maps to INCOMPLETE_LOOKUP, never global ABSENT.

## Safe-intake era invariant
- Composer/build output is era-blind.
- Tracker safe intake assigns era_id solely from the verified active CanonicalEraBoundary.
- No active boundary, registry mismatch, or active-era mismatch fails closed before mutation.

## Initial authority-state provenance
- Safe intake is the governed birth event for a newly built identity.
- It must record why the identity is born into its initial lifecycle/authority state, who created it, and the governing authority reference.
- No synthetic NULL -> CANDIDATE/CURRENT transition is invented.
- creation_reason_ref, created_by, and authority_ref are mandatory before mutation.

## Authority-state transition history
Every later authority/lifecycle-state change for a tracked Type-1 identity uses an append-only GOVERNED_STATE_TRANSITION_RECORD.

Required invariants:
- state mutation and transition-record append occur atomically on the governed Type-1 path;
- from_state must equal the object's actual current state inside the atomic operation;
- prior_transition_id chains the first transition to the creation record and later transitions to their immediate predecessor;
- reason_class, reason_ref, changed_ts, changed_by, and authority_ref are mandatory;
- OTHER_GOVERNED may never be justified by free text alone; it requires a governed reason_ref;
- historical transition records are immutable; recovery/rollback appends a new record;
- current object state must reconcile to the terminal valid transition state;
- forks, orphan/cyclic history, duplicate transition IDs, and tracked-object state/history disagreement fail stale-state sweep.

Master Health may inspect/replay this common history shape but does not acquire Tracker promotion, recovery, quarantine, retirement, or mutation authority.

## Type-1 direct-mutation limitation
The Type-1 store is an in-memory reference implementation. Raw direct mutation of store internals remains technically possible and is therefore a known bounded bypass at Type 1.

For objects already tracked by creation/transition history, stale-state sweep detects state/history divergence. Prevention of unauthorized direct storage mutation belongs to Type 2 storage/permission enforcement.

BYPASS_PATH_COUNT = 1 is therefore accepted as a stated Type-1 limitation; it is not falsely represented as prevented.

## Explicitly out of scope
- feature materialization;
- eligibility computation;
- Tracker health;
- package production;
- Consumer Gateway delivery;
- Forward-Walk execution;
- ML training;
- trading/risk/execution logic;
- Type 2 production integration and storage permission enforcement.

## Empty-store invariant
An empty canonical identity store is a valid searched store.
When all mandatory scopes are searched or explicitly excluded with governed reason
codes under a complete policy and normalizer:
- LOOKUP_COMPLETE = TRUE
- OUTCOME = ABSENT_IN_ERA_1 for ERA_1_ONLY queries

Record count is not a completeness condition.

## False-complete fence
LOOKUP_COMPLETE = TRUE is prohibited if any required scope is neither searched nor
explicitly excluded, or if required search-policy/normalizer identity metadata is
missing.

## Stale-state closeout
Completion requires a clean sweep for:
- stale/current lifecycle contradictions;
- multiple current versions;
- orphan canonical-survivor pointers;
- dangling dependencies;
- current alias collisions;
- test/temp/migration identities in live scopes;
- incomplete search-policy/normalizer metadata;
- tracked-object state/history disagreement;
- transition-history forks or orphan/cyclic chains;
- duplicate creation/transition record IDs;
- missing mandatory transition/creation provenance fields.

Historical/superseded records remain preserved but explicitly non-current.

## Validation containment invariant
- validation is a Tracker scope, not a lifecycle state.
- validation-scope identities use the normal CURRENT lifecycle while they remain current.
- stale-state sweep rejects validation-scope rows whose lifecycle is not CURRENT or whose is_current flag is false.
- ordinary identity lookup excludes scope=validation.
- explicit include_validation_scope=true is required to inspect validation-scope identities.
- validation scope is Tracker-internal baseline/conformance content and must not be emitted as ordinary consumer feature content.
