# SALIX Trading — Stage A — Tracker

Authored end to end under the Owner delegation recorded in `CLAUDE.md` §2A (this repository only).
A merge of this code is a **code event**: it does not clear, close or advance any gate, hold, acceptance or stage.
Governance state changes only when the Manager records it in Drive. Governing sources are cited by ID only
(Plan `TRK-FULL-P03`, Composer §27/§28, Build Plan §27 TR-01–TR-15); none is copied here.

## Scope
The whole Tracker lifecycle in the frozen order: SAFE INTAKE → ADMISSIBILITY → FEATURE IDENTIFICATION →
CLASSIFICATION → CERTIFICATION → MATERIALIZATION → RECORDING VERIFICATION, then CANONICAL ACCEPTANCE and
PUBLISHABLE as status transitions on an accepted-transition journal. Tracker is the only order consumer here;
nothing in this package issues orders as a role.

## Dependency map (forward and backward)
```
tracker_identity (baseline, unchanged)  <--  tracker_component (orders/claims/journal port/§28 report)  <--  stage_a
stage_a/errors, identifiers, clocks, authority, observability, replay, currentness      shared foundations
stage_a/storage/{keys,byte_primitives,object_store,postgres_read_model}                 storage (read model = sqlite stand-in)
stage_a/coordination/{interface,object_store_journal,fencing,transition_record,recovery,scheduler}
stage_a/composer/expression/{schema,manifest,opcodes,capability,canonical_encoding,hashing,evaluator,fit_generation,artifacts}
stage_a/tracker/{quant_intake_adapter,quant_certification,registry,publication,authority_bridge,pipeline}
stage_a/tracker/materialization/stateful_materializer.py                                producer side
stage_a/tracker/verification/*                                                          INDEPENDENT side (own encoder, hasher, traversal, reference evaluator)
```
Forward: nothing downstream (Gateway, FW, ML, Health) is called; publication is eligibility only (`delivered` is a
structural constant `False`). Backward: the baseline is only *called* (`safe_intake_built_identity`,
`identity_lookup`), never edited. Direction is enforced by `tests/trk_stage_a/test_dependency_direction.py`.
Deviation from the plan's "stage_a → tracker_identity only": stage_a also depends on `tracker_component`.

## Authority model
* Orders and claims are hash-chained journal records (`tracker_component`); the verifier re-checks order validity at the commit point.
* Acceptance first **exercises** the claim (`CLAIM_CONSUMED`, compare-and-append on the claims journal), then appends
  `CANONICAL_ACCEPTED` carrying that record as `claim_witness`. A crash in between leaves a consumed claim without
  acceptance; re-running the same request completes it exactly once. The fence is checked **before** spending authority.
* Each authority namespace (`INSTRUMENT/TIMEFRAME/FEATURE_ID`) has one immutable journal and one mutable HEAD
  `{seq,hash,epoch}`. Acceptance = successful conditional replace of HEAD. Records are content-addressed per
  `(seq,hash)`; objects not reachable from HEAD are orphans with no authority.
* `authority_bridge.make_construction_authority_resolver` builds a fail-closed resolver for the baseline's single seam
  (`tracker_identity.store._governed_construction_authority`). It is **not installed**: the baseline stays hard-False.

## Failure / refusal matrix (all fail closed, all produce a verifiable 23-entry §28 report)
SCHEMA, HASH_BINDING, CAPABILITY, FIT_ANCESTRY, SCOPE_BINDING, IDENTITY_CONTENT_KEY, LOOKUP_COMPLETENESS
(ERA_1 structural absence is **not** absence), DUPLICATE (EXACT→REUSE_EXISTING, NEAR→REVIEW_REQUIRED),
CONSTRUCTION_AUTHORITY (NO_ORDER, ORDER_REVOKED, ISSUER_NOT_ANCHORED, SOURCE_BINDING_MISMATCH, ORDER_EXPIRED,
SUBJECT_ALREADY_CLAIMED…), CERTIFICATION, MATERIALIZATION, INDEPENDENT_VERIFICATION, BASELINE_REGISTRATION.
A failed *requested* quant build is `FAILED_REQUESTED_BUILD`, never `NO_QUANT_FEATURE` (TR-06).

## Tests and evidence
`python3 -m pytest tests -q` (all suites) · `python3 -m unittest discover -s tests` (unittest-style suites)
· `python3 tests/trk_stage_a/mutation_sweep.py` (22 deliberate defects; every one must be killed).
Expected values in `tests/trk_stage_a` are **hand-derived by the author** (self-generated oracle).

## Independent-review state
None. Authorship independence between materializer and verifier is **not** achieved (same author); only code-level
independence is enforced (static import audit, separate encoder/hasher/traversal/reference evaluator, cross-checked
by deliberate defects on both sides). Codex/Manager may challenge.

## Known open integrations
See the PR description / `coder_returns/TRK-STAGE-A-TRACKER-R01.md` (D1–D10).

## Migration / rollback
Purely additive (new packages `stage_a/`, tests, and two small additive methods on `ClaimService`). Rollback = revert the merge.
