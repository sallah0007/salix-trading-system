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
