FROM = CODER
MESSAGE_ID = C-GOLD-ID-GATE-HARDENING-001
SEGMENT_ID = ERA1-BOOTSTRAP-CONTRACT-RECON-001
TASK_STATE = ANSWERED

# Type-1 post-admission identity gate hardening — C-1 / H-1 / M-1

## SOURCES AND BASIS

SOURCE_DOCUMENTS_AVAILABLE_LOCALLY = NO

This session has no Google Drive access and no GitHub connector. The only
inputs were the Owner-relayed commission text and the local repository. Every
Drive ID cited in the commission (governed authorities, Canonical 7, Owner
decisions) was NOT opened here. No claim in this report depends on one.

CURRENT_MAIN_VERIFIED = YES
  git rev-parse origin/main (post-fetch) == ec8478540cf5e4df1c947575c5b64f5c1360a1bf

BASE_SHA = ec8478540cf5e4df1c947575c5b64f5c1360a1bf
TARGET_BRANCH = type1/post-admission-identity-gate-hardening
  created with: git switch --detach <BASE_SHA> ; git switch -c <TARGET_BRANCH>
HEAD_SHA = ba72b78415aa96e7d60598f525fc41f38fda3217
  (this report is committed separately on top of that commit)

WORKTREE_STATUS_BEFORE = clean; git diff --stat vs BASE_SHA empty
WORKTREE_STATUS_AFTER  = clean after commit; only __pycache__ present, already
                         covered by the repository's own .gitignore

## ENVIRONMENT

PYTHON_INTERPRETER_AVAILABLE = YES (installed during this commission)
INTERPRETER_PATH = C:\Users\salla\AppData\Local\Programs\Python\Python312\python.exe
PYTHON_VERSION = 3.12.10
INSTALL_METHOD = winget, user scope, from python.org; installer hash verified
REQUIRED_DEPENDENCIES = NONE

Determined from repo files, not assumed: there is no requirements.txt,
pyproject.toml, setup.py, setup.cfg, Pipfile, tox.ini, pytest.ini or
.python-version anywhere in the repository. `.github/workflows/type1-tests.yml`
pins Python 3.12, runs `python -m unittest discover -s tests -v`, and has no
dependency-install step. The governed suite is standard-library only and uses
unittest, not pytest. Nothing was installed into or configured inside the repo.

## CHANGED FILES

CHANGED_FILES =
  tracker_identity/policy_registry.py     NEW
  tracker_identity/search.py              M-1 / H-1 binding
  tracker_identity/intake.py              C-1 claim gate, integrity-first order
  tracker_identity/store.py               C-1 claim gate at the atomic boundary
  tracker_identity/__init__.py            exports
  tests/test_identity_surface.py          NC01-NC27 + registry integrity
  tests/test_safe_intake_era.py           fixture repair
  tests/test_registration_atomicity.py    fixture repair + defect test inverted
  tests/test_import_content_key.py        governed policy for its one lookup

DIFF_STATS (vs BASE_SHA, implementation commit) =
  8 files changed, 714 insertions(+), 54 deletions(-)
  tests/test_identity_surface.py       | 511 ++++-
  tests/test_registration_atomicity.py |  70 ++-
  tests/test_safe_intake_era.py        |  67 ++-
  tests/test_import_content_key.py     |  10 +-
  tracker_identity/store.py            |  69 +--
  tracker_identity/intake.py           |  25 +-
  tracker_identity/__init__.py         |   9 +
  tracker_identity/search.py           |   7 +
  plus tracker_identity/policy_registry.py (new file)

DO_NOT_TOUCH VERIFIED: population/**, .github/** and CLAUDE.md are absent from
`git diff --name-only BASE_SHA..HEAD`. Composer, Connected Contract, Gold
feature calculation/evidence, FW, ML, Type-2 and production code untouched.
No file outside the authorized scope was modified.

## DEFECT CLOSURE

C1_CLOSED = YES
H1_CLOSED = YES
M1_CLOSED = YES

CLAIM_MANDATORY_FOR_NEW_CANONICAL_REGISTRATION = YES
CLAIMLESS_ORDINARY_REGISTRATION_POSSIBLE       = NO
MANDATORY_SCOPE_FALSE_ABSENCE_POSSIBLE         = NO
CALLER_CAN_REDEFINE_GOVERNED_SEARCH_POLICY     = NO

### C-1 — what was actually wrong

`commit_registration` guarded claim validation behind
`if content_key_composite is not None and request_id is not None:` and fell
through to `held=None` otherwise, then registered anyway. `safe_intake` never
required `claim_request_id` at all. A caller passing no claim reached canonical
registration with the lookup/claim gate entirely skipped.

Now: a non-blank `request_id` AND a content key are required; the claim must
exist, be ACTIVE, be unexpired, be bound to that request_id and to the
recomputed CONTENT_IDENTITY_KEY; duplicate re-check, identity append, creation
append and claim consumption remain one atomic transaction under the unchanged
lock order.

A second, deeper half of C-1 surfaced while fixing it: candidates with no
derivable content key were previously registered bare. They are now refused,
because a claim cannot be validated against a key that does not exist.

### H-1 / M-1 — what was actually wrong

`SearchPolicy.completeness_errors()` only checks INTERNAL consistency, and
`computed_hash()` is derived from the caller's own field values. A caller could
therefore invent any `required_scopes`, exclude a mandatory scope with any
non-blank reason string, self-hash the result, and receive a claimable
structural absence while a duplicate sat unsearched.

Now `identity_lookup` calls `resolve_governed_search_policy`, which requires an
exact match against a Tracker-owned registry entry: id, version, required
scopes, searched scopes, exclusions, exclusion reason codes, and a hash compared
against the GOVERNED hash. Two further checks — MANDATORY_SCOPE_NOT_SEARCHED and
MANDATORY_SCOPE_EXCLUDED — are evaluated independently of the registry entry, so
they hold even if an entry were itself wrong. Registry entries are validated at
import time and the module refuses to load if defective.

GOVERNED V1: SEARCH_POLICY_ID = tracker.identity.search, SEARCH_POLICY_VERSION
= 1, required = searched = the 13 mandatory lifecycle scopes, no exclusions
permitted. Future versions are added as separate entries; a published entry is
never edited in place, because that would silently re-interpret every historical
lookup evidence hash citing it.

## TESTS

TARGETED_TEST_COMMAND =
  <PY> -m unittest tests.test_identity_surface -v
TARGETED_TEST_RESULT = Ran 56 tests — OK

FULL_TEST_COMMAND =
  <PY> -m unittest discover -s tests
FULL_TEST_RESULT = Ran 188 tests — OK
  TOTAL=188 PASSED=188 FAILED=0 ERRORS=0 SKIPPED=0 XFAILED=0

BASELINE_FULL_TEST (unmodified BASE_SHA) = Ran 155 tests — OK
  155 baseline + 33 new = 188. No baseline test was deleted.

DERIVATION_CLASS = INDEPENDENTLY_DERIVED (executed)
REPRODUCIBLE_BY_MANAGER = YES

### Mutation check — the controls can fail

A test that cannot fail is not evidence. Each new guard was deliberately broken
in a scratch copy (never in the repo) and the suite re-run:

  M1 drop CLAIM_REQUEST_ID_REQUIRED in intake.py        -> 4 failures
  M2 drop governed-policy binding in search.py          -> 6 failures
  M3 drop claim gate in commit_registration             -> 1 failure
  M4 drop MANDATORY_SCOPE_NOT_SEARCHED in registry      -> 3 failures

All four mutants are caught.

## CHANGED EXISTING TESTS

Nine tests were changed across three files. Two encoded the defect; seven used
the unsafe path as fixture setup. No assertion was weakened.

--- TEST_NAME = test_intake_without_a_claim_still_works
    (renamed to test_intake_without_a_claim_is_refused)
OLD_EXPECTATION = claimless intake succeeds; docstring asserted "Claim
  presentation is optional; governed legacy intake is unchanged".
NEW_EXPECTATION = refused with CLAIM_REQUEST_ID_REQUIRED; store and creation
  records both remain empty.
WHY_OLD_EXPECTATION_WAS_UNSAFE_OR_FIXTURE_INVALID = this test WAS C-1. It
  asserted the bypass as correct behaviour. It passed at baseline, which is how
  the defect stayed live.

--- TEST_NAME = test_same_canonical_key_cannot_be_registered_twice
OLD_EXPECTATION = claimless intake registers the first identity; a later
  commit_registration(content_key_composite=None, request_id=None) reaches the
  canonical-key check and returns CANONICAL_KEY_ALREADY_REGISTERED.
NEW_EXPECTATION = both registrations present valid claims; the isolation check
  presents a VALID active claim whose canonical key is already registered, and
  still returns CANONICAL_KEY_ALREADY_REGISTERED.
WHY_OLD_EXPECTATION_WAS_UNSAFE_OR_FIXTURE_INVALID = the isolation half asserted
  NC09's bypass — that a claimless direct call reaches the registry's inner
  checks at all. The proposition (canonical-key defence in depth) is valid and
  is preserved; the route to it was the defect. An assertion was ADDED that the
  refusal is not merely the claim gate firing.

--- TEST_NAME = test_C_identity_appearing_after_claim_blocks_stale_claimant
OLD_EXPECTATION = a second claimless intake supplies the competing identity.
NEW_EXPECTATION = the competing identity arrives via store.add(), the governed
  import route, while the worker holds its claim.
WHY_OLD_EXPECTATION_WAS_UNSAFE_OR_FIXTURE_INVALID = fixture only. Under C-1 a
  second intake cannot supply it, because only one active claim per content key
  can exist — which is the control working. Import is the genuine remaining way
  for an identity to appear between claim and registration, so the test now
  exercises the real scenario rather than an impossible one.

--- TEST_NAME = test_safe_intake_assigns_era_only_from_active_boundary
--- TEST_NAME = test_candidate_cannot_supply_or_override_era
--- TEST_NAME = test_stale_failure_does_not_mutate_store
OLD_EXPECTATION = registration succeeds with no claim presented.
NEW_EXPECTATION = a claim is reserved first via claim_for(); registration then
  succeeds. In test_stale_failure the second candidate also presents a valid
  claim and is asserted NOT to fail on CLAIM_REQUEST_ID_REQUIRED, so the test
  still proves non-mutation on stale failure rather than on the claim gate.
WHY_OLD_EXPECTATION_WAS_UNSAFE_OR_FIXTURE_INVALID = fixture only. Their
  propositions (era assignment, era non-override, non-mutation) are unchanged.

--- TEST_NAME = test_safe_intake_era candidate() fixture (affects all 13 tests)
OLD_EXPECTATION = candidates carried no governed content dimensions and were
  registered with content_key_composite = None.
NEW_EXPECTATION = candidates carry the full governed content dimensions so a
  CONTENT_IDENTITY_KEY derives.
WHY_OLD_EXPECTATION_WAS_UNSAFE_OR_FIXTURE_INVALID = registering identities with
  no content key is the second half of C-1: such a row cannot participate in
  content-keyed duplicate control and cannot have a claim validated against it.
  None of these dimensions feed computed_definition_hash or computed_graph_hash,
  so the two hash-tamper tests are untouched and still expose their own defects.

--- TEST_NAME = test_I7_pre_id_remains_operational_after_import
OLD_EXPECTATION = a PRE_ID lookup under policy_id "import-ctl" with a single
  searched scope ("current_active") returns EXACT_CANONICAL_IDENTITY.
NEW_EXPECTATION = the lookup runs under governed_search_policy() and all 13
  mandatory scopes are declared reachable; still EXACT_CANONICAL_IDENTITY.
WHY_OLD_EXPECTATION_WAS_UNSAFE_OR_FIXTURE_INVALID = it was an instance of both
  H-1 and M-1: an ungoverned, self-hashed policy searching 1 of 13 mandatory
  scopes. The test's real proposition — PRE_ID still works after import — is
  preserved and is now proven under governed duplicate control.

## NEGATIVE_CONTROL_MATRIX

All 27 executed and passing. Located in tests/test_identity_surface.py
(GateHardeningNegativeControls) unless noted.

NC01 safe_intake claim_request_id=None                  -> FAIL  PASS
NC02 claim_request_id=""                                -> FAIL  PASS
NC03 whitespace claim_request_id                        -> FAIL  PASS
NC04 fabricated claim                                   -> FAIL  PASS
NC05 expired claim                                      -> FAIL  PASS
NC06 released claim                                     -> FAIL  PASS
NC07 claim bound to a different request                 -> FAIL  PASS
NC08 claim bound to a different content key             -> FAIL  PASS
NC09 direct commit_registration without claim           -> FAIL  PASS
NC10 INCOMPLETE_LOOKUP cannot yield successful intake   ->       PASS
NC11 Era-1 absence cannot authorize global FEATURE_ID   ->       PASS
NC12 exclude current_active holding a duplicate         -> INCOMPLETE/no claim  PASS
NC13 remove current_active from required scopes         -> FAIL  PASS
NC14 remove mandatory historical scope                  -> FAIL  PASS
NC15 self-hashed ungoverned SearchPolicy                -> FAIL  PASS
NC16 same id/version, changed scopes                    -> FAIL  PASS
NC17 same id/version, changed exclusions                -> FAIL  PASS
NC18 wrong governed policy hash                         -> FAIL  PASS
NC19 governed V1 retains legitimate exact match         ->       PASS
NC20 governed V1 retains legitimate near-match review   ->       PASS
NC21 concurrent identical PRE_ID -> one active claim    ->       PASS
NC22 expired-worker ABA remains blocked                 ->       PASS
NC23 identity appearing after claim blocks registration ->       PASS
NC24 canonical survivor remains fail-closed             ->       PASS
NC25 unkeyed searched rows block PRE_ID absence         ->       PASS
NC26 validation-scope protections intact                ->       PASS
NC27 typed content-key encoding protections intact      ->       PASS

## SECOND_PASS_ATTACK

17 probes executed outside the automated suite, against the built branch.
16 BLOCKED, 1 residual and scoped.

BLOCKED:
  A1  claim reuse after successful registration      CLAIM_NOT_ACTIVE:RELEASED
  A2  one claim registering two identities           CLAIM_NOT_ACTIVE:RELEASED
  A4  padded-reserved claim presented clean          CLAIM_NOT_FOUND
  A5  candidate carrying era_id                      no such field exists
  A6  caller-supplied content key on the subject     INCOMPLETE_LOOKUP
  A7  scope ORDER permutation, self-hashed           3 governance errors
  A8  governed hash replayed onto narrowed scopes    MANDATORY_SCOPE_NOT_SEARCHED
  A9  blank-reason exclusion of a mandatory scope    INCOMPLETE_LOOKUP
  A10 duplicate hidden by dropping its scope         INCOMPLETE_LOOKUP, no claim
  A11 control: governed policy SEES that duplicate   EXACT_CANONICAL_IDENTITY
  A12 runtime-injected rogue registry entry          MANDATORY_SCOPE_NOT_SEARCHED
  A13 in-place mutation of a live governed entry     TypeError (hardened, below)
  A13b mandatory exclusion with a rogue ENTRY        MANDATORY_SCOPE_EXCLUDED
  A15 ALL_ERAS emitting absence                      INCOMPLETE_LOOKUP
  A16 rewinding the store clock to revive a claim    CLAIM_NOT_ACTIVE:EXPIRED

A13 was BYPASSED on first run: permitted_exclusions was a caller-owned dict and
could be edited in place at runtime. Hardened during this commission —
GovernedSearchPolicyEntry.__post_init__ now normalises scopes to tuples and
wraps permitted_exclusions in MappingProxyType. A13b then confirmed the
defence in depth: even with a deliberately rogue registry entry installed, the
independent mandatory-scope checks still refuse the exclusion. Both are pinned
by tests.

A3 is reported as behaviour, not a bypass: a request_id is whitespace-stripped
before comparison, so "  R3  " matches a claim reserved as "R3". This is
normalisation of the same logical request, and the converse (A4) fails closed.
Flagged so it is a recorded decision rather than an accident.

### RESIDUAL — NOT CLOSED BY THIS COMMISSION

A14 store.add() / store.extend() are NOT claim-gated.
  `import_identity_content` writes through `target_store.extend()` at
  importer.py:365 and never calls commit_registration. The governed import
  route therefore still writes identities without a claim.
  This is the condition the commission named: "If a governed import/migration
  route genuinely requires claimless registration: DO NOT add it in this
  commission. Instead stop and report the requirement." It is reported, not
  changed. C-1 as scoped covers ORDINARY canonical registration; the import
  route has its own manifest/provenance/source-universe controls, which were
  not assessed here.
  SEVERITY = MEDIUM, scoped. Recommend a separate bounded segment to decide
  whether import should carry an equivalent authority binding.

## COUNTS

NEW_CRITICAL_COUNT = 0
NEW_HIGH_COUNT     = 0
NEW_MEDIUM_COUNT   = 1   (A14 import route not claim-gated — pre-existing,
                          out of scope, reported not changed)
NEW_LOW_COUNT      = 1   (A13 entry mutability — found and closed in-commission)

ARCHITECTURE_REOPEN_REQUIRED = NO
FROZEN_TRACKER_CORE_REOPENED = NO

## FENCES — UNCHANGED BY THIS PATCH

GLOBAL_CANONICAL_ABSENCE_PROVEN = NO
ALGEBRAIC_EQUIVALENCE_IMPLEMENTED = NO
ALGEBRAIC_EQUIVALENCE_VALIDATED = NO
IDENTITY_LOOKUP_READY_FOR_GOLD = NO
FEATURE_ID_CREATION_READY_FOR_MANAGER_DECISION = NO

CANONICAL_TRACKER_FEATURE_ID = NOT ASSIGNED
FEATURE_ID_CREATED = NO
FEATURE_VERSION_CREATED = NO
TRACKER_REGISTRY_ROW_CREATED = NO
GOLD_FEATURE_ID_CREATION_AUTHORIZED = NO
GOLD_ADMITTED = YES (unchanged; not altered by this patch)
FW_EXECUTION = NO
ML_TRAINING = NO
TYPE_2 = NO
PRODUCTION = NO

Era-1 structural absence is still not global absence. This patch makes the
Era-1 duplicate search harder to falsify; it does not extend its reach. The
older/global identity universe remains incomplete and unassessed.

## HANDOFF

TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES

Exit criteria, each independently evidenced above: C1/H1/M1 closed; claim
mandatory; claimless ordinary registration impossible; mandatory-scope false
absence impossible; caller cannot redefine governed policy; all 27 negative
controls pass; full suite 188/188; second pass all clear except the one
reported and scoped residual; 0 new critical, 0 new high; no baseline test
deleted and no assertion weakened.

PUSH_SUCCEEDED = NO
PUSH_REQUIRED_BY_OWNER = NOT STATED — not pushed; awaiting instruction
PR_CREATED = NO
MERGED = NO

DO NOT MERGE.

CODER FINDING != SALIX DECISION
TEST PASS != GOVERNANCE CLOSURE
A successful patch does NOT authorize FEATURE_ID creation.
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE

---

# MANAGER RE-ATTACK CORRECTION — C-1R / M-1R

APPENDED, not replacing. Everything above stands as written at HEAD ba72b78
and is preserved for audit. This section records the correction only.

BASE_FOR_CORRECTION = e5fdc61be95eeddb8c4fa138d5291b283ad9d685
ba72b78 and e5fdc61 were NOT amended, rebased or squashed.

## C-1R — ACTIVE CLAIM WAS NOT GOVERNED CONSTRUCTION AUTHORITY

Manager finding CONFIRMED and reproduced. At ba72b78, reserve_claim() was
publicly callable with no provenance: a caller could compute a content key,
mint an ACTIVE claim, and redeem it at registration with no completed
identity_lookup anywhere in the chain. ClaimRecord bound only
claim_id/content_key/request_id/issuer/time — nothing about origin or
permission. AbsentClaimToken.authorizes_construction existed but was never
read by safe_intake or commit_registration.

CORRECTION
  models.py       new ClaimProvenance; ClaimRecord.provenance;
                  CLAIMABLE_LOOKUP_OUTCOMES
  store.py        reserve_claim requires provenance; new bind_lookup_evidence
                  (write-once); commit_registration enforces the full binding
  search.py       identity_lookup builds provenance and binds the emitted
                  lookup result back onto the claim

Registration now proves all seven required facts:
  1 exact lookup result identity   lookup_result_id, write-once bound
  2 lookup evidence identity       lookup_evidence_hash of the emitted result
  3 request_id binding             provenance.request_id == presented id
  4 content-key binding            provenance key == recomputed candidate key
  5 governed policy binding        resolved against the governed registry
  6 lookup completeness + outcome  lookup_complete AND outcome in
                                   CLAIMABLE_LOOKUP_OUTCOMES
  7 construction authority         explicit, never inferred from 1-6

### R6 = NOT YET AVAILABLE — REGISTRATION IS FAIL-CLOSED

This is the material consequence and it is deliberate.

No code path in tracker_identity sets authorizes_construction=True. An ERA_1
structural absence is not a global absence: GLOBAL_CANONICAL_ABSENCE_PROVEN is
NO and SEMANTIC_UNIQUENESS is UNRESOLVED_NOT_CERTIFIED. Per the commission, no
construction-authorized outcome was invented to make a test pass. Therefore:

  ORDINARY CANONICAL REGISTRATION CANNOT CURRENTLY SUCCEED.

A fully valid candidate holding a real, fully provenance-bound governed claim
reaches the terminal gate and is refused with CLAIM_NOT_CONSTRUCTION_AUTHORIZED.
Nothing is written. test_R6 asserts this by scanning the package source and
FAILS the moment any construction-authorized path is introduced — which is
exactly when Manager must re-decide.

### ORDERING DECISION — AUTHORITY GATE IS LAST

The construction-authority check sits AFTER claim existence/active/binding and
after the duplicate and canonical-key checks, immediately before mutation.

Rationale: every upstream control stays independently observable instead of
being masked by a blanket authority refusal. Expiry still reports
CLAIM_NOT_ACTIVE, a duplicate still reports IDENTITY_APPEARED_SINCE_CLAIM, a
canonical collision still reports CANONICAL_KEY_ALREADY_REGISTERED. Nothing is
mutated before the gate, so the ordering costs no safety and preserves
auditability. Raised explicitly because it is a judgement call.

### PROPOSITIONS NOW UNVERIFIABLE END-TO-END

Reported rather than quietly dropped. Fail-closed registration makes these
unreachable; the tests were re-pointed at the reachable, safety-relevant half:

  claim consumption ON SUCCESS        was test_E_success_consumes_exactly_its_
                                      own_claim. Now proves the converse: a
                                      refused registration consumes nothing.
  stale failure AFTER a successful
  first registration                  was test_stale_failure_does_not_mutate_
                                      store. Now proves non-mutation at the
                                      authority gate.
  written-row era assignment          era binding now asserted via
                                      result.assigned_era_id, which IS returned
                                      on refusal.
  end-to-end double registration      canonical-key control still fully
                                      exercised via the import path plus a
                                      valid claim.

These become verifiable again the moment a governed construction order exists.

## M-1R — REGISTRY CONTAINER WAS MUTABLE

Manager finding CONFIRMED. Entries were immutable after the A13 fix, but
GOVERNED_SEARCH_POLICIES was an ordinary exported dict: a caller could replace,
delete or insert entries at runtime.

CORRECTION: the container is now MappingProxyType over a private _BUILT dict,
built and validated at import. New versions arrive by editing _ENTRIES in
source, never by mutating a running process. Added
resolve_governed_search_policy_binding() for callers that retained only the
(id, version, hash) triple, such as a claim's provenance.

## SECOND-PASS ATTACK — RE-ATTACK ROUND

10 probes. First run: 8 blocked, 2 bypassed. After correction: 9 blocked, 1
residual (the pre-existing A14).

  B1  direct reserve_claim, no provenance      CLAIM_PROVENANCE_REQUIRED
  B2  forged provenance, ungoverned policy     CLAIM_PROVENANCE_POLICY_NOT_GOVERNED
  B3  forged CONSTRUCTION-AUTHORIZED provenance  *** BYPASSED, then CLOSED ***
  B4  re-binding evidence on a governed claim  CLAIM_LOOKUP_EVIDENCE_ALREADY_BOUND
  B5  governed claim redeemed at registration  CLAIM_NOT_CONSTRUCTION_AUTHORIZED
  B6  registry insertion                       TypeError
  B7  registry deletion                        TypeError
  B8  entry permitted_exclusions mutation      TypeError
  B9  NEAR_MATCH issues no claim               no token, no claim persisted
  B10 store.add() ungated                      RESIDUAL — pre-existing A14

### B3 — A COMPLETE BYPASS FOUND AND CLOSED IN THIS ROUND

The first correction was NOT sufficient. A search-policy binding is PUBLIC
knowledge, so presenting one proves nothing about authority. A caller could:
  1 forge a ClaimProvenance with a correct governed policy binding and
    authorizes_construction=True;
  2 reserve the claim — accepted, because the binding checked out;
  3 self-call bind_lookup_evidence with fabricated ids — accepted;
  4 call commit_registration — SUCCEEDED, rows=1.

Measured, not theorised: the probe registered a row.

FIX: reserve_claim now refuses ANY provenance asserting
authorizes_construction=True — CONSTRUCTION_AUTHORITY_NOT_SELF_ASSERTABLE. The
governed path issues False, so a True arriving at reservation was authored by
the caller. That single fence is the designated replacement point: when a
governed construction ORDER exists, authority gets verified against that order
there, never taken on the caller's word. Pinned by test_R5c.

## NEGATIVE CONTROLS ADDED

  R1  direct reserve_claim + intake                     FAIL   PASS
  R2  direct reserve_claim + direct commit_registration FAIL   PASS
  R3  claim from INCOMPLETE_LOOKUP                      FAIL   PASS
  R4  Era-1 absence claim, authorizes_construction=False FAIL  PASS
  R5  fabricated lookup-result/evidence binding         FAIL   PASS
  R5b evidence binding is write-once                    FAIL   PASS
  R5c construction authority self-assertion (B3)        FAIL   PASS
  R6  construction-authorized path                      NOT YET AVAILABLE,
                                                        asserted by source scan
  R7  assignment to GOVERNED_SEARCH_POLICIES            FAIL   PASS
  R8  deletion                                          FAIL   PASS
  R9  insertion of rogue version                        FAIL   PASS
  R10 governed V1 remains usable                               PASS
  R11 mandatory-scope defence survives a rogue entry           PASS

## TESTS AFTER CORRECTION

TARGETED  = <PY> -m unittest tests.test_identity_surface   -> Ran 69 — OK
FULL      = <PY> -m unittest discover -s tests             -> Ran 201 — OK
  TOTAL=201 PASSED=201 FAILED=0 ERRORS=0 SKIPPED=0 XFAILED=0
BASELINE at BASE_SHA was 155 — OK. No baseline test deleted.

MUTATION SWEEP — every guard broken deliberately in a scratch copy:
  M1 CLAIM_REQUEST_ID_REQUIRED                -> 4 failures
  M2 governed-policy binding                  -> 3 failures
  M3 claim gate (commit_registration)         -> 1 failure
  M4 MANDATORY_SCOPE_NOT_SEARCHED             -> 4 failures
  M5 CLAIM_NOT_CONSTRUCTION_AUTHORIZED        -> 7 failures
  M6 CLAIM_PROVENANCE_REQUIRED                -> 2 errors
  M7 lookup-evidence binding required         -> 1 failure
  M8 registry container frozen                -> 24 failures, 15 errors
  M9 self-assert authority fence (B3)         -> 1 failure
All nine caught.

## CHANGED EXISTING TESTS — CORRECTION ROUND

 TEST_NAME = test_E_success_consumes_exactly_its_own_claim
             -> test_E_fail_closed_registration_consumes_no_claim
 OLD = successful registration consumes exactly its own claim.
 NEW = a registration refused at the authority gate consumes NOTHING and leaves
       an unrelated worker's claim ACTIVE.
 WHY = fixture invalid, not unsafe: consumption-on-success is unreachable while
       registration is fail-closed. The converse is the safety-relevant half.

 TEST_NAME = test_stale_failure_does_not_mutate_store
             -> test_refused_intake_does_not_mutate_store
 OLD = a stale failure after a successful first registration mutates nothing.
 NEW = a valid candidate holding a real governed claim writes nothing.
 WHY = fixture invalid: the first registration can no longer succeed. The
       non-mutation proposition is preserved.

 TEST_NAME = test_A_stalled_worker_with_expired_claim_cannot_register
 OLD = B registers, A's expired claim then fails.
 NEW = neither registers; B fails at the AUTHORITY gate, A fails earlier on
       CLAIM_NOT_ACTIVE. Asserted as different errors.
 WHY = fixture invalid. The ABA control is strengthened, not weakened: it now
       proves expiry fires independently of the authority gate.

 TEST_NAME = test_B_two_workers_same_content_key_cannot_both_register
 OLD = two direct reserve_claim calls; one registers.
 NEW = two governed lookups; the second gets NO claim (PENDING_CLAIM_EXISTS);
       neither registers, for different reasons.
 WHY = fixture invalid: reserve_claim no longer mints claims on demand.

 TEST_NAME = test_same_canonical_key_cannot_be_registered_twice
 OLD = first identity registered via intake.
 NEW = first identity placed by the governed import path with unrelated
       content; the canonical-key check still refuses a valid claim.
 WHY = fixture invalid. The canonical-key control remains fully exercised.
       Content deliberately made unrelated so the claimant's lookup is not
       routed to related-version review instead.

 TEST_NAME = test_safe_intake_assigns_era_only_from_active_boundary
 TEST_NAME = test_candidate_cannot_supply_or_override_era
 OLD = asserted era on the written row / returned identity.
 NEW = asserted via result.assigned_era_id, which IS returned on refusal.
 WHY = fixture invalid; proposition unchanged.

 TEST_NAME = NC05, NC06, NC07, NC08, NC22, NC23, and the claim_for helpers in
             test_safe_intake_era and test_registration_atomicity
 OLD = obtained claims by calling store.reserve_claim directly.
 NEW = obtain claims through a real governed identity_lookup.
 WHY = fixture invalid, and the invalidity IS the defect: direct reservation
       was the C-1R bypass. NC22 and NC23 additionally now assert that expiry
       and duplicate detection fire BEFORE the authority gate.

## COUNTS — CORRECTION ROUND

NEW_CRITICAL_COUNT = 1   (B3, found by this round's own second pass, CLOSED)
NEW_HIGH_COUNT     = 0
NEW_MEDIUM_COUNT   = 0   (A14 unchanged and still open, counted in round 1)
NEW_LOW_COUNT      = 0
ARCHITECTURE_REOPEN_REQUIRED = NO
FROZEN_TRACKER_CORE_REOPENED = NO

## RESIDUAL — UNCHANGED, NOT TOUCHED THIS ROUND

A14 / B10 store.add() and store.extend() remain un-claim-gated.
importer.py:365 writes through target_store.extend(). Left exactly as reported,
per instruction. Still recommended for its own bounded segment.

## FENCES — STILL UNCHANGED

GLOBAL_CANONICAL_ABSENCE_PROVEN = NO
ALGEBRAIC_EQUIVALENCE_IMPLEMENTED = NO
ALGEBRAIC_EQUIVALENCE_VALIDATED = NO
SEMANTIC_UNIQUENESS = UNRESOLVED_NOT_CERTIFIED
CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
IDENTITY_LOOKUP_READY_FOR_GOLD = NO
FEATURE_ID_CREATION_READY_FOR_MANAGER_DECISION = NO
CANONICAL_TRACKER_FEATURE_ID = NOT ASSIGNED
FEATURE_ID_CREATED = NO   FEATURE_VERSION_CREATED = NO
TRACKER_REGISTRY_ROW_CREATED = NO
GOLD_FEATURE_ID_CREATION_AUTHORIZED = NO
GOLD_ADMITTED = YES (unchanged by this patch)
FW_EXECUTION = NO  ML_TRAINING = NO  TYPE_2 = NO  PRODUCTION = NO

TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES
PR_CREATED = NO   MERGED = NO

DO NOT MERGE.
CODER FINDING != SALIX DECISION
TEST PASS != GOVERNANCE CLOSURE
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE

---

# AUTHORITY ISSUANCE CORRECTION — DC-GOLD-ID-GATE-AUTHORITY-ISSUANCE-001

APPENDED. Everything above stands as written at ba72b78 / a3d4879 and is
preserved for audit.

BASE_FOR_THIS_CORRECTION = a3d48797e3c7c7f5e6fc27ae3752d4b65d57acfd
No prior commit was amended, squashed or rebased.

DESIGN RULE APPLIED: AUTHORITY_MUST_BE_ISSUED_OR_RESOLVED_BY_ITS_OWNER.
CALLER_PRESENTED_PROPERTIES_ARE_NOT AUTHORITY.

## ALL THREE REVIEW_CODER DEFECTS REPRODUCED FIRST

Executed against a3d4879 before any edit. Not taken on report.

  D1  pr._BUILT[("rogue","1")]="INJECTED" -> GOVERNED_SEARCH_POLICIES returned
      'INJECTED'. The exported proxy was a VIEW over a live module dict.
  D2  hand-built ClaimProvenance + public governed policy binding + invented
      normalizer ("totally.made.up"@99) -> reserve_claim ACCEPTED it;
      bind_lookup_evidence ACCEPTED 'FABRICATED-RESULT'/'FABRICATED-HASH';
      claim reported fully bound. No identity_lookup was ever called.
  D3  an arbitrary normalizer identity passed completeness, as every existing
      test using "safe-intake"/"import-ctl" normalizers demonstrates.

## DEFECT 1 — REGISTRY BACKING MAP

Both registries are now built by a function whose dict is FUNCTION-LOCAL and
never becomes a module attribute. Only the read-only view escapes. `_BUILT` is
gone; underscore naming is not treated as access control anywhere.

Resolvers no longer trust membership. `_entry_or_errors()` RECOMPUTES each
entry's integrity (mandatory scope coverage, derived hash, equivalence-class
support) on every use, so an entry that reached the registry by any route is
still refused if it does not satisfy the governed rules.

REGISTRY_BACKING_MUTATION_POSSIBLE = NO (through any ordinary module surface)

Measured honestly: a read-only mapping still holds a backing dict that
gc.get_referents() can reach. That is outside the stated threat model, and the
control does not depend on it being unreachable — tests A6 and N5 install a
rogue entry BY THAT ROUTE and prove the integrity recheck still refuses it, the
lookup still returns INCOMPLETE_LOOKUP, and no claim is issued.

## DEFECT 2 — PROVENANCE WAS CALLER-FORGEABLE. FLOW INVERTED.

reserve_claim no longer has a `provenance` parameter. It is now store-owned
ISSUANCE: the caller supplies only what it wants looked up, and the store
establishes every fact that could confer authority:

  * search policy must resolve against the governed registry;
  * normalizer must resolve against the governed registry;
  * every governed searched scope must be proven reachable IN THIS STORE;
  * ABSENCE IS RE-DERIVED over the store's own records — lookup_complete and
    the outcome are facts the store established, never assertions it accepted;
  * the store then CONSTRUCTS the provenance, including a store-generated
    lookup_result_id and an issuance evidence hash over exactly those verified
    facts.

bind_lookup_evidence was REMOVED, not tightened. There is nothing left to bind:
both identifiers are store-generated and no public entry point accepts either.

identity_lookup now emits the STORE-generated lookup_result_id, so the result
and the claim refer to the same issuance. identity_lookup has no more power to
mint a claim than any other caller.

A store-owned issuance ledger (`_issued_claim_ids`) records what this store
actually issued. A structurally perfect forged ClaimRecord appended to
`store.claims` — every governed binding resolving, completeness_errors() == ()
— is refused at registration with CLAIM_NOT_ISSUED_BY_THIS_STORE. That is the
executable distinction between REAL_LOOKUP_ISSUED_CLAIM and
CALLER_CONSTRUCTED_LOOKALIKE. No secret is involved: the values are visible,
they are simply not settable through any reachable entry point.

CALLER_CAN_CONSTRUCT_AUTHORITATIVE_PROVENANCE = NO
CALLER_CAN_FABRICATE_LOOKUP_EVIDENCE_BINDING  = NO
REAL_LOOKUP_ISSUED_CLAIM_DISTINGUISHABLE      = YES

## DEFECT 3 — GOVERNED NORMALIZER AUTHORITY

New module tracker_identity/normalizer_registry.py, mirroring the policy
registry: versioned Tracker-owned entries, derived hash, function-local build,
read-only container, integrity revalidation on every resolve.

GOVERNED V1: tracker.identity.normalizer @ 1, equivalence classes exactly
("EXACT_STRUCTURAL_IDENTITY",). A registry entry claiming an unsupported class
is refused by its own integrity rules, so equivalence capability cannot be
widened by adding a registry entry.

Bound at both layers: identity_lookup resolves the presented normalizer, and
the store re-resolves independently at issuance. Both layers are separately
pinned (N2b / N2c) because under mutation they masked each other.

NORMALIZER_BINDING_GOVERNED = YES
SUPPORTED_EQUIVALENCE_CLASSES unchanged.
ALGEBRAIC_EQUIVALENCE remains NOT IMPLEMENTED / NOT VALIDATED.

## CONSTRUCTION AUTHORITY — UNCHANGED AND STILL ABSENT

CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO

No code path sets authorizes_construction. reserve_claim has no parameter for
it, so it cannot even be requested. Registration remains FAIL-CLOSED: a genuine
store-issued claim reaches the terminal gate and is refused with
CLAIM_NOT_CONSTRUCTION_AUTHORIZED, writing nothing. test_R6 scans package
source and fails the moment such a path appears.

Authority-gate-last ordering retained per Manager acceptance. Verified: no
registry or creation mutation occurs before it, each earlier control remains
independently observable with its own error code, and a refusal at the gate
consumes no claim (the claim stays ACTIVE).

## TESTS

TARGETED = <PY> -m unittest tests.test_identity_surface  -> Ran 84 — OK
FULL     = <PY> -m unittest discover -s tests            -> Ran 216 — OK
  TOTAL=216 PASSED=216 FAILED=0 ERRORS=0 SKIPPED=0
BASELINE at BASE_SHA was 155 — OK. No baseline test deleted.

### MUTATION SWEEP — INCLUDING WHAT SURVIVED

First sweep: 12 guards mutated, 7 killed, 5 SURVIVED. Reported rather than
hidden, because a guard no test can kill is not evidence.

  G2  store normalizer re-resolution   SURVIVED -> now killed (test N2c)
  G9  lookup normalizer binding        SURVIVED -> now killed (test N2b)
  G11 normalizer entry integrity       SURVIVED -> now killed (test N5)
  G6  store_issued provenance check    SURVIVES — see below
  G7  commit-time normalizer binding   SURVIVES — see below

G2 and G9 masked each other: removing either alone still produced
INCOMPLETE_LOOKUP via the other layer. The new tests assert the specific
layer's error code, so each is now independently pinned.

G6 and G7 remain unkillable BY DESIGN and this is stated plainly: they are
redundant defence-in-depth at the commit boundary. Any claim in the issuance
ledger necessarily carries store-issued provenance with a governed normalizer
binding, because the store built it — so no public API can produce a claim that
passes the ledger check and fails these two. They are retained as cheap
insurance against a future change that separates those facts. They are NOT
counted as evidence of anything.

Killed mutants: G1 policy re-resolution, G3 scope reachability, G4 absence
re-derivation, G5 issuance ledger, G8 construction-authority gate, G10 policy
entry integrity, G12 provenance governed bindings, plus G2/G9/G11.

## SECOND-PASS ADVERSARIAL ATTACK

20 probes. 18 blocked, 2 outside this task's scope.

REVIEW_CODER's exact chain, step by step:
  RC1 hand-built provenance passes completeness  BLOCKED (normalizer not governed)
  RC2 reserve_claim accepts caller provenance    BLOCKED (TypeError, no parameter)
  RC3 public evidence binder exists              BLOCKED (removed)
  RC4 strongest forgery — every governed binding
      resolving, completeness_errors() == () —
      injected into store.claims and redeemed    BLOCKED
      CLAIM_NOT_ISSUED_BY_THIS_STORE, rows=0

Registry sweep: no module-level dict in either registry; no _BUILT; insert,
delete, replace, clear and update all refused (AttributeError/TypeError).

Normalizer: self-hashed ungoverned refused; widened equivalence classes refused.
Genuine path: store-built claim, result id matches, authorizes_construction False.
Store re-derivation: CLAIM_CONTENT_IDENTITY_ALREADY_PRESENT when the store's own
records contradict the requested absence.

Not blocked:
  REG4 gc.get_referents reaches the backing dict — outside the stated threat
       model, and neutralised in depth by the integrity recheck (A6, N5).
  A14  store.add()/store.extend() ungated — OUT OF SCOPE, untouched by
       instruction. importer.py was not modified.

IMPORT_PATH_AUTHORITY_RESIDUAL = OPEN

## COUNTS

NEW_CRITICAL_COUNT = 0
NEW_HIGH_COUNT     = 0
NEW_MEDIUM_COUNT   = 0
NEW_LOW_COUNT      = 1   (gc-reachable backing dict; outside threat model,
                          neutralised in depth, reported not hidden)
ARCHITECTURE_REOPEN_REQUIRED = NO

## FENCES — UNCHANGED

GLOBAL_CANONICAL_ABSENCE_PROVEN = NO
SEMANTIC_UNIQUENESS = UNRESOLVED_NOT_CERTIFIED
ALGEBRAIC_EQUIVALENCE_IMPLEMENTED = NO
ALGEBRAIC_EQUIVALENCE_VALIDATED = NO
CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
IDENTITY_LOOKUP_READY_FOR_GOLD = NO
FEATURE_ID_CREATION_READY_FOR_MANAGER_DECISION = NO
CANONICAL_TRACKER_FEATURE_ID = NOT ASSIGNED
FEATURE_ID_CREATED = NO   FEATURE_VERSION_CREATED = NO
TRACKER_REGISTRY_ROW_CREATED = NO
GOLD_FEATURE_ID_CREATION_AUTHORIZED = NO
GOLD_ADMITTED = YES (unchanged by this patch)
FW_EXECUTION = NO  ML_TRAINING = NO  TYPE_2 = NO  PRODUCTION = NO

TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES
PUSH_REQUIRED = YES   PUSH_SUCCEEDED = NO   PR_CREATED = NO   MERGED = NO

DO NOT MERGE.
DESKTOP_CODER FINDING != REVIEW_CODER FINDING
DESKTOP_CODER TEST PASS != MANAGER ACCEPTANCE
CODER FINDING != SALIX DECISION
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE

---

# ISSUANCE AUTHENTICITY CORRECTION — DC-ISSUANCE-AUTHENTICITY-BINDING-003

APPENDED. Everything above stands as written and is preserved for audit.

FROM = DESKTOP_CODER
TASK_ID = DC-ISSUANCE-AUTHENTICITY-BINDING-003
BASE_FOR_CORRECTION = cd254ce1a498f650352f5e9e43aee6ab45b58222
IMPLEMENTATION_SHA  = 644b59facbb01c383729172f180593cec6ae0536
No prior commit was amended, squashed or rebased.

GOVERNED COMMISSION OPENED = YES
  Drive 1GSFdntr5YHg3qAI7EHRuM9Z29v3jANcmN58uZg-yZcs, read in full, read-only.
  CR-1, CR-2, the required security property, the 14 mandatory controls and
  the allowed-file list were taken from that document, not from the chat relay.

## CORRECTION TO MY OWN PRIOR RETURN

The previous section declared:
  CALLER_CAN_CONSTRUCT_AUTHORITATIVE_PROVENANCE = NO
  REAL_LOOKUP_ISSUED_CLAIM_DISTINGUISHABLE      = YES
Both were WRONG under ordinary object mutation, and the severity was CRITICAL,
not LOW. Reproduced at cd254ce before any edit:

  CR-1  planted synthetic ClaimRecord + store._issued_claim_ids.add(id)
        -> committed=True, rows=1
  CR-2  genuine claim; provenance replaced with authorizes_construction=True
        in the public claims list; its id still "issued"
        -> committed=True, rows=1

Both were full canonical row writes. The issuance ledger was a mutable set, and
the authority bit was read from a record the caller could replace.

## DESIGN — SMALLEST ROBUST OPTION

The keyed-MAC candidate was considered and NOT adopted. A MAC needs a signer the
store can call; in one process that signer is equally callable by caller code,
so a MAC alone would not close the defect — it would move it to the signer.

Adopted instead — no key, no MAC, no signer:

  * A per-store ledger held ONLY in a closure. It is never a store attribute
    and never a module-level container, so no container mutation reaches it.
  * For each claim it records an EXACT canonical snapshot of every bound fact
    — claim id, content key, request id, issuer, both timestamps, and the full
    provenance including the authority bit, policy and normalizer bindings,
    lookup result id and evidence hash — plus the authoritative lifecycle.
  * AUTHENTIC = current contents reproduce that snapshot exactly AND the
    lifecycle equals the ledger's.
  * Registration, validation, expiry, release and one-active-claim-per-key are
    all decided against the ledger. The public `claims` list is a display
    mirror only; anything a caller appends or replaces there is inert.
  * Exactly ONE writer, and it accepts only raw lookup inputs. It re-derives
    every authority-bearing fact and generates the claim id, lookup result id,
    both timestamps and the evidence hash itself. No function accepts a
    caller-built record or provenance to seal. Invoking the writer directly is
    therefore indistinguishable from a legitimate issuance and cannot mint
    authority.
  * `_issued_claim_ids` REMOVED. Underscore naming and id membership are not
    part of the security argument anywhere.
  * Ledgers are keyed per store by object identity and released when the store
    is collected, so a claim is unknown to every store but its issuer.

## STATED BOUNDARY — MEASURED, NOT ASSUMED

DEFENDED (every probe below executed; all refused, rows=0):
  ordinary mutation of any caller-reachable container or field; in-place
  mutation of a frozen record or provenance via object.__setattr__; subclassed
  record/provenance lookalikes; exact copies gaining extra authority; cross-store
  replay into a fresh store, into copy.copy(store) and into
  dataclasses.replace(store); lifecycle revival; expiry extension.

NOT DEFENDED — and both were exercised, not assumed:
  CODE REPLACEMENT  rebinding store_module._authenticate_claim to a function
                    that always returns authentic      -> rows=1
  REFLECTION        walking fn.__closure__ reaches the ledger at closure depth
                    2; rewriting its snapshot           -> rows=1

No pure in-process Python design can prevent either. Neither is claimed.

A first probe reported reflection as "blocked" because it looked only one
closure level deep. That was a weakness in the probe, not protection. It was
re-run as a recursive walk before anything was reported, and the corrected
result is the one given above.

Why module-function rebinding was not "hardened": any rebinding of the module
name could equally be done to the class method that calls it, so hardening one
level would only imply a protection that does not exist.

## MANDATORY NEGATIVE CONTROLS — ALL 14

  1  synthetic provenance + synthetic record cannot register         PASS  C01
  2  synthetic claim + EVERY caller-mutable container stuffed         PASS  C02
  3  genuine claim, provenance replaced to authority=True (CR-2)      PASS  C03
  4  post-issuance change of request id, content key, policy binding,
     normalizer binding, lookup result id, evidence binding,
     lifecycle state, release reason, authority bit, issuer, both
     timestamps, semantic uniqueness, outcome, completeness —
     every one invalidates authenticity                              PASS  C04
     + in-place frozen mutation (C04b), subclass lookalikes (C04c)
  5  copy / deepcopy / reconstruction gain no authority              PASS  C05
  6  Store A claim replay into Store B fails                         PASS  C06
     + copy.copy(store) and dataclasses.replace(store) (C06b)
  7  expired / released / consumed stay unusable                     PASS  C07
     + no revival via API (C07b), expiry cannot be extended (C07c)
  8  same claim cannot register twice                                PASS  C08b
     + one-active-claim survives mirror tampering (C08, C08c, C08d)
  9  direct commit without authentic issued claim fails              PASS  C09
     + planted lookalike cannot shadow a genuine claim (C09b)
  10 policy and normalizer integrity remain PASS                     PASS  C10
  11 construction-authorized path remains absent                     PASS  C11, C11b, R6
  12 import/direct-mutation residual OPEN, out of scope              PINNED C12
  13 mutation-test every new guard, report survivors                 DONE  below
  14 full regression, no safety assertion weakened                   PASS  below

Note on control 8: registration never succeeds today, so "cannot register
twice" is proven at the claim layer — a claim is consumed at most once, in the
ledger, and no copy can be presented afterwards.

## MUTATION RESULT

15 new authenticity guards mutated in a scratch copy, never in the repo.

First sweep: 12 killed, 3 SURVIVED.
  A8  reserve_claim pre-check uses ledger   SURVIVED -> killed by C08c
  A11 writer enforces one-active via ledger SURVIVED -> killed by C08d
  A15 consumption recorded in ledger        SURVIVES

A8 and A11 masked each other: each is a separate ledger-backed layer, so
breaking one alone was still caught by the other. Each is now pinned
independently.

A15 remains UNKILLABLE BY CONSTRUCTION and is stated plainly: it is the
consumption step after a successful registration, and registration never
succeeds because no construction authority exists. It is not counted as
evidence of anything. It becomes testable the moment a governed construction
order exists.

FINAL = 15 guards, 14 killed, 1 survivor (A15, unreachable).

Killed: A1 record type, A2 not-issued, A3 provenance type, A4 snapshot
equality, A5 lifecycle equality, A6 scan past lookalikes, A7 commit
authenticates, A8, A9 expiry from ledger, A10 monotonic terminate, A11,
A12 snapshot covers provenance, A13 covers expires_ts, A14 covers request_id.

## TESTS

TARGETED = <PY> -m unittest tests.test_identity_surface  -> Ran 106 — OK
FULL     = <PY> -m unittest discover -s tests            -> Ran 238 — OK
  TOTAL=238 PASSED=238 FAILED=0 ERRORS=0 SKIPPED=0
Baseline at BASE_SHA was 155. No test deleted. No safety assertion weakened.
The one changed existing assertion (P6/P7) now checks authenticity through the
public claim_authenticity() instead of the removed set — strictly stronger.

## CHANGED FILES

  tracker_identity/store.py
  tests/test_identity_surface.py
  coder_returns/C-GOLD-ID-GATE-HARDENING-001.md   (this append)

Both code files are on the commission's allowed list. models.py, search.py,
intake.py, both registries, __init__.py and all other tests were not modified.
test_pre_id_content_identity.py was not modified; its reserve_claim
introspection invariants are preserved. population/**, .github/**, CLAUDE.md
and importer.py untouched.

## OBSERVATIONS — NOT FIXED, OUT OF SCOPE

  * reserve_claim still accepts a caller ttl_seconds. It affects claim
    lifetime only, never authority, and pre-dates this task.
  * store._clock is a caller-settable field by design (deterministic tests).
    A caller controlling it controls expiry. Claims confer no authority, so
    this cannot write a row, but it is a real lever and is recorded here.

## RETURN

CR1_CLOSED = YES
CR2_CLOSED = YES
CROSS_STORE_REPLAY_BLOCKED = YES
POST_ISSUANCE_CONTENT_MUTATION_BLOCKED = YES  (data mutation; see boundary)
SYNTHETIC_CLAIM_ACCEPTED = NO
CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
IMPORT_PATH_AUTHORITY_RESIDUAL = OPEN
FULL_TEST_RESULT = Ran 238 tests — OK
MUTATION_RESULT = 15 guards, 14 killed, 1 surviving (A15, unreachable by construction)

NEW_CRITICAL_COUNT = 0
NEW_HIGH_COUNT     = 0
NEW_MEDIUM_COUNT   = 0
NEW_LOW_COUNT      = 0
PRIOR_RETURN_CORRECTED = YES  (cd254ce authenticity claims were wrong; CRITICAL)

TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES
PR_CREATED = NO   MERGED = NO

GLOBAL_CANONICAL_ABSENCE_PROVEN = NO
SEMANTIC_UNIQUENESS = UNRESOLVED_NOT_CERTIFIED
ALGEBRAIC_EQUIVALENCE_VALIDATED = NO
FEATURE_ID_CREATED = NO   FEATURE_VERSION_CREATED = NO
TRACKER_REGISTRY_ROW_CREATED = NO

DO NOT MERGE.
DESKTOP_CODER TEST PASS != MANAGER ACCEPTANCE
CODER FINDING != SALIX DECISION
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE

---

# WEAKREF + STORE-OWNED TIME CORRECTION — DC-WEAKREF-TIME-HARDENING-004

APPENDED. Everything above is preserved as written.

FROM = DESKTOP_CODER
TASK_ID = DC-WEAKREF-TIME-HARDENING-004
BASE_FOR_CORRECTION = aaec2c49af0f339752a4095c9fdd9e5d39f9ab49
IMPLEMENTATION_PARENT = 644b59facbb01c383729172f180593cec6ae0536 (verified)
IMPLEMENTATION_SHA  = 6edc67ee540b0e73d678607f5bc8b723e667b6c2
No prior commit was amended, squashed or rebased.

GOVERNED COMMISSION OPENED = YES
  Drive 1x2xlGrA7NeyeRri6OAgAv6CAkvfnq2Cm_B0uWgzdSIg, read in full, read-only.

## CORRECTION TO MY OWN PRIOR RETURN

At 644b59f I wrote that the ledger was "never a store attribute and never a
module attribute, so no ordinary container mutation can reach it". That was
FALSE. Cleanup was registered as weakref.finalize(store, ledgers.pop, key).
`ledgers.pop` is a bound method; its __self__ is the ledger; and
weakref.finalize publishes its callback through the public peek() API.

## ALL DEFECTS REPRODUCED AT BASE BEFORE ANY EDIT

  CR-R1     fin.peek()[1].__self__ IS the ledger dict. Snapshot rewritten
            through it, no __closure__ used -> committed=True, rows=1
  MR-TIME-1 _expire_due_claims(store, "2999-...") force-expired a live claim
  MR-TIME-2 far-future injected clock, then removed -> claim expires_ts
            2999-01-01T00:15, still active on the real clock
            ttl_seconds=-5 -> claim created already expired
  LR-TIME-1 ttl_seconds=10**12 -> UNHANDLED OverflowError

## CORRECTIONS

1 CR-R1. Cleanup is now `_drop(key)`, a plain closure-local function taking
  only the integer store id. Verified via public peek(): exactly one finalizer
  per store, func.__self__ is None, args == (id(store),), and no dict/list/set
  is reachable from func, args or kwargs. The ledger is not merely renamed or
  hidden: nothing in the registry owns or contains it.

2 STORE-OWNED TIME. No method on the store and no callable in the store module
  accepts a time parameter (asserted by signature scan across both, NC-W5).
  `_expire_due`, `_active_claim_at_locked` and `_expire_due_claims` lost their
  now_iso parameters. Liveness at validation and registration reads the ledger
  at store time, not a record predicate given a supplied timestamp.

  The store derives a per-store monotonic effective time, held in the closure:

      effective = max(wall clock, injected test clock, last + real elapsed)

  It never decreases, never freezes, never runs slower than real time.

  Two simpler designs were rejected on evidence, not preference:
    * anchoring expiry to the wall clock alone breaks deterministic tests that
      advance the clock and then issue — new claims are born expired;
    * a plain high-water mark lets one far-future jump FREEZE effective time,
      so claims outlive their TTL in real time — the MR-TIME-2 defect again.

3 TTL. Bounded to [CLAIM_TTL_MIN_SECONDS=1, CLAIM_TTL_MAX_SECONDS=governed
  default 900]. Structured refusals: CLAIM_TTL_INVALID_TYPE (including bool,
  since True is an int), CLAIM_TTL_NOT_POSITIVE, CLAIM_TTL_EXCEEDS_GOVERNED_
  MAXIMUM. Nothing is silently clamped. Arithmetic near datetime.max saturates
  or returns CLAIM_EXPIRY_OVERFLOW; nothing raises. Enforced inside the single
  writer, so direct invocation is bounded too.

## EXACT SUPPORTED TEST-CLOCK BOUNDARY (NC-W9)

`store._clock` remains settable. It must: test_pre_id_content_identity.py,
which this commission does not authorise me to edit, assigns it after
construction in six tests. Its power is now bounded precisely:

  * it can only move store time FORWARD — earlier expiry, a liveness effect
    that release_claim() already grants any caller;
  * it cannot slow, freeze, rewind or extend any claim;
  * a past, naive, malformed or raising clock is IGNORED, not trusted;
  * it grants no construction authority (NC-W9b).

A far-future jump followed by removing the clock no longer extends anything:
NC-W6b proves this with REAL elapsed time — a 1-second claim issued under a
2999 clock dies after ~1.25 s of wall time once the clock is removed.

## MANDATORY NEGATIVE CONTROLS — ALL PASS

  NC-W1  finalize registry exposes no ledger via bound-method owner   W01, W01b
  NC-W2  synthetic claim + every store container stuffed -> unauthentic W02
  NC-W3  genuine provenance replacement rejected                       W03
  NC-W4  cross-store replay rejected                                   W04
  NC-W5  no store/module callable accepts caller-selected time         W05, W05b
  NC-W6  caller cannot extend lifetime (over-max TTL; real-time jump)  W06, W06b
  NC-W7  negative / zero TTL refused, no expired-at-birth claim        W07
  NC-W8  oversized / malformed TTL structured; datetime.max saturates  W08, W08b, W08c
  NC-W9  test clock forward-only, ignores past/naive/malformed/raising W09, W09a, W09c
         and grants no authority                                       W09b
  NC-W10 rewind cannot revive expired or released claims               W10
  NC-W11 one-active-claim-per-key intact                               W11
  NC-W12 construction-authorized path absent                           W12, R6
  NC-W13 policy + normalizer registries PASS                           W13
  NC-W14 import/direct-mutation residual OPEN and untouched            W14, C12

## TESTS

PYTHON = 3.12.10  (C:\Users\salla\AppData\Local\Programs\Python\Python312\python.exe)
TARGETED = <PY> -m unittest tests.test_identity_surface  -> Ran 124 — OK
FULL     = <PY> -m unittest discover -s tests            -> Ran 256 — OK
  TOTAL=256 PASSED=256 FAILED=0 ERRORS=0 SKIPPED=0
Suite time rose to ~1.4 s. That is NC-W6b's deliberate real-time sleep, the
only way to prove non-extension without trusting the clock under test.
Baseline at BASE_SHA was 155. No test deleted. No safety assertion weakened.

## MUTATION RESULT

NEW GUARDS (this task) — 17 mutated.
  First sweep: 14 killed, 3 SURVIVED:
    T4  naive injected datetime accepted     SURVIVED -> killed by W09a
    T14 negative monotonic elapsed allowed   SURVIVED -> killed by W09c
    T15 elapsed-add overflow unguarded       SURVIVED -> killed by W08c
  T4 survived because datetime.astimezone() silently reinterprets a naive
  value as LOCAL time instead of raising, so the mutant's jump still looked
  monotonic. T14 and T15 are unreachable with a real clock (monotonic time
  never regresses; two fast calls can see zero elapsed on Windows' ~15 ms
  tick), so both are driven deterministically by patching the store's clock
  source with unittest.mock.
  FINAL: 17 killed, 0 surviving.

PRIOR AUTHENTICITY GUARDS — regression sweep on the new code, 14 mutated.
  The ledger was restructured in this task, so every prior guard was re-run.
  A1-A8, A10-A14: all still KILLED.
  A9 superseded by T12 (expiry from the ledger), killed.
  A15 consumption recorded in the ledger at commit: SURVIVES.

COMBINED = 31 guards mutated, 30 killed, 1 surviving.

ALL SURVIVING MUTANTS:
  A15 — the claim-consumption step after a SUCCESSFUL registration. It cannot
  be reached: registration never succeeds, because no construction authority
  exists. Unchanged from the previous round, unkillable by construction, and
  not counted as evidence. It becomes testable when a governed construction
  order exists.

## STATED BOUNDARY — UNCHANGED, RESTATED

DEFENDED: ordinary mutation of any caller-reachable DATA, and now the public
weakref registry route.
NOT DEFENDED, and not claimed: CODE replacement (rebinding store methods or
module functions) and reflection on closure cells (fn.__closure__), gc,
ctypes. `_drop` still closes over the state dict — reachable through
_drop.__closure__, which is reflection, the stated boundary.

## CHANGED FILES

  tracker_identity/store.py
  tests/test_identity_surface.py
  coder_returns/C-GOLD-ID-GATE-HARDENING-001.md   (this append)

All three are on the allowed list. models.py, test_registration_atomicity.py
and test_safe_intake_era.py were NOT needed and were not modified.
test_pre_id_content_identity.py (not allowed this round) was not modified, and
its six post-construction `_clock` assignments still pass. population/**,
.github/**, CLAUDE.md, importer.py untouched.

## RETURN

CR_R1_CLOSED = YES
STORE_OWNED_TIME_RESTORED = YES
CALLER_SELECTED_TTL_BLOCKED = YES   (bounded to [1, governed default])
OVERFLOW_STRUCTURED_FAILURE = YES
CROSS_STORE_REPLAY_BLOCKED = YES
POST_ISSUANCE_CONTENT_MUTATION_BLOCKED = YES   (data mutation; see boundary)
CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
IMPORT_PATH_AUTHORITY_RESIDUAL = OPEN
FULL_TEST_RESULT = Ran 256 tests — OK (0 failed, 0 errors, 0 skipped)
MUTATION_RESULT = 31 guards, 30 killed, 1 surviving (A15, unreachable)
PRIOR_RETURN_CORRECTED = YES  (644b59f ledger-unreachability claim was false)
TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES
PR_CREATED = NO   MERGED = NO

DESKTOP_CODER TEST PASS != MANAGER ACCEPTANCE
REVIEW_CODER FINDING != MANAGER DECISION
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE
DO NOT MERGE.

---

# CLOCK ISOLATION + PUBLIC WEAKREF CORRECTION — DC-CLOCK-ISOLATION-WEAKREF-TEST-005

APPENDED. Everything above is preserved as written.

FROM = DESKTOP_CODER — IMPLEMENTATION ENGINEER
TASK_ID = DC-CLOCK-ISOLATION-WEAKREF-TEST-005
BASE_FOR_CORRECTION = 259149f8d979132858d164f7810789f1c14f4ea9
IMPLEMENTATION_SHA  = 90f31ce050d2683484212cd9809089b035138b34
No prior commit was amended, squashed or rebased.

GOVERNED COMMISSION OPENED = YES
  Drive 15PPVvRR4oyGkLyAqdSv6wx78WH0zWxr6cV9ZjD6YzE4, read in full, read-only.

## WHAT THE DC004 CHALLENGE ESTABLISHED, AND WHAT CHANGED

The DC004 challenge return (read-only) corrected two overstated DC004 fields:
STORE_OWNED_TIME_RESTORED was QUALIFIED, not YES; CALLER_SELECTED_TTL_BLOCKED
was NO, not YES. This task closes both in the strong sense.

## 1. PUBLIC WEAKREF ROUTE — NOW PERMANENTLY TESTED

test_NC01_NC02_exact_public_weakref_route uses documented public APIs only:
    weakref.getweakrefs(store)   -> ref
    ref.__callback__             -> weakref.finalize
    finalize.peek()              -> (obj, func, args, kwargs)
    func.__self__                -> asserted None
weakref.finalize._registry is not used anywhere in that test. It asserts one
cleanup finalizer, no bound-method owner, no mutable container reachable from
func/args/kwargs, args == (id(store),), and that the former forgery chain now
fails with CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE and writes nothing.

Executed evidence from the DC004 challenge on the same route:
  BASE aaec2c4    func=dict.pop   __self__=dict (the ledger)  forgery rows=1
  CURRENT         func=_drop      __self__=None               ledger not reached

## 2. PRODUCTION CLOCK AUTHORITY REMOVED

The `_clock` dataclass field is deleted. It was init=True, so the production
constructor accepted it, and it was an ordinary field. Through it a caller
could push authoritative time, issued_ts, expires_ts and last_effective
arbitrarily forward; the poisoning outlived its removal for the life of the
store, and near datetime.max forced permanent CLAIM_EXPIRY_OVERFLOW refusals.

Store time now derives ONLY from two dedicated source functions:
    _wall_now()       real UTC wall clock
    _monotonic_now()  real monotonic clock
    effective = max(_wall_now(), last_effective + monotonic elapsed)
No constructor argument, store field, flag, environment variable or API
parameter reaches either.

## 3. EXACT TEST-ONLY MECHANISM

Deterministic tests replace those source FUNCTIONS with unittest.mock via
install_test_clock() / patch_store_source(), restored by addCleanup. This is
test instrumentation by code replacement — the same class as rebinding any
store method, which has been outside the stated boundary for production
callers since DC-003. It is not production data and not an API.

NC-08 proves it both ways in one test: setting fifteen clock-like attributes on
a store has NO effect (time stays < 2100); replacing the source function DOES
(time == 2999). Data cannot steer time; only code replacement can.

## 4. STORE-OWNED LIFETIME

reserve_claim and _issue_claim no longer accept any lifetime. Passing
ttl_seconds, issued_ts or expires_ts to either raises TypeError. Every claim
takes _governed_claim_ttl_seconds() (the governed default, 900 s), and
expires - issued is exactly that. The CLAIM_TTL_* structured refusals now guard
the store's OWN policy source — defence in depth in case it is ever mis-edited
or mis-patched — rather than a caller input.

## 5. MODULE HELPERS ALIGNED TO THE PUBLIC BOUNDARY

  _terminate_claim   REMOVED. It let a caller mark a live claim EXPIRED with
                     any reason (proven in the DC004 challenge).
  _release_claim     exactly release_claim(): ACTIVE -> RELEASED, non-blank,
                     non-reserved reason only.
  _consume_claim     requires an authentic, ACTIVE, construction-authorized
                     claim whose identity is really in the records under the
                     claim's content key. No construction authority exists, so
                     it always refuses — even with the identity planted by the
                     A14 route (NC-13b).
  _issue_claim       no time and no lifetime inputs; equivalent to reserve_claim.
  _transaction_time  no parameter; records only real time.
  _expire_due_claims no parameter; applies only expiry already due.

RESERVED_LIFECYCLE_REASONS = {TTL_EXPIRED, REGISTRATION_COMPLETED} are refused
at BOTH the public release_claim and _release_claim, so no caller can record
that a claim timed out or was consumed by a registration when it was not.
EXPIRED is assigned only by genuine store-time expiry: NC-13c calls every
exported store-first helper with EXPIRED-style arguments and the live claim
never becomes EXPIRED.

## 6. NARROW SCOPE EXPANSION — test_pre_id_content_identity.py

Exactly the six `store._clock = clock` lines were replaced with
`install_test_clock(self, clock)`, plus one test-only helper. Diff: +22 / -6.
Verified mechanically that no other line of that file changed. All 59 tests in
the file pass, including C2, C2b, C3 and the M-series expiry tests.

test_registration_atomicity.py was also required: its three `store._clock`
sites would otherwise have silently stopped steering time. Migrated the same
way. test_safe_intake_era.py was not needed and was not modified.

## MANDATORY NEGATIVE CONTROLS — ALL PASS

  NC-1  exact public weakref path permanently tested         NC01_NC02
  NC-2  former public route cannot obtain the ledger         NC01_NC02
  NC-3  constructor has no caller clock authority            NC03, NC03b
  NC-4  no caller-mutable store field controls time          NC04
  NC-5  reserve_claim cannot choose transaction timestamp    NC05_NC06_NC07
  NC-6  reserve_claim cannot choose issued_ts / expires_ts   NC05_NC06_NC07, NC06b
  NC-7  ordinary caller cannot choose TTL                    NC05_NC06_NC07, NC06b
  NC-8  test-only mechanism unreachable as data/API          NC08
  NC-9  expired / released claims cannot revive              NC09_to_NC12, W10
  NC-10 one-active-claim-per-key intact                      NC09_to_NC12, W11
  NC-11 cross-store replay blocked                           NC09_to_NC12
  NC-12 post-issuance content mutation blocked               NC09_to_NC12
  NC-13 _terminate_claim cannot falsify expiry/state         NC13, NC13b, NC13c
  NC-14 construction-authorized path absent                  NC14_NC15_NC16, R6
  NC-15 policy + normalizer registries PASS                  NC14_NC15_NC16
  NC-16 A14 OPEN and untouched                               NC14_NC15_NC16, C12
  NC-17 full regression + mutation testing                   below

## TESTS

PYTHON = 3.12.10
  targeted  <PY> -m unittest tests.test_identity_surface          Ran 131 — OK
  pre-ID    <PY> -m unittest tests.test_pre_id_content_identity   Ran 59  — OK
  full      <PY> -m unittest discover -s tests                    Ran 263 — OK
  TOTAL=263 PASSED=263 FAILED=0 ERRORS=0 SKIPPED=0
Baseline at BASE_SHA was 155. No test deleted. No safety assertion weakened.
The pre-ID file still holds exactly 59 tests.

Superseded 004 tests, each with its proposition preserved:
  W06  caller TTL over maximum     -> now NC05_NC06_NC07: no TTL input at all
  W06b far-future clock, removed   -> wall-clock step BACK cannot extend a
                                      claim; still measured in real time
  W07/W08 caller TTL bounds        -> bounds now guard the store's own policy
                                      source (W07_W08)
  W09/W09a injected-clock semantics-> removed: the injected clock no longer
                                      exists; replaced by NC03, NC04, NC08

## MUTATION RESULT

38 guards mutated in a scratch copy, never in the repo.

  DC-005 new guards       18 mutated, 13 killed, 5 surviving
  retained DC-004 time     7 mutated,  7 killed
  prior authenticity      13 mutated, 12 killed, 1 surviving

First sweep had 6 survivors. D3 (bypassing the _monotonic_now source) was a
REAL TEST GAP: existing tests asserted only inequalities that still held on
the real monotonic clock. test_NC03b now pins an exact 10,000 s advance from
the dedicated source; D3 is killed.

COMBINED = 38 mutated, 33 killed, 5 surviving.

ALL SURVIVING MUTANTS — every one is in the registration-consumption path:
  D10 _consume_claim: drop ACTIVE check
  D11 _consume_claim: drop authenticity check
  D12 _consume_claim: drop identity-in-records check
  D13 _consume_claim: drop content-key match
  A15 commit_registration: skip consumption

These are UNKILLABLE BY CONSTRUCTION, and I state it plainly rather than
counting them as evidence. The authority check in _consume_claim (D9) is killed
and always refuses, because no construction authority exists. So every consume
returns False whatever the other guards do. Reordering does not help: while
authority always refuses, no scenario can make any other guard decisive. A15
is the same path at commit. They become testable when a governed construction
order exists.

## STATED BOUNDARY

DEFENDED: mutation of any caller-reachable DATA; the public weakref route;
every production time, issuance-timestamp and lifetime input.
NOT DEFENDED, not claimed: CODE replacement (rebinding store methods, module
functions, or the time/lifetime source functions) and reflection on closure
cells, gc, ctypes. Replacing the source functions is exactly the test
mechanism, and exactly why it is not a production surface.

## CHANGED FILES

  tracker_identity/store.py
  tests/test_identity_surface.py
  tests/test_pre_id_content_identity.py   (narrow: six clock lines + helper)
  tests/test_registration_atomicity.py    (required: three clock sites)
  coder_returns/C-GOLD-ID-GATE-HARDENING-001.md   (this append)
All on the allowed list. models.py, importer.py, population/**, .github/**,
CLAUDE.md untouched. store.add, store.extend and records.append unchanged.

## RETURN

PUBLIC_WEAKREF_ROUTE_PERMANENTLY_TESTED = YES
PRODUCTION_CALLER_CAN_SET_TRANSACTION_TIME = NO
PRODUCTION_CALLER_CAN_SET_ISSUED_TS = NO
PRODUCTION_CALLER_CAN_SET_EXPIRES_TS = NO
TEST_CLOCK_PRODUCTION_REACHABLE = NO
CALLER_SELECTED_TTL_BLOCKED = YES
ARBITRARY_OR_OVERMAX_TTL_BLOCKED = YES
STORE_OWNED_TIME_RESTORED = YES
  Meaning, precisely: no production data or API input reaches transaction
  time, issued_ts, expires_ts or lifetime; time derives only from the store's
  own wall and monotonic sources, never decreases, and never runs slower than
  real time. Only code replacement can steer it — the stated boundary.
TERMINATE_HELPER_CAPABILITY_ALIGNED = YES
CROSS_STORE_REPLAY_BLOCKED = YES
POST_ISSUANCE_CONTENT_MUTATION_BLOCKED = YES
CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
IMPORT_PATH_AUTHORITY_RESIDUAL = OPEN
FULL_TEST_RESULT = Ran 263 tests — OK (0 failed, 0 errors, 0 skipped)
MUTATION_RESULT = 38 mutated, 33 killed, 5 surviving (all in the consumption
                  path, unreachable while construction authority is absent)
TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES
PR_CREATED = NO   MERGED = NO

DESKTOP_CODER TEST PASS != MANAGER ACCEPTANCE
REVIEW_CODER FINDING != MANAGER DECISION
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE
DO NOT MERGE.


---

# DC-TYPE1-CROSS-INSTRUMENT-CONSTRUCTION-GATE-006 — DESKTOP CODER RETURN

COMMISSION     = Drive 1zPSNh475RGe5H1sLxKZ1mlvYc0RHHdcoRvmsMiwGNtw (opened, read in full)
GOVERNED BASIS = Composer V9 §39.4 (Drive 1aMYAmh5…, line 2054 opened and quoted);
                 Frozen Tracker Core (Drive 1eZThdek…, five-dimension model and
                 §7 cross-instrument firewall, opened); Owner Era-1 activation
                 (Drive 13ltUNSo…, opened). CR014 reconciliation (1atPPMI0…) was
                 relied on only through the commission's citation of it.
BASE           = 441a3d22914656ba9e4d084c2a4c84030fb28ea9. Re-verified
                 immediately before commit: HEAD == origin/main after
                 `git fetch`. Base NOT stale.
BRANCH         = type1/cross-instrument-construction-gate (new, from base)

## CORRECTION D — READ THIS FIRST (governs every earlier section of this file)

The governed threat boundary is:

    Type-1 in-process authority = INTEGRITY-AGAINST-ACCIDENT,
    NOT security against adversarial same-process Python code.

Earlier sections in this file use phrases like "held ONLY in a closure", "no
container mutation reaches it" and "unreachable". Read each of them as
"not reachable by ordinary caller APIs or data mutation". None of them claims
resistance to closure-cell reflection (fn.__closure__), gc traversal, ctypes,
or code replacement. Those remain a DECLARED OUT-OF-BOUNDARY residual. The
same narrowing is applied in code:

- the `_make_issuance_authority` docstring;
- the NC01 test docstring;
- the IssuanceAuthenticityCR1CR2 class docstring;
- the `transition_authority_state` docstring.

Earlier sections are left verbatim (history preserved) and corrected here.

## CORRECTION A — INSTRUMENT IDENTITY SEMANTICS

**Rule implemented.** It follows the frozen five-dimension model and Composer
§39.4. No new identity authority was introduced.

- **SCOPE_ELIGIBILITY content.** It is `instrument_applicability`, `timeframe`
  and `scope_universe`. The bound `instrument` is added only when
  `instrument_applicability == "INSTRUMENT_SPECIFIC"`. That is the case where
  applicability is "encoded in the governed feature definition".
- **Unclear applicability.** `instrument_applicability` is a required
  dimension, and exactly `INSTRUMENT_AGNOSTIC` or `INSTRUMENT_SPECIFIC` is
  accepted. Any other value produces no key and the error
  `INSTRUMENT_APPLICABILITY_REVIEW_REQUIRED:<value>`. This covers: missing,
  blank, lower-case, padded, abbreviated, bool, int. Lookup then returns
  INCOMPLETE_LOOKUP and no claim is issued. It never silently shares and never
  silently splits.
- **Fitted state.** FITTED_LEARNED_STATE appends `instrument` whenever
  `fitted_state != "NONE"`, whatever the applicability. Learned state never
  crosses instruments (§7 default deny).
- **Binding instrument.** `instrument` stays a required declared dimension
  (`BINDING_DIMENSIONS`) even when it is not identity content. It is carried
  as `ClaimProvenance.bound_instrument` and
  `IdentityLookupResult.bound_instrument`, which is lineage, not authority.
- **Algorithm id.** `CONTENT_KEY_ALGORITHM_ID` was bumped from V1 to V2
  because the derivation changed. Searching population/** for `content_key`
  and `SALIX-CONTENT-IDENTITY-KEY` found nothing (INDEPENDENTLY_DERIVED), so
  no persisted V1 key is invalidated.
- **Fixture change.** Existing fixtures now declare INSTRUMENT_SPECIFIC. That
  preserves their prior (V1) split semantics, and no assertion was weakened.

**Tests.** Class `InstrumentIdentityCorrectionA006` in
tests/test_identity_surface.py:

| Test | What it proves |
|---|---|
| I1 | Same key for XAUUSD and EURUSD under AGNOSTIC. End to end, an EURUSD lookup gets EXACT on the XAUUSD row, and no claim is issued. |
| I2 | SPECIFIC splits the SCOPE key. Same definition gives NEAR_MATCH with RELATED_VERSION_CONTENT_REVIEW_REQUIRED, never a silent merge. |
| I2b | The declared applicability is itself scope content. |
| I3 | Missing or ambiguous applicability gives no key, INCOMPLETE_LOOKUP and no claim. |
| I3b | A missing `instrument` still fails, under both AGNOSTIC and SPECIFIC. |
| I4 / I4b | Fitted state differs by instrument even when the definition is AGNOSTIC; an EURUSD lookup is not EXACT on the XAUUSD fitted row. Control: with no fitted state, the fitted subkey is equal. |
| I5 / I5b | The request's target instrument survives a shared identity, in both the result and the claim provenance. One pending claim spans all bindings. |
| I6 | Source/provider, timeframe, causal/time, normalization, definition and price basis still split identity. |
| I7 | The algorithm id is V2. |

## CORRECTION B — D10/D11/D12/D13/A15

- `store._governed_construction_authority(verified)` is a module function that
  returns False in production. It is the single point where authority is
  resolved.
- `issue()` sets `authorizes_construction = (source(...) is True)`. A truthy
  non-True value is not authority (test B0b).
- There is no constructor argument, field, flag or API parameter for
  authority.
- Tests reach consumption only by replacing that function with
  `unittest.mock`, which is code replacement. The patch is scoped to issuance.
- The R6-style source scan still finds no literal `authorizes_construction=True`.
  The function body is asserted to be `return False`.
- **CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO.**

Also moved: the registration transaction, including the only
registered-identity append, is now the store-owned
`_commit_governed_registration`, and `commit_registration` delegates to it.
The terminal gate is now `authorizes_construction is not True`, not
`not authorizes_construction`.

Tests are in class `ConstructionConsumptionKillB006`:

- B0, B0b.
- A15: an authorized intake is accepted, the ledger moves to
  RELEASED/REGISTRATION_COMPLETED, and the claim can't be reused.
- A positive control: direct consume succeeds when every precondition holds.
  This shows the D-tests are not vacuous.
- D10: an EXPIRED authorized claim is not consumed.
- D11: a tampered mirror is not consumed.
- D12: an equal-but-different object, or None, is not consumed.
- D13: a different content key is not consumed.
- The source scan.

## CORRECTION C — A14 WRITE-PATH INVENTORY

| # | Path | Class |
|---|------|-------|
| 1 | `CanonicalIdentityStore.commit_registration` → `_commit_governed_registration` (claim, authenticity, ACTIVE, duplicate, canonical key, provenance, construction authority, consume; one lock order) | GOVERNED REGISTRATION |
| 2 | `import_identity_content` → `_commit_governed_import`. The store-owned writer RE-RUNS the whole import contract (`_plan_identity_import`) under the transition lock and appends only what that plan returns. | GOVERNED IMPORT / MIGRATION (authority QUALIFIED, see F-1) |
| 3 | `transition_authority_state` → `_commit_governed_transition`. It takes a transition record, never a row, re-checks type, key, from/to, known state, unique match, from_state, prior chain and duplicate id, and derives the replacement row itself. | GOVERNED TRANSITION (state replacement, not identity creation) |
| 4 | `_fixture_write_records`. It raises PermissionError unless `_fixture_seeding_permitted()` (production: False; only exact True counts) is code-replaced under test. | TEST / FIXTURE ONLY |
| 5 | `_staging_copy`. Ephemeral sweep copy; refuses claim issue, registration, import and transition; never the registry. | TEST/VALIDATION-INTERNAL (non-authoritative) |
| – | `store.add`, `store.extend` | REMOVED |
| – | `CanonicalIdentityStore(records=[...])` / positional seeding | REMOVED: no `records` field; `kw_only=True` makes positional misuse a TypeError |
| – | `store.records[...] = …` / `.append` | REMOVED: `records` is a read-only property returning a tuple snapshot |
| – | closure reflection / gc / ctypes / code replacement | UNGOVERNED, DECLARED OUT OF BOUNDARY (Correction D) |

Nothing reachable by ordinary calls is classed UNGOVERNED BYPASS.

**Tests.**

- `ClaimlessWritePathsClosedA14006` (surface), controls A14_1 to A14_9:
  - add/extend absent; records read-only;
  - constructor seeding rejected;
  - seeder refuses in production, including a truthy non-True permission;
  - seeder available to tests and scoped;
  - snapshot view;
  - staging copy refuses every authority operation;
  - registration commit refused without a claim and without authority;
  - transition commit can't inject a row, plus separate chain, duplicate and
    uniqueness kills with a positive control;
  - a live source scan finds no records writer outside store.py.
- `ImportAuthorityBoundaryA14006` (tests/test_identity_import.py):
  - a valid import writes through the governed commit;
  - generator rows are materialized once;
  - planning alone never writes;
  - a direct store import commit can't skip the contract (row count,
    authority class, provenance, era, catalogue);
  - a supplied content key is never trusted;
  - duplicate/currentness is not weakened: a second identical import is
    refused by the sweep;
  - a staging copy can't be imported into;
  - there is no extend escape hatch;
  - a pinned residual test (see F-1).
- The earlier A14-OPEN pins (C12, W12_W13_W14, NC14_NC15_NC16) were
  deliberately inverted to CLOSED.
- The fixtures in 5 test files moved to `fixture_store` / `seed_fixture`,
  which are test-only helpers built on code replacement.
- The three raw `store.records[0]=…` lines in test_transition_history became
  `seed_fixture(..., replace_all=True)`.

## M-2 (non-blocking) — FIXED (small, isolated)

Release reasons are also compared after NFKC, casefold and dropping
non-alphanumerics against the reserved set. The following are refused:

- ttl_expired
- TTL-EXPIRED
- Ttl Expired
- full-width forms
- a zero-width-suffixed form
- registration.completed
- a tab-suffixed form

Ordinary reasons still release, including "TTL expired early - withdrawn".
Test: `ReservedReasonLookalikesM2006`.

## FINDINGS

**F-1 — MEDIUM — import authority objects are self-certifying**

- **Where:**
  - tracker_identity/importer.py `_plan_identity_import`;
  - `CanonicalEraBoundary.computed_hash`, `SourceUniverseAuthority.computed_hash`,
    `IdentityImportManifest.evidence_hash`, `FeatureDefinitionCatalogue`;
  - pinned by test `ImportAuthorityBoundaryA14006.test_declared_residual_self_certifying_authority_objects`.
- **Scenario:** a caller builds a mutually consistent boundary, universe,
  manifest and catalogue (each self-hashed), plus rows that match them.
  `import_identity_content` accepts it and writes canonical rows without any
  claim. The contract proves internal consistency and catalogue-derived
  identity. It does NOT prove that the package is the Owner-ratified one.
- **Why not fixed:** no frozen or current governance defines an
  import-authority or package-approval object to bind against. The commission
  forbids inventing one.
- **Smallest safe correction (needs governance):** a Manager/Owner-issued
  approved-package fingerprint, or a registry resolved Tracker-side (the same
  pattern as the governed policy/normalizer registries), checked inside
  `_plan_identity_import`.
- **Frozen authority reopen:** NO for the frozen core. It needs a NEW governed
  definition of import authority.
- → A14_STATUS = BLOCKED_BY_MISSING_GOVERNANCE (import-authority sub-part
  only; ordinary claimless paths are CLOSED).

**F-2 — MEDIUM — UNIVERSE is still identity content**

- **Where:** content_identity.py `SUBKEY_DIMENSIONS["SCOPE_ELIGIBILITY"]` includes
  `scope_universe`.
- **Scenario:** §39.4 routes a UNIVERSE difference to PAYLOAD_BINDING unless
  semantics change. Here any `scope_universe` difference splits identity.
  Worse, a universe string that names the instrument (a fixture uses
  "XAUUSD/ERA_1") re-introduces instrument splitting for a definition declared
  INSTRUMENT_AGNOSTIC. The I1 tests use an instrument-neutral universe, so they
  do not catch this.
- **Smallest safe correction:** Manager decides whether `scope_universe` is
  definition semantics (keep) or binding (move to BINDING_DIMENSIONS with its
  own applicability declaration). A validation rule could also refuse a
  universe that names the bound instrument under AGNOSTIC.
- **Why not fixed:** not changed here, because the frozen model lists
  "regime/population/applicability" under SCOPE. Choosing between the two is a
  governance reading, not a Coder decision.
- **Frozen authority reopen:** POSSIBLY. The frozen SCOPE wording and §39.4
  pull in different directions for UNIVERSE.

**F-3 — LOW — canonical row identity still carries instrument**

- **Where:** models.py `FeatureIdentity.canonical_key` includes `instrument`.
  Catalogue `FeatureDefinitionRecord` hashes and importer check
  `ROW_CATALOGUE_INSTRUMENT_MISMATCH`.
- **Scenario:** a shared AGNOSTIC identity's canonical row records its first
  binding. A CANONICAL_ID-mode lookup with another instrument misses the
  canonical-key match, although the PRE_ID content path resolves correctly
  (I1). The catalogue cannot yet express one agnostic definition bound to
  many instruments.
- **Smallest safe correction:** a governed design for agnostic catalogue rows.
  Out of Correction A's "smallest clean" scope.
- **Frozen authority reopen:** NO. It needs Manager design.

**F-4 — LOW — history lists stay publicly mutable**

- **Where:** store.py `creation_records`, `transitions`, `claims` stay public
  lists. `add_creation` / `add_transition` remain.
- **Scenario:** raw appends can fabricate creation or transition history, but
  cannot write a canonical identity. `claims` is an inert mirror checked
  against the ledger. A forged creation record could satisfy the transition
  prior-chain check for a tracked row.
- **Smallest safe correction:** move creation/transition history into the same
  store-owned state, in a later bounded commission.
- **Frozen authority reopen:** NO.

**F-5 — LOW — scope disclosure**

The changed files outside the commission's "expected likely files" list are:

- tracker_identity/search.py (+2 lines: bound_instrument lineage, needed for I5);
- tracker_identity/catalogue.py (+6: `instrument_applicability` declared on the
  governed definition, needed for A2);
- tracker_identity/__init__.py (+2: exports);
- tracker_identity/transition.py (writes through the store-owned transition
  commit, needed for A14 because it performed a raw `store.records[i]=`).

None of these is a fenced path. models.py was touched only for the two lineage
fields (I5). population/**, .github/**, FW, ML, Composer and CLAUDE.md are
untouched.

**F-6 — LOW — mutation survivor `IMP_commit_staged_check_removed`**

- **Where:** store.py `commit_import` guard `not is_staged(store)`.
- **Why it survives:** it is an equivalent mutant today. `_plan_identity_import`
  already refuses a staged target (that mutant is killed), so this second
  guard is defence in depth and cannot be observed.
- **Smallest safe correction:** none needed. Either keep it (it protects
  against a future plan regression) or delete it. Reported, not hidden.

Withdrawn / corrected from earlier returns: none new. The DC004/DC005
"unreachable" phrasing is narrowed by Correction D above.

## EVIDENCE

- **TARGETED_TEST_RESULTS**
  - DERIVATION_CLASS = INDEPENDENTLY_DERIVED; EXACT_INPUTS = IMPLEMENTATION_SHA
    tree; Python 3.12.10.
  - tests.test_identity_surface: Ran 163, OK.
  - tests.test_pre_id_content_identity: Ran 59, OK.
  - tests.test_registration_atomicity: Ran 11, OK.
  - tests.test_import_content_key: Ran 13, OK.
- **FULL_TEST_RESULT**
  - `python -m unittest discover -s tests`: Ran 304, OK (0 failed, 0 errors).
  - Baseline at 441a3d2 was 263 OK.
- **MUTATION_RESULT**
  - Totals: 49 mutants, 48 killed, 1 surviving (F-6, equivalent).
  - METHOD: scratchpad driver `mutate006.py`. For each mutant it applies one
    exact-anchor source replacement (the anchor must be unique or
    occurrence-indexed), runs the full discover suite, restores the source,
    and asserts the restored baseline is green (it was).
  - First pass: 5 survivors. Four were killed by new tests (I3b,
    transition unique-match, prior-chain, duplicate-id). The re-run gave 48
    of 49.
  - Groups:
    - **I-guards (11, all killed):** I1 (scope-always), I2 (scope-never),
      I2b, I3, I3b, I4 (fitted-never), I4b (fitted-always), I7, and three
      I5 variants.
    - **Correction B (10, all killed):** D10, D11, D12, D12b (== for is),
      D13, Dx (authority check in consume), A15, commit authority gate,
      truthy-authority at issue, production authority True.
    - **A14 (21, all killed):** fixture gate removed/truthy/permitted;
      records live list; kw_only removed; add restored; staging unmarked;
      three staged guards; eight transition re-checks; dead-writer scan;
      registration duplicate and canonical checks.
    - **Import discriminator (6, 5 killed):** plan-errors-still-write,
      sweep-fail-still-writes, plan staged check, commit-skips-plan (writes
      caller rows), supplied key trusted; SURVIVED: commit staged check (F-6).
    - **M-2 (1, killed):** fold removed.
  - REPRODUCIBLE_BY_MANAGER = YES (driver available on request; every anchor
    and its replacement is listed in it).

## RETURN

- BASE_FOR_CORRECTION = 441a3d22914656ba9e4d084c2a4c84030fb28ea9
- IMPLEMENTATION_SHA = 6f97f098d94c75728a3b4b7ec941f3e44be4ea5a
- REPORT_SHA = (the commit adding this section; stated in the relay message)
- PUSH_SUCCEEDED = (stated in the relay message)
- PR_CREATED = NO
- MERGED = NO

Instrument identity:

- INSTRUMENT_BINDING_SPLITS_CANONICAL_IDENTITY_BY_DEFAULT = NO
  - Qualified by F-2: a universe string that names the instrument still splits.
- INSTRUMENT_SPECIFIC_SEMANTICS_REMAIN_IDENTITY_CONTENT = YES
- UNCLEAR_INSTRUMENT_APPLICABILITY_FAILS_CLOSED = YES
- CROSS_INSTRUMENT_FITTED_STATE_REUSE_BLOCKED = YES
  - At content-identity level. Actual fitted caches are not implemented in
    Type-1.

Consumption mutants:

- D10_KILLED = YES
- D11_KILLED = YES
- D12_KILLED = YES
- D13_KILLED = YES
- A15_KILLED = YES

Write paths:

- A14_STATUS = BLOCKED_BY_MISSING_GOVERNANCE
  - The ordinary claimless paths are CLOSED.
  - The import-authority sub-part needs governance (F-1).
- PRODUCTION_STORE_ADD_EXTEND_BYPASS = NO
- IMPORT_AUTHORITY_BOUNDARY_SOUND = QUALIFIED
  - The contract can't be bypassed, but its authority objects are
    self-certifying (F-1).

Boundaries:

- CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
- SAME_PROCESS_INTROSPECTION_RESIDUAL = DECLARED_OUT_OF_BOUNDARY

Results:

- TARGETED_TEST_RESULTS = surface 163 OK; pre_id 59 OK; atomicity 11 OK;
  import_content_key 13 OK
- FULL_TEST_RESULT = Ran 304 — OK
- MUTATION_RESULT = 49 mutated, 48 killed, 1 surviving (equivalent, F-6)

New finding counts:

- NEW_CRITICAL_COUNT = 0
- NEW_HIGH_COUNT = 0
- NEW_MEDIUM_COUNT = 2 (F-1, F-2)
- NEW_LOW_COUNT = 4 (F-3, F-4, F-5, F-6)

TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES
  - F-1 and F-2 are governance decisions, not code defects in this change.

No FEATURE_ID, FEATURE_VERSION, Tracker registry row, EURUSD fit, FW
execution, holdout exposure, ML training, Type-2 or production artifact was
created. Drive was read only.

DESKTOP_CODER TEST PASS != MANAGER ACCEPTANCE
REVIEW_CODER FINDING != MANAGER DECISION
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE
DO NOT MERGE.


---

# DC-TYPE1-CROSS-INSTRUMENT-CONSTRUCTION-GATE-006R — DESKTOP CODER RETURN

**Documents opened and read in full**

| Document | Drive ID |
|---|---|
| Commission | 1WOsB4qu7_3G0lrPbY4gKkIYAClkoCaerdfT_AexKNYI |
| CR015 | 1TsTnoo9ur7aUFcIDhv2MTNJgqWjesMd52N-l_d5XQEg |
| Owner Era-1 activation | 13ltUNSo7rXLoNGfrCDO35XghyRzJ-2_Z__0z0skPnco |

The Owner Era-1 activation was re-opened to decide whether production package registration is possible.

**Base check**

- BASE = d9350ee76aac00e7ba88a2681dec0eaa797fd81d.
- Immediately before commit, after `git fetch`, HEAD and origin/type1/cross-instrument-construction-gate were both at d9350ee.
- The base is not stale.

## CORRECTION E — CLAIM NARROWING (read first)

- DC-006 V2 fixed only the DIRECT bound-instrument field.
- It did NOT close instrument leakage through the other identity-bearing fields. DC-006 already qualified its own `INSTRUMENT_BINDING_SPLITS_CANONICAL_IDENTITY_BY_DEFAULT = NO`. Read that claim as "direct field only".
- This correction addresses the alternate paths in the ways described below. It does not claim generic same-process security.
- Type-1 in-process authority is integrity-against-accident only.
- Closure reflection, gc, ctypes and code replacement remain DECLARED OUT OF BOUNDARY.

**Withdrawn:** the DC-006 finding "F-6 equivalent / cannot be caught" was wrong.

- Permitted test instrumentation (mock) reaches that guard.
- Reaching it exposed a latent defect in my own DC-006 code. When the commit-stage staged guard fired, `commit_import` returned the planner's SUCCESS result (`imported_row_count=1`, `errors=()`) while writing nothing. It now reports `STORE_IS_STAGING_COPY` with 0 rows.

## A — INSTRUMENT-AGNOSTIC IDENTITY LEAKAGE (content_identity.py)

**Mechanism**

| Concept | Carried by | Status |
|---|---|---|
| SEMANTIC_APPLICABILITY_SCOPE | the existing `scope_universe` dimension (name kept for catalogue compatibility) | identity content |
| BOUND_UNIVERSE | the optional `bound_universe` dimension | binding / lineage only; never part of any subkey |

**Leakage guard**

- For INSTRUMENT_AGNOSTIC definitions, every identity-bearing field is scanned by `instrument_token_leaks()`: graph, dependency closure, parameters (keys and values), normalization, causal time, completion, availability, source, price basis, vintage, timeframe and scope.
- Any leaked token produces `INSTRUMENT_TOKEN_LEAKAGE_REVIEW_REQUIRED:<field>:<token>`.
- The result is no key, an INCOMPLETE lookup and no claim.
- Nothing is stripped or rewritten.
- The guard detects:
  - the payload's own bound instrument, anywhere in the field;
  - currency/metal pair symbols: a 6-letter token, the 6-letter prefix of a longer token such as XAUUSDm, or two adjacent code tokens such as XAU/USD;
  - metal codes;
  - metal names.
- Fitted state is exempt from the scan. It is always instrument-qualified (DC-006).

**Time and dependencies**

- Server/feed time semantics are shared when the declared feed clock is identical, e.g. "SALIX-BROKER-SERVER-UTC-TRANSITION-V1".
- A different feed clock splits.
- Role references ("BOUND_ROLE:close") do not split across bindings.

**Tests: `AgnosticLeakage006R`**

| Test | What it proves |
|---|---|
| L1 | XAUUSD and EURUSD with equivalent semantics give the same composite key |
| L2 | a bound_universe difference alone does not split, and bound_universe is never hashed |
| L2b | the semantic applicability scope still splits |
| L3 | the same feed clock shares identity; a different feed splits |
| L4 | role dependencies share identity |
| L5 | INSTRUMENT_SPECIFIC with instrument-named scope, time and dependencies still splits, with no error |
| L6 | 12 leaky agnostic declarations across scope, time, dependencies, graph, parameters and source fail REVIEW_REQUIRED; an unknown symbology is caught through the bound instrument; a suffixed pair of a different instrument is caught |
| L6b | a leak is refused, not stripped |
| L6c | an end-to-end leaky lookup is INCOMPLETE and issues no claim |
| L7 | the neutral vocabulary produces no false positives |
| L8 | the ANY scope rules hold |

## B — CANONICAL ROW REPRESENTATION

**Rules**

- The `AGNOSTIC_INSTRUMENT_SCOPE = "ANY"` is the canonical-row instrument scope of an INSTRUMENT_AGNOSTIC, UNFITTED definition.
- `FeatureDefinitionRecord.completeness_errors` refuses an agnostic unfitted row stamped with a concrete instrument: `AGNOSTIC_DEFINITION_ROW_INSTRUMENT_MUST_BE_ANY`. It is refused, not rewritten.
- A fitted agnostic row keeps its concrete instrument, because learned state is instrument-qualified.
- The content key refuses ANY in two cases:
  - with INSTRUMENT_SPECIFIC applicability (`INSTRUMENT_SCOPE_ANY_REQUIRES_AGNOSTIC_APPLICABILITY`);
  - with fitted state (`FITTED_STATE_REQUIRES_CONCRETE_INSTRUMENT`).
- A PRE_ID construction request must be bound to a concrete instrument (`PRE_ID_BOUND_INSTRUMENT_MUST_BE_CONCRETE`).
- The exact binding stays in `ClaimProvenance.bound_instrument` and `IdentityLookupResult.bound_instrument`.
- `search._canonical_matches`: an ANY row matches a canonical-ID subject bound to any CONCRETE instrument with identical feature id, version, definition hash, graph hash and timeframe.
- The subject's binding is reported, never written onto the row.

**Tests: `CanonicalAgnosticRow006R`**

| Test | What it proves |
|---|---|
| R1 | when an XAUUSD-bound request registers first, the row is ANY and the claim lineage says XAUUSD |
| R2 | an agnostic candidate stamped XAUUSD is refused, and nothing is written |
| R3 | a later EURUSD PRE_ID request is EXACT on the same row: bound=EURUSD, no claim, no new identity |
| R4 | a later canonical-ID request (EURUSD and XAUUSD, with and without content) is EXACT on the same row. Controls: a different timeframe, an unbound subject, and a concrete XAUUSD row with an EURUSD subject do not match. |
| R4b | pinned residual (see R-4) |
| R5 | a PRE_ID request bound to ANY is refused |
| R6 | a fitted agnostic row stays concrete |

- R1 to R4 register through the construction path only with `_governed_construction_authority` mocked. That is code replacement; the production path is unchanged.

## C — APPROVED_IMPORT_PACKAGE_REGISTRY

This is the new file `tracker_identity/import_package_registry.py`.

**Entry and package identity**

- Each entry pins:
  - era-boundary hash;
  - source-universe hash;
  - import-manifest hash;
  - catalogue hash;
  - a governed `approval_ref`.
- All four hashes are validated as 64-character lowercase hex.
- Bare role or status words are refused as approval references: OWNER, MANAGER, APPROVED, YES, TRUE, ADMIN, SALIX_MANAGER, SALIX_OWNER, GOVERNED, AUTHORIZED.
- The package identity is always the COMPUTED hashes, never the declared hash fields.
  - `FeatureDefinitionCatalogue.computed_hash()` is new.
  - It hashes every field of every definition, type-tagged and ordered.

**Immutability and checks**

- The registry is a MappingProxyType over a FUNCTION-LOCAL dict. There is no module-level backing container, and `_ENTRIES` is a tuple.
- Malformed, duplicate or wrong-type entries refuse to load.
- At use, the resolver re-checks entry type, integrity and key.
- `_plan_identity_import` requires approval. The store-owned import commit re-runs the plan, so the direct store path is gated too.
- No admin or bypass path was added.
- Tests register fixture packages only by `mock.patch` of the registry attribute, which is code replacement.

**Production state: EMPTY**

The Owner Era-1 activation pins only these things:

- the Era-1 freeze;
- PR4 at d4946d2 and PR5 at d562342;
- the Era model.

It pins no import-manifest hash, no catalogue hash and no package approval. No entry was invented. Every production import refuses, including the checked-in Era-1 package (test `test_era1_package_is_not_production_approved`).

**Tests**

- `ApprovedImportPackageRegistry006R` C1 to C7:
  - production empty and closed;
  - runtime immutable, with no module dict;
  - an approved package imports, but any single-field catalogue or manifest change refuses;
  - approval role words are refused;
  - malformed entries are refused;
  - integrity is revalidated at use;
  - copied declared hash strings are not identity.
- `test_self_consistent_fake_package_cannot_write`: this inverts the DC-006 residual pin.
- Existing import tests now wrap each import in `approve_package(...)` for exactly the package imported. The negative import tests still prove their own checks: the direct-commit test asserts that `IMPORT_PACKAGE_NOT_APPROVED` is NOT the reason it refused.

## D — F6

- `CommitStageStagedGuardF6006R.test_F6`: the planner's staged check is bypassed with a mock of `importer._is_staged`. The test asserts the plan really succeeds. The commit-stage guard then refuses, reports `STORE_IS_STAGING_COPY` with 0 rows, and writes nothing.
- `test_F6b`: the converse. It proves the planner's check refuses on its own.

## F — PRESERVED

- **D10–D13 and A15:** still killed (mutants re-run below).
- **Construction authority:** `_governed_construction_authority` still returns False, and no literal grant exists.
- **Write bypasses:** add, extend and records mutation remain absent.
- **Reserved-reason fold (M-2):** intact.
- **Same-process introspection:** remains declared out of boundary.

## RESIDUALS

**R-1 — MEDIUM — the leakage guard is lexical**

- **Location:** content_identity.py, `instrument_token_leaks` and `LEAKAGE_CHECKED_DIMENSIONS`.
- **Failure scenario:** an agnostic definition bound to XAUUSD whose time semantics name an alias ("CABLE-SESSION") or an index symbol ("US30"). The token is not a currency/metal pair, not a metal and not the bound instrument, so it passes. The instrument token then enters identity and SPLITS it per instrument.
  - The failure direction is over-split (fragmentation), not a cross-instrument merge.
  - Numeric semantics tuned to one instrument (e.g. a pip size) are undetectable by any lexical scan.
- **Blocks merge:** NO. The detectable cases fail closed, and the undetected failure over-splits rather than merging.
- **Smallest safe correction:** a Tracker-owned governed instrument-symbology registry (symbols and aliases) replacing the built-in vocabulary.
- **Frozen authority reopen:** NO.

**R-2 — MEDIUM — ANY rows do not check applicability-scope membership**

- **Location:** search.py, `_canonical_matches`.
- **Failure scenario:** a definition whose semantic scope is FX_METALS resolves EXACT for a request bound to GER40. No governed instrument-to-universe membership map exists to check against.
  - No identity is created: construction authority is absent, and CROSS-INSTRUMENT IDENTITY CREATION stays fenced.
  - However, a consumer could reuse a definition outside its declared semantic scope.
- **Blocks merge:** NO for this branch. It must be resolved before any cross-instrument USE of a shared identity.
- **Smallest safe correction:** a governed universe-membership registry, checked in `_canonical_matches` and in PRE_ID lookup.
- **Frozen authority reopen:** NO.
- → CANONICAL_AGNOSTIC_ROW_INSTRUMENT_REPRESENTATION_SOUND = QUALIFIED.

**R-3 — LOW — shared feed is proven only by declaration**

- **Location:** causal_time_semantics and source_provider.
- **Failure scenario:** "same server/feed is proven" rests on equality of the declared clock string and provider. Two feeds that are actually different but declared with the same string would share identity.
- **Blocks merge:** NO.
- **Smallest safe correction:** a governed feed/clock registry.
- **Frozen authority reopen:** NO.

**R-4 — LOW — BOUND_ROLE references are not a governed dependency form**

- **Location:** stale_sweep dangling-dependency check; pinned by test R4b.
- **Failure scenario:** role references share identity at the key level (L4). Registration of such a definition, however, fails closed: STALE_STATE_SWEEP_FAILED with DANGLING_DEPENDENCY.
- **Why not fixed:** no role-resolution semantics were invented.
- **Blocks merge:** NO.
- **Smallest safe correction:** Manager defines role-reference resolution, and the sweep resolves roles against the binding.
- **Frozen authority reopen:** NO.

**R-5 — LOW — the catalogue hash algorithm is unversioned**

- **Location:** catalogue.py, `FeatureDefinitionCatalogue.computed_hash`.
- **Failure scenario:** a later change to the hashing would silently un-approve every registered package.
- **Blocks merge:** NO. The registry is empty.
- **Smallest safe correction:** add a catalogue-hash algorithm id to the entry.
- **Frozen authority reopen:** NO.

**Carried forward (not new)**

- CR015 M-2: public creation/transition history lists.
- Registry and module rebinding by code replacement. This is the same class as the policy and normalizer registries and is declared out of boundary.

## EVIDENCE

DERIVATION_CLASS = INDEPENDENTLY_DERIVED. EXACT_INPUTS = the IMPLEMENTATION_SHA tree on Python 3.12.10. REPRODUCIBLE_BY_MANAGER = YES.

**Targeted tests**

| Suite | Result |
|---|---|
| tests.test_identity_surface | Ran 181, OK |
| tests.test_pre_id_content_identity | Ran 59, OK |
| tests.test_registration_atomicity | Ran 11, OK |
| tests.test_import_content_key | Ran 13, OK |
| tests.test_identity_import | Ran 25, OK |

**Full suite:** `python -m unittest discover -s tests` ran 332 tests, OK. The DC-006 total was 304.

**Mutation**

- Method: scratchpad driver `mutate006r.py`, the DC-006 driver extended. For each mutant it applies one exact-anchor replacement, runs the full suite, restores the file, and re-checks that the baseline is green afterwards.
- First pass, 79 mutants: 75 killed, 4 surviving.

| First-pass survivor | Resolution |
|---|---|
| IMP_plan_staged_check_removed | killed by F6b |
| LK_prefix_pair_off | killed by a suffixed pair of another instrument in L6 |
| ROW_canon_any_match_off | killed by the content-free canonical-ID lookup in R4 |
| ROW_near_uses_exact_key | proven equivalent: an ANY canonical match is always an exact hit, so the near list never decides the outcome. The code change was reverted rather than kept untested, and the mutant was removed. |

- Final: 78 mutated, 78 killed, 0 survivors. The restored baseline was green.
- Groups:

| Group | Count | Mutants |
|---|---|---|
| Retained DC-006 | 48 | I-guards; D10, D11, D12, D12b, D13, Dx, A15; B authority; A14 controls; import discriminators; M-2 |
| Leakage | 10 | guard off; scope, time and dependencies unchecked; bound rule; pair rule; metal rule; adjacent rule; prefix rule; bound_universe hashed |
| ANY | 2 | specific rule; fitted rule |
| Row | 5 | must-be-ANY; ANY match; ANY timeframe; ANY accepts unbound; PRE_ID concrete |
| Registry | 11 | check removed; declared hashes; role word; hex format; duplicate; build type; use type; use integrity; use key; mutable registry; partial catalogue hash |
| F6 | 2 | commit guard off; refusal misreported |

## RETURN

Commit and branch:

- BASE_FOR_CORRECTION = d9350ee76aac00e7ba88a2681dec0eaa797fd81d
- IMPLEMENTATION_SHA = 4bdee299d259764c57d57bfe4ff060d9cdf61f2e
- REPORT_SHA = (the commit adding this section; stated in the relay message)
- PUSH_SUCCEEDED = (stated in the relay message)
- PR_CREATED = NO
- MERGED = NO

Corrections:

- AGNOSTIC_BOUND_UNIVERSE_SPLITS_IDENTITY = NO
- AGNOSTIC_INSTRUMENT_TOKEN_LEAKAGE_FAILS_CLOSED = YES (for the detectable token classes; R-1)
- CANONICAL_AGNOSTIC_ROW_INSTRUMENT_REPRESENTATION_SOUND = QUALIFIED (R-2)
- APPROVED_IMPORT_PACKAGE_REGISTRY_IMPLEMENTED = YES
- FAKE_SELF_CONSISTENT_IMPORT_CAN_WRITE = NO
- IMPORT_PRODUCTION_PACKAGE_REGISTRATION_BLOCKED = YES
- F6_KILLED = YES
- D10_KILLED = YES
- D11_KILLED = YES
- D12_KILLED = YES
- D13_KILLED = YES
- A15_KILLED = YES
- CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO
- SAME_PROCESS_INTROSPECTION_RESIDUAL = DECLARED_OUT_OF_BOUNDARY

Results:

- TARGETED_TEST_RESULTS = surface 181 OK; pre_id 59 OK; atomicity 11 OK; import_content_key 13 OK; identity_import 25 OK
- FULL_TEST_RESULT = Ran 332, OK
- MUTATION_RESULT = 78 mutated, 78 killed, 0 surviving

New findings:

- NEW_CRITICAL_COUNT = 0
- NEW_HIGH_COUNT = 0
- NEW_MEDIUM_COUNT = 2 (R-1, R-2)
- NEW_LOW_COUNT = 3 (R-3, R-4, R-5)

TECHNICALLY_READY_FOR_MANAGER_RECONCILIATION = YES

**Scope**

| File | Change |
|---|---|
| tracker_identity/content_identity.py | edited |
| tracker_identity/catalogue.py | edited |
| tracker_identity/search.py | edited |
| tracker_identity/importer.py | edited |
| tracker_identity/store.py | F6 only |
| tracker_identity/__init__.py | exports |
| tracker_identity/import_package_registry.py | new |
| tests/test_identity_surface.py | tests |
| tests/test_identity_import.py | tests |
| tests/test_import_content_key.py | tests |
| tests/test_era1_boundary.py | tests |

The following were not touched: population/**, .github/**, FW, ML, the Composer document and CLAUDE.md.

Nothing was created: no FEATURE_ID, FEATURE_VERSION, Tracker registry row, cross-instrument identity, EURUSD fit, FW execution, holdout exposure, ML training, Type-2 or production artifact. Drive was read only.

DESKTOP_CODER TEST PASS != MANAGER ACCEPTANCE
REVIEW_CODER FINDING != MANAGER DECISION
NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE
DO NOT MERGE.
