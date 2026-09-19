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
- stale-state hygiene checks.

## Era-scoped absence invariant
- ERA_1_ONLY no-match may emit only ABSENT_IN_ERA_1.
- ALL_ERAS remains INCOMPLETE_LOOKUP while Era 0 coverage is unresolved.
- At the era-blind Composer boundary, ABSENT_IN_ERA_1 maps to INCOMPLETE_LOOKUP, never global ABSENT.

## Safe-intake era invariant
- Composer/build output is era-blind.
- Tracker safe intake assigns era_id solely from the verified active CanonicalEraBoundary.
- No active boundary, registry mismatch, or active-era mismatch fails closed before mutation.

## Explicitly out of scope
- feature materialization;
- eligibility computation;
- Tracker health;
- package production;
- Consumer Gateway delivery;
- Forward-Walk execution;
- ML training;
- trading/risk/execution logic;
- Type 2 production integration.

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
- incomplete search-policy/normalizer metadata.

Historical/superseded records remain preserved but explicitly non-current.
