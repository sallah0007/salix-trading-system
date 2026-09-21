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
