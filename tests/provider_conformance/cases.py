"""The 15 frozen E-01 conformance cases.

Every case runs in its OWN namespace (run_id + case_id) so that no case can
contaminate another's HEAD, and so a failed case leaves diagnosable state.

Status vocabulary, used strictly:
    PASS      the required behaviour was observed
    FAIL      the required behaviour was violated
    UNPROVEN  this configuration cannot decide it (NEVER reported as PASS)
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .authority_writer import RestrictedAuthorityWriter
from .canonical import sha256_hex
from .evidence import EvidenceRecorder
from .model import (HeadRecord, head_key, is_authority_key, probe_key,
                    transition_key)
from .store_port import (AccessDenied, NotFound, ObjectStorePort,
                         PreconditionFailed, UnknownWriteOutcome)

PASS, FAIL, UNPROVEN = "PASS", "FAIL", "UNPROVEN"


@dataclass
class CaseResult:
    case_id: str
    title: str
    requirement: str
    status: str
    detail: str
    facts: dict = field(default_factory=dict)


@dataclass
class CaseContext:
    store: ObjectStorePort
    prefix: str
    run_id: str
    recorder: EvidenceRecorder
    ordinary_store: Optional[ObjectStorePort] = None
    ordinary_principal_label: str = ""
    sequence_policy: str = "RESET_PER_EPOCH"
    _clock: Callable[[], int] = None

    def __post_init__(self):
        counter = itertools.count(1_000_000_000)
        self._clock = lambda: next(counter)

    def writer(self, case_id: str, *, writer_id: str = "authority-writer-1"
               ) -> RestrictedAuthorityWriter:
        return RestrictedAuthorityWriter(
            self.store, prefix=self.prefix,
            namespace_id=f"{self.run_id}--{case_id}", clock=self._clock,
            writer_id=writer_id, sequence_policy=self.sequence_policy)

    def started(self, case_id: str, writer: RestrictedAuthorityWriter,
                *, transitions: int = 0) -> RestrictedAuthorityWriter:
        """Namespace with a genesis HEAD and `transitions` accepted transitions."""
        writer.initialise_namespace(payload_hash=sha256_hex(b"genesis"))
        for index in range(transitions):
            token = writer.issue_fencing_token()
            request = writer.propose(sha256_hex(f"payload-{index}".encode()))
            outcome = writer.commit(request, token)
            if not outcome.accepted:
                raise AssertionError("FIXTURE_COMMIT_FAILED:" + outcome.status)
        return writer

    def log(self, case_id: str, operation: str, outcome: str, **kwargs) -> None:
        self.recorder.record(case_id=case_id, operation=operation,
                             outcome=outcome, **kwargs)


class _LostResponseStore:
    """Delegates every call, but reports ONE compare_and_swap_head as unknown
    AFTER the provider really performed it.

    This is how a dropped response / client timeout looks to a caller: the
    write may or may not have landed. It is the only honest way to exercise
    E01-M1 unknown-commit recovery against a live provider.
    """

    def __init__(self, inner):
        self._inner = inner
        self.armed = True

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def compare_and_swap_head(self, key, expected_version, data):
        result = self._inner.compare_and_swap_head(key, expected_version, data)
        if self.armed:
            self.armed = False
            raise UnknownWriteOutcome("RESPONSE_LOST_AFTER_PROVIDER_ACCEPTED")
        return result


# ---------------------------------------------------------------- cases
def case_01_strong_read_after_write(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c01", ctx.writer("c01"))
    # DC-038 F: dedicated, run-scoped probe key. A probe is never written to an
    # authoritative HEAD or transition key, even in an isolated bucket.
    key = probe_key(ctx.prefix, ctx.run_id, "c01-read-after-write")
    if is_authority_key(key):
        return CaseResult("c01", "strong read-after-write", "BuildPlan 15.1 / E07-M1",
                          FAIL, "PROBE_KEY_INSIDE_AUTHORITY_NAMESPACE:" + key)
    payload = b"read-after-write-probe"
    equal, meta = ctx.store.read_after_write_probe(key, payload)
    token = writer.issue_fencing_token()
    outcome = writer.commit(writer.propose(sha256_hex(b"p1")), token)
    head, _ = writer.read_head()
    ctx.log("c01", "read_after_write_probe", PASS if equal else FAIL,
            request_metadata={"key": key, "content_sha256": sha256_hex(payload)},
            response_metadata=meta)
    head_visible = (outcome.accepted
                    and head.accepted_transition_hash == outcome.transition_hash)
    status = PASS if (equal and head_visible) else FAIL
    return CaseResult("c01", "strong read-after-write", "BuildPlan 15.1 / E07-M1",
                      status,
                      f"object_probe_equal={equal} head_reads_own_write={head_visible}",
                      {"head_sequence": head.sequence, "probe_key": key})


def case_02_immutable_create_only(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c02", ctx.writer("c02"))
    key = transition_key(ctx.prefix, writer.namespace_id, 1, 999, "a" * 64)
    ctx.store.append_transition_if_absent(key, b"first-bytes")
    conflict_refused = False
    try:
        ctx.store.append_transition_if_absent(key, b"different-bytes")
    except PreconditionFailed:
        conflict_refused = True
    identical_ok = True
    try:
        ctx.store.append_transition_if_absent(key, b"first-bytes")
    except PreconditionFailed:
        identical_ok = False
    body = ctx.store.read_transition(key).data
    unchanged = body == b"first-bytes"
    ctx.log("c02", "append_transition_if_absent", PASS if conflict_refused else FAIL,
            request_metadata={"key": key},
            detail="overwrite attempt with different bytes")
    status = PASS if (conflict_refused and unchanged) else FAIL
    return CaseResult("c02", "immutable create-only transition write", "E01-M1 / E-09",
                      status,
                      f"overwrite_refused={conflict_refused} bytes_unchanged={unchanged} "
                      f"identical_rewrite_idempotent={identical_ok}")


def case_03_conditional_head_cas(ctx: CaseContext) -> CaseResult:
    writer = ctx.writer("c03")
    genesis = writer.initialise_namespace(sha256_hex(b"genesis"))
    duplicate = writer.initialise_namespace(sha256_hex(b"genesis"))
    token = writer.issue_fencing_token()
    accepted = writer.commit(writer.propose(sha256_hex(b"p1")), token)
    head, _ = writer.read_head()
    ctx.log("c03", "create_head_if_absent", PASS if genesis.accepted else FAIL,
            response_metadata={"etag": genesis.head_version})
    ctx.log("c03", "duplicate_create",
            PASS if duplicate.status == "REJECTED_NAMESPACE_EXISTS" else FAIL,
            detail=duplicate.status)
    ok = (genesis.accepted and duplicate.status == "REJECTED_NAMESPACE_EXISTS"
          and accepted.accepted and head.sequence == 1)
    return CaseResult("c03", "conditional HEAD CAS", "E01-H1 / E01-M1",
                      PASS if ok else FAIL,
                      f"genesis={genesis.status} duplicate={duplicate.status} "
                      f"commit={accepted.status} head_sequence={head.sequence}")


def case_04_stale_etag_rejected(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c04", ctx.writer("c04"))
    stale_request = writer.propose(sha256_hex(b"stale"))          # holds version V1
    first = writer.commit(writer.propose(sha256_hex(b"advance")),
                          writer.issue_fencing_token())            # HEAD -> V2
    # Committed against its OWN snapshot, so the request is internally
    # consistent and the PROVIDER's If-Match precondition is what refuses it.
    # That is the behaviour under test here, not the writer's own validation.
    replayed = writer.commit(stale_request, writer.issue_fencing_token(),
                             use_observed_snapshot=True)
    # And the same stale request re-validated against current state is refused
    # semantically too, before any CAS: defence in depth, both observable.
    revalidated = writer.commit(stale_request, writer.issue_fencing_token())
    head, _ = writer.read_head()
    ctx.log("c04", "compare_and_swap_head_stale_etag",
            PASS if replayed.status == "CAS_LOST" else FAIL,
            request_metadata={"if_match": stale_request.observed_head_version},
            response_metadata=replayed.evidence or {},
            detail=replayed.status)
    ok = (first.accepted and replayed.status == "CAS_LOST"
          and revalidated.status == "REJECTED_SEQUENCE_NOT_STRICTLY_NEXT"
          and head.sequence == 1)
    return CaseResult("c04", "stale ETag rejection (provider precondition)", "E01-M1",
                      PASS if ok else FAIL,
                      f"first={first.status} stale_etag={replayed.status} "
                      f"revalidated={revalidated.status} head_sequence={head.sequence}")


def case_05_stale_epoch_with_current_etag(ctx: CaseContext) -> CaseResult:
    """THE SYDNEY FINDING. Provider CAS alone accepts an old-epoch body when the
    caller holds the current ETag. The writer must refuse it BEFORE the CAS."""
    writer = ctx.started("c05", ctx.writer("c05"), transitions=1)
    advanced = writer.advance_epoch(writer.issue_fencing_token())
    head_after, version_after = writer.read_head()

    stale_epoch_request = writer.propose(
        sha256_hex(b"old-epoch-body"), epoch=head_after.epoch - 1,
        sequence=head_after.sequence + 1)
    writer_outcome = writer.commit(stale_epoch_request,
                                   writer.issue_fencing_token())
    writer_refused = writer_outcome.status == "REJECTED_TRANSITION_EPOCH_STALE"

    # Now the bypass path the Manager observed: current ETag, old epoch body,
    # no semantic validation. Recorded as provider BEHAVIOUR, not as a failure
    # of the provider: it is exactly why the writer must be load-bearing.
    rollback_body = HeadRecord(
        namespace_id=writer.namespace_id, epoch=head_after.epoch - 1,
        sequence=head_after.sequence + 1,
        accepted_transition_hash=head_after.accepted_transition_hash,
        previous_head_hash=head_after.head_hash(),
        accepted_at_ns=ctx._clock()).to_bytes()
    try:
        ctx.store.raw_put_head(head_key(ctx.prefix, writer.namespace_id),
                               rollback_body, expected_version=version_after)
        provider_accepted_rollback = True
    except (PreconditionFailed, AccessDenied) as exc:
        provider_accepted_rollback = False
        ctx.log("c05", "raw_put_head_bypass", "REFUSED", detail=str(exc))
    if provider_accepted_rollback:
        read_back, _ = writer.read_head()
        ctx.log("c05", "raw_put_head_bypass", "PROVIDER_ACCEPTED_OLD_EPOCH",
                request_metadata={"if_match": version_after},
                detail=f"read_back_epoch={read_back.epoch}",
                extra={"reproduces_manager_critical_finding": True})
    ctx.log("c05", "authority_writer_validate",
            PASS if writer_refused else FAIL, detail=writer_outcome.status)
    return CaseResult(
        "c05", "stale semantic epoch rejected even with current ETag",
        "Manager reconciliation 2026-09-23 / E10-M1",
        PASS if (advanced.accepted and writer_refused) else FAIL,
        f"writer={writer_outcome.status} "
        f"provider_accepted_rollback_via_bypass={provider_accepted_rollback}",
        {"provider_accepted_rollback_via_bypass": provider_accepted_rollback})


def case_06_sequence_monotonicity(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c06", ctx.writer("c06"), transitions=2)
    head, _ = writer.read_head()
    replay = writer.commit(writer.propose(sha256_hex(b"replay"), sequence=head.sequence),
                           writer.issue_fencing_token())
    gap = writer.commit(writer.propose(sha256_hex(b"gap"), sequence=head.sequence + 2),
                        writer.issue_fencing_token())
    backwards = writer.commit(writer.propose(sha256_hex(b"back"), sequence=0),
                              writer.issue_fencing_token())
    after, _ = writer.read_head()
    for label, outcome in (("replay", replay), ("gap", gap), ("backwards", backwards)):
        ctx.log("c06", "commit_" + label,
                PASS if outcome.status == "REJECTED_SEQUENCE_NOT_STRICTLY_NEXT" else FAIL,
                detail=outcome.status)
    ok = (all(o.status == "REJECTED_SEQUENCE_NOT_STRICTLY_NEXT"
              for o in (replay, gap, backwards)) and after.sequence == head.sequence)
    return CaseResult("c06", "strict sequence monotonicity", "E-09 / BuildPlan 15.1",
                      PASS if ok else FAIL,
                      f"replay={replay.status} gap={gap.status} back={backwards.status}")


def case_07_transition_chain_validation(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c07", ctx.writer("c07"), transitions=1)
    wrong_chain = writer.commit(
        writer.propose(sha256_hex(b"x"), previous_transition_hash="0" * 64),
        writer.issue_fencing_token())
    wrong_head = writer.commit(
        writer.propose(sha256_hex(b"y"), previous_head_hash="0" * 64),
        writer.issue_fencing_token())
    good = writer.commit(writer.propose(sha256_hex(b"z")), writer.issue_fencing_token())
    ctx.log("c07", "commit_broken_chain",
            PASS if wrong_chain.status == "REJECTED_TRANSITION_CHAIN_BROKEN" else FAIL,
            detail=wrong_chain.status)
    ctx.log("c07", "commit_broken_head_link",
            PASS if wrong_head.status == "REJECTED_PREVIOUS_HEAD_HASH_MISMATCH" else FAIL,
            detail=wrong_head.status)
    ok = (wrong_chain.status == "REJECTED_TRANSITION_CHAIN_BROKEN"
          and wrong_head.status == "REJECTED_PREVIOUS_HEAD_HASH_MISMATCH"
          and good.accepted)
    return CaseResult("c07", "previous-head / transition-chain validation", "E01-H1",
                      PASS if ok else FAIL,
                      f"chain={wrong_chain.status} head_link={wrong_head.status} "
                      f"control={good.status}")


def case_08_unknown_commit_recovery(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c08", ctx.writer("c08"), transitions=1)
    lossy = _LostResponseStore(ctx.store)
    lossy_writer = RestrictedAuthorityWriter(
        lossy, prefix=ctx.prefix, namespace_id=writer.namespace_id,
        clock=ctx._clock, sequence_policy=ctx.sequence_policy)
    request = lossy_writer.propose(sha256_hex(b"unknown-commit"))
    outcome = lossy_writer.commit(request, lossy_writer.issue_fencing_token())
    head, _ = writer.read_head()
    resolved_by_reread = outcome.status == "UNKNOWN_RESOLVED_ACCEPTED"
    no_second_transition = head.accepted_transition_hash == outcome.transition_hash
    # A blind retry would mint a SECOND accepted transition for one logical
    # change. Re-presenting the same request must not advance the HEAD again.
    retry = writer.commit(request, writer.issue_fencing_token())
    after, _ = writer.read_head()
    blind_retry_blocked = (not retry.accepted and after.sequence == head.sequence)
    ctx.log("c08", "resolve_unknown_commit", PASS if resolved_by_reread else FAIL,
            detail=outcome.status,
            extra={"blind_retry_status": retry.status})
    ok = resolved_by_reread and no_second_transition and blind_retry_blocked
    return CaseResult("c08", "unknown-commit recovery by authoritative reread", "E01-M1",
                      PASS if ok else FAIL,
                      f"outcome={outcome.status} blind_retry={retry.status} "
                      f"head_sequence_stable={blind_retry_blocked}")


def case_09_journal_rebuild(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c09", ctx.writer("c09"), transitions=3)
    # An inert candidate: written to the journal, never accepted by a CAS.
    orphan = writer.propose(sha256_hex(b"never-accepted"), sequence=99)
    orphan_hash = orphan.transition.transition_hash()
    orphan_key = transition_key(ctx.prefix, writer.namespace_id, 1, 99, orphan_hash)
    ctx.store.append_transition_if_absent(orphan_key, orphan.transition.to_bytes())

    rebuilt = writer.rebuild_from_journal()
    head, _ = writer.read_head()
    orphan_excluded = orphan_key in rebuilt.orphans
    chain_ok = (rebuilt.consistent and len(rebuilt.chain) == 3
                and rebuilt.chain[-1].transition_hash() == head.accepted_transition_hash)
    ctx.log("c09", "rebuild_from_journal", PASS if chain_ok else FAIL,
            detail=rebuilt.detail,
            extra={"chain_length": len(rebuilt.chain), "orphans": len(rebuilt.orphans)})
    return CaseResult("c09", "complete journal scan / rebuild", "E01-H1 / E01-M1",
                      PASS if (chain_ok and orphan_excluded) else FAIL,
                      f"{rebuilt.detail} chain={len(rebuilt.chain)} "
                      f"orphan_excluded={orphan_excluded}")


def case_10_delayed_stale_fencing(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c10", ctx.writer("c10"), transitions=1)
    delayed_token = writer.issue_fencing_token()            # minted at epoch 1
    advanced = writer.advance_epoch(writer.issue_fencing_token())
    delayed = writer.commit(writer.propose(sha256_hex(b"delayed")), delayed_token)
    forged_future = writer.commit(writer.propose(sha256_hex(b"future")),
                                  writer.issue_fencing_token(epoch=99))
    head, _ = writer.read_head()
    ctx.log("c10", "commit_with_delayed_token",
            PASS if delayed.status == "REJECTED_FENCING_TOKEN_EPOCH_STALE" else FAIL,
            detail=delayed.status)
    ok = (advanced.accepted
          and delayed.status == "REJECTED_FENCING_TOKEN_EPOCH_STALE"
          and forged_future.status == "REJECTED_FENCING_TOKEN_EPOCH_UNKNOWN"
          and head.epoch == 2)
    return CaseResult("c10", "delayed / stale fencing rejection", "E10-M1 / 15.1",
                      PASS if ok else FAIL,
                      f"delayed={delayed.status} forged_future={forged_future.status} "
                      f"head_epoch={head.epoch}")


def case_11_competing_writers(ctx: CaseContext) -> CaseResult:
    writer_a = ctx.started("c11", ctx.writer("c11", writer_id="writer-a"))
    writer_b = RestrictedAuthorityWriter(
        ctx.store, prefix=ctx.prefix, namespace_id=writer_a.namespace_id,
        clock=ctx._clock, writer_id="writer-b", sequence_policy=ctx.sequence_policy)
    # Both read the SAME head, both are semantically valid, both attempt CAS.
    request_a = writer_a.propose(sha256_hex(b"a"))
    request_b = writer_b.propose(sha256_hex(b"b"))
    token_a = writer_a.issue_fencing_token()
    token_b = writer_b.issue_fencing_token()
    outcome_a = writer_a.commit(request_a, token_a, use_observed_snapshot=True)
    outcome_b = writer_b.commit(request_b, token_b, use_observed_snapshot=True)
    head, _ = writer_a.read_head()
    rebuilt = writer_a.rebuild_from_journal()
    exactly_one = outcome_a.accepted != outcome_b.accepted
    loser_inert = head.accepted_transition_hash != (
        outcome_b.transition_hash if outcome_a.accepted else outcome_a.transition_hash)
    ctx.log("c11", "competing_cas", PASS if exactly_one else FAIL,
            detail=f"a={outcome_a.status} b={outcome_b.status}")
    ok = (exactly_one and loser_inert and rebuilt.consistent
          and head.sequence == 1 and len(rebuilt.chain) == 1)
    return CaseResult("c11", "competing-writer race", "BuildPlan 15.1",
                      PASS if ok else FAIL,
                      f"a={outcome_a.status} b={outcome_b.status} "
                      f"head_sequence={head.sequence} chain={len(rebuilt.chain)}")


def case_12_rollback_epoch_fence(ctx: CaseContext) -> CaseResult:
    writer = ctx.started("c12", ctx.writer("c12"), transitions=1)
    pre_rollback_token = writer.issue_fencing_token()
    pre_rollback_request = writer.propose(sha256_hex(b"pre-rollback"))
    advanced = writer.advance_epoch(writer.issue_fencing_token())

    # DC-038 C/D: an epoch advance is a HEAD fence, not an accepted transition.
    # The journal must rebuild consistently IMMEDIATELY after it, before any
    # new transition exists in the new epoch.
    fenced_head, _ = writer.read_head()
    fenced_rebuild = writer.rebuild_from_journal()
    ctx.log("c12", "rebuild_immediately_after_epoch_advance",
            PASS if fenced_rebuild.consistent else FAIL,
            detail=fenced_rebuild.detail,
            extra={"head_epoch": fenced_head.epoch,
                   "head_sequence": fenced_head.sequence})

    delayed = writer.commit(pre_rollback_request, pre_rollback_token)
    post_token = writer.issue_fencing_token()
    post = writer.commit(writer.propose(sha256_hex(b"post-rollback")), post_token)
    head, _ = writer.read_head()
    post_rebuild = writer.rebuild_from_journal()
    ctx.log("c12", "pre_rollback_token_after_advance",
            PASS if delayed.status == "REJECTED_FENCING_TOKEN_EPOCH_STALE" else FAIL,
            detail=delayed.status)
    expected_first_sequence = 1 if ctx.sequence_policy == "RESET_PER_EPOCH" else 2
    ok = (advanced.accepted
          and fenced_rebuild.consistent
          and fenced_head.sequence == (0 if ctx.sequence_policy == "RESET_PER_EPOCH"
                                       else 1)
          and delayed.status == "REJECTED_FENCING_TOKEN_EPOCH_STALE"
          and post.accepted and head.epoch == 2
          and head.sequence == expected_first_sequence
          and post_rebuild.consistent)
    return CaseResult("c12", "rollback epoch advance fences prior tokens", "E10-M1",
                      PASS if ok else FAIL,
                      f"advance={advanced.status} fenced_rebuild={fenced_rebuild.detail} "
                      f"fenced_sequence={fenced_head.sequence} "
                      f"pre_rollback={delayed.status} post={post.status} "
                      f"epoch={head.epoch} sequence={head.sequence} "
                      f"post_rebuild={post_rebuild.detail}",
                      {"sequence_policy": ctx.sequence_policy})


def case_13_bypass_prevention(ctx: CaseContext) -> CaseResult:
    """Can an ORDINARY caller overwrite the authoritative HEAD directly?

    Only a provider-side permission denial answers this. If no separate
    ordinary principal is configured, the answer is UNPROVEN — never PASS.
    """
    writer = ctx.started("c13", ctx.writer("c13"), transitions=1)
    key = head_key(ctx.prefix, writer.namespace_id)
    head, version = writer.read_head()
    if ctx.ordinary_store is None:
        ctx.log("c13", "bypass_attempt", UNPROVEN,
                detail="no ordinary principal configured")
        return CaseResult(
            "c13", "bypass prevention (ordinary caller cannot write HEAD)",
            "Manager reconciliation 2026-09-23", UNPROVEN,
            "No second principal configured. A refusal produced by harness code "
            "would prove nothing; an enforceable boundary is a provider-side "
            "permission denial. Supply --ordinary-profile to decide this case.")

    forged = HeadRecord(
        namespace_id=writer.namespace_id, epoch=head.epoch, sequence=head.sequence + 1,
        accepted_transition_hash="f" * 64, previous_head_hash=head.head_hash(),
        accepted_at_ns=ctx._clock()).to_bytes()
    denied = False
    detail = ""
    try:
        ctx.ordinary_store.raw_put_head(key, forged, expected_version=version)
        detail = "ORDINARY_PRINCIPAL_WROTE_AUTHORITATIVE_HEAD"
    except AccessDenied as exc:
        denied, detail = True, "ACCESS_DENIED:" + str(exc)
    except PreconditionFailed as exc:
        # A precondition refusal is NOT a permission boundary: with the right
        # ETag the same caller would have succeeded.
        detail = "PRECONDITION_ONLY_NOT_A_PERMISSION_BOUNDARY:" + str(exc)
    after, _ = writer.read_head()
    unchanged = after.accepted_transition_hash == head.accepted_transition_hash
    ctx.log("c13", "bypass_attempt", PASS if denied else FAIL,
            request_metadata={"key": key, "if_match": version,
                              "principal_label": ctx.ordinary_principal_label},
            detail=detail)
    return CaseResult("c13", "bypass prevention (ordinary caller cannot write HEAD)",
                      "Manager reconciliation 2026-09-23",
                      PASS if (denied and unchanged) else FAIL,
                      detail + f" head_unchanged={unchanged}")


def case_14_evidence_capture(ctx: CaseContext) -> CaseResult:
    required = {"run_id", "seq", "ts_utc", "ts_ns", "provider_id", "case_id",
                "operation", "outcome", "request_metadata", "response_metadata"}
    records = ctx.recorder.records
    missing_fields = [r["seq"] for r in records if not required.issubset(r)]
    cases_covered = {r["case_id"] for r in records}
    ok = bool(records) and not missing_fields and len(cases_covered) >= 10
    return CaseResult("c14", "evidence capture", "commission item 14",
                      PASS if ok else FAIL,
                      f"records={len(records)} cases_with_evidence={len(cases_covered)} "
                      f"records_missing_fields={len(missing_fields)}",
                      {"cases_covered": sorted(cases_covered)})


def case_15_manifest_determinism(ctx: CaseContext) -> CaseResult:
    from .evidence import compute_manifest
    first = compute_manifest(ctx.recorder.run_dir)
    second = compute_manifest(ctx.recorder.run_dir)
    stable = first["evidence_digest"] == second["evidence_digest"]
    ok = stable and first["files"]
    return CaseResult("c15", "deterministic SHA-256 evidence manifest",
                      "commission item 15", PASS if ok else FAIL,
                      f"stable={stable} files={len(first['files'])} "
                      f"digest={first['evidence_digest'][:16]}...",
                      {"evidence_digest": first["evidence_digest"]})


# (case_id, function). The id is explicit so a crashing case still reports
# under its own id instead of being lost or mislabelled.
ALL_CASES: Tuple[Tuple[str, Callable[[CaseContext], CaseResult]], ...] = (
    ("c01", case_01_strong_read_after_write),
    ("c02", case_02_immutable_create_only),
    ("c03", case_03_conditional_head_cas),
    ("c04", case_04_stale_etag_rejected),
    ("c05", case_05_stale_epoch_with_current_etag),
    ("c06", case_06_sequence_monotonicity),
    ("c07", case_07_transition_chain_validation),
    ("c08", case_08_unknown_commit_recovery),
    ("c09", case_09_journal_rebuild),
    ("c10", case_10_delayed_stale_fencing),
    ("c11", case_11_competing_writers),
    ("c12", case_12_rollback_epoch_fence),
    ("c13", case_13_bypass_prevention),
    ("c14", case_14_evidence_capture),
    ("c15", case_15_manifest_determinism),
)


def run_all(ctx: CaseContext) -> List[CaseResult]:
    results: List[CaseResult] = []
    for case_id, case in ALL_CASES:
        try:
            result = case(ctx)
        except Exception as exc:                      # a crash is a FAIL, never a skip
            result = CaseResult(case_id, case.__name__, "harness", FAIL,
                                f"UNHANDLED_EXCEPTION:{type(exc).__name__}:{exc}")
            try:
                ctx.log(case_id, "case_execution", FAIL, detail=result.detail)
            except Exception:
                pass
        if result.case_id != case_id:
            raise AssertionError(f"CASE_ID_MISMATCH:{case_id}:{result.case_id}")
        results.append(result)
    return results
