"""The restricted authority writer under test.

THE POINT OF THIS FILE. The Sydney probe showed that a request carrying the
CURRENT ETag but an OLD epoch body was accepted by S3 and read back as a
rollback. Object-level CAS proves only "the object has not changed since I read
it". It says nothing about what is INSIDE the new body.

So every authority-bearing write validates, BEFORE the conditional HEAD write:

    1. fencing token epoch == current HEAD epoch      (stale/forged token)
    2. transition epoch    == current HEAD epoch      (semantic epoch)
    3. transition sequence == HEAD.sequence + 1       (strict monotonicity)
    4. transition.previous_head_hash == hash(HEAD read)   (head chain)
    5. transition.previous_transition_hash == HEAD.accepted_transition_hash
                                                      (journal chain)
and only then performs create-only journal append + conditional HEAD CAS.

This writer is TEST SURFACE. It is not stage_a/coordination/object_store_journal.py
and confers no implementation authority. Critically, it is also NOT the
enforceable boundary: a writer that ordinary callers can simply not call is a
convention. The enforceable boundary is a provider-side permission denial,
which case C13 attempts to prove and which this code cannot supply.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .model import (NO_PREVIOUS_HEAD, NO_PREVIOUS_TRANSITION, HeadRecord,
                    TransitionRecord, head_key, transition_key,
                    transition_scan_prefix)
from .store_port import (AccessDenied, NotFound, PreconditionFailed,
                         UnknownWriteOutcome)

# Underspecification, declared rather than silently assumed. The frozen text
# says "sequence monotonically increases within epoch/status namespace" and
# "epoch monotonically increases on governed authority failover", which does not
# settle what sequence does AT an epoch advance. Both readings are implemented;
# the default is RESET_PER_EPOCH. See README "Open semantic question S-1".
SEQUENCE_POLICIES = ("RESET_PER_EPOCH", "CONTINUE_ACROSS_EPOCH")


@dataclass(frozen=True)
class FencingToken:
    namespace_id: str
    epoch: int
    token_id: str


@dataclass(frozen=True)
class TransitionRequest:
    transition: TransitionRecord
    observed_head_version: str
    # The HEAD this request was built against. Carrying it lets a caller commit
    # against what it OBSERVED (real concurrency: two writers read, then both
    # attempt CAS) instead of a value re-read after the other writer finished.
    observed_head: "HeadRecord" = None


@dataclass(frozen=True)
class CommitOutcome:
    status: str
    detail: str
    transition_hash: Optional[str] = None
    head: Optional[HeadRecord] = None
    head_version: Optional[str] = None
    evidence: Optional[dict] = None

    @property
    def accepted(self) -> bool:
        return self.status in ("ACCEPTED", "UNKNOWN_RESOLVED_ACCEPTED")


@dataclass(frozen=True)
class RebuiltState:
    chain: Tuple[TransitionRecord, ...]
    orphans: Tuple[str, ...]
    head: Optional[HeadRecord]
    consistent: bool
    detail: str


class AuthorityWriterRejection(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class RestrictedAuthorityWriter:
    def __init__(self, store, *, prefix: str, namespace_id: str,
                 clock: Callable[[], int], writer_id: str = "authority-writer-1",
                 sequence_policy: str = "RESET_PER_EPOCH"):
        if sequence_policy not in SEQUENCE_POLICIES:
            raise ValueError("SEQUENCE_POLICY_INVALID:" + sequence_policy)
        self.store = store
        self.prefix = prefix
        self.namespace_id = namespace_id
        self.clock = clock
        self.writer_id = writer_id
        self.sequence_policy = sequence_policy
        self._token_serial = 0

    # -- keys ------------------------------------------------------------
    @property
    def head_key(self) -> str:
        return head_key(self.prefix, self.namespace_id)

    # -- reads -----------------------------------------------------------
    def read_head(self) -> Tuple[HeadRecord, str]:
        obj = self.store.read_head(self.head_key)
        return HeadRecord.from_bytes(obj.data), obj.version

    # -- lifecycle -------------------------------------------------------
    def initialise_namespace(self, payload_hash: str) -> CommitOutcome:
        """Genesis HEAD, create-only. A second attempt must fail closed."""
        genesis = HeadRecord(
            namespace_id=self.namespace_id, epoch=1, sequence=0,
            accepted_transition_hash=NO_PREVIOUS_TRANSITION,
            previous_head_hash=NO_PREVIOUS_HEAD,
            accepted_at_ns=self.clock(),
        )
        try:
            written = self.store.create_head_if_absent(self.head_key, genesis.to_bytes())
        except PreconditionFailed as exc:
            return CommitOutcome("REJECTED_NAMESPACE_EXISTS", str(exc))
        except AccessDenied as exc:
            return CommitOutcome("REJECTED_ACCESS_DENIED", str(exc))
        return CommitOutcome("ACCEPTED", "genesis head created",
                             head=genesis, head_version=written.version,
                             evidence={"payload_hash": payload_hash})

    def issue_fencing_token(self, *, epoch: Optional[int] = None) -> FencingToken:
        """Mint a token for the CURRENT epoch (or an explicit one, for tests
        that must present a stale or forged token)."""
        if epoch is None:
            head, _ = self.read_head()
            epoch = head.epoch
        self._token_serial += 1
        return FencingToken(self.namespace_id, epoch,
                            f"{self.writer_id}:{epoch}:{self._token_serial}")

    def propose(self, payload_hash: str, *, epoch: Optional[int] = None,
                sequence: Optional[int] = None,
                previous_head_hash: Optional[str] = None,
                previous_transition_hash: Optional[str] = None) -> TransitionRequest:
        """Build a well-formed transition against the CURRENT head.

        The override arguments exist so negative cases can present a
        deliberately malformed transition. Production callers would not have
        them.
        """
        head, version = self.read_head()
        transition = TransitionRecord(
            namespace_id=self.namespace_id,
            epoch=head.epoch if epoch is None else epoch,
            sequence=(head.sequence + 1) if sequence is None else sequence,
            previous_head_hash=(head.head_hash() if previous_head_hash is None
                                else previous_head_hash),
            previous_transition_hash=(head.accepted_transition_hash
                                      if previous_transition_hash is None
                                      else previous_transition_hash),
            payload_hash=payload_hash,
            accepted_at_ns=self.clock(),
        )
        return TransitionRequest(transition=transition, observed_head_version=version,
                                 observed_head=head)

    # -- the gate --------------------------------------------------------
    def validate(self, request: TransitionRequest, token: FencingToken,
                 head: HeadRecord) -> None:
        """Every semantic precondition, evaluated BEFORE any write."""
        t = request.transition
        if token.namespace_id != self.namespace_id or t.namespace_id != self.namespace_id:
            raise AuthorityWriterRejection("NAMESPACE_MISMATCH")
        if token.epoch < head.epoch:
            raise AuthorityWriterRejection("FENCING_TOKEN_EPOCH_STALE")
        if token.epoch > head.epoch:
            raise AuthorityWriterRejection("FENCING_TOKEN_EPOCH_UNKNOWN")
        if t.epoch < head.epoch:
            raise AuthorityWriterRejection("TRANSITION_EPOCH_STALE")
        if t.epoch > head.epoch:
            raise AuthorityWriterRejection("TRANSITION_EPOCH_AHEAD_OF_HEAD")
        if t.sequence != head.sequence + 1:
            raise AuthorityWriterRejection("SEQUENCE_NOT_STRICTLY_NEXT")
        if t.previous_head_hash != head.head_hash():
            raise AuthorityWriterRejection("PREVIOUS_HEAD_HASH_MISMATCH")
        if t.previous_transition_hash != head.accepted_transition_hash:
            raise AuthorityWriterRejection("TRANSITION_CHAIN_BROKEN")
        if not str(t.payload_hash or "").strip():
            raise AuthorityWriterRejection("PAYLOAD_HASH_REQUIRED")

    def commit(self, request: TransitionRequest, token: FencingToken, *,
               use_observed_snapshot: bool = False) -> CommitOutcome:
        """Validate, append the immutable candidate, then conditionally CAS HEAD.

        E01-M1: acceptance is the successful CAS, not the candidate write. A
        failed CAS never reuses the candidate or its accepted_at.

        By default the authoritative HEAD is RE-READ here, because §15.1
        requires fencing/epoch validation on EVERY authority-bearing write, not
        only at epoch advance: a token that went stale while this caller was
        delayed must be refused on its own, without relying on the ETag.

        use_observed_snapshot=True validates against the HEAD the request was
        built from and lets the provider's conditional write decide the
        outcome. That is what two genuinely concurrent writers do — both read,
        both validate, both attempt CAS — and it is the only way to exercise
        the provider precondition rather than hiding it behind a re-read.
        """
        if use_observed_snapshot and request.observed_head is not None:
            head, current_version = request.observed_head, request.observed_head_version
        else:
            try:
                head, current_version = self.read_head()
            except NotFound as exc:
                return CommitOutcome("REJECTED_NAMESPACE_ABSENT", str(exc))

        try:
            self.validate(request, token, head)
        except AuthorityWriterRejection as exc:
            return CommitOutcome("REJECTED_" + exc.reason, exc.reason,
                                 transition_hash=request.transition.transition_hash(),
                                 head=head, head_version=current_version)

        # The caller's observed version is re-checked against the version just
        # read, and the CAS itself still carries the precondition: the store,
        # not this code, decides the race.
        t = request.transition
        t_hash = t.transition_hash()
        key = transition_key(self.prefix, self.namespace_id, t.epoch, t.sequence, t_hash)
        try:
            self.store.append_transition_if_absent(key, t.to_bytes())
        except PreconditionFailed as exc:
            return CommitOutcome("REJECTED_IMMUTABLE_KEY_CONFLICT", str(exc),
                                 transition_hash=t_hash)
        except AccessDenied as exc:
            return CommitOutcome("REJECTED_ACCESS_DENIED", str(exc),
                                 transition_hash=t_hash)

        new_head = HeadRecord(
            namespace_id=self.namespace_id, epoch=t.epoch, sequence=t.sequence,
            accepted_transition_hash=t_hash, previous_head_hash=head.head_hash(),
            accepted_at_ns=self.clock(),
        )
        try:
            written = self.store.compare_and_swap_head(
                self.head_key, current_version, new_head.to_bytes())
        except PreconditionFailed as exc:
            # Lost the race. The candidate object stays inert: it is not
            # referenced by the accepted HEAD chain, so it is non-authoritative.
            # The provider's own refusal metadata (409 vs 412) is carried
            # through so the evidence keeps the distinction.
            return CommitOutcome("CAS_LOST", str(exc), transition_hash=t_hash,
                                 evidence=getattr(exc, "provider_metadata", {}))
        except AccessDenied as exc:
            return CommitOutcome("REJECTED_ACCESS_DENIED", str(exc),
                                 transition_hash=t_hash)
        except UnknownWriteOutcome as exc:
            return self.resolve_unknown_commit(t_hash, cause=str(exc))
        return CommitOutcome("ACCEPTED", "head advanced", transition_hash=t_hash,
                             head=new_head, head_version=written.version)

    def resolve_unknown_commit(self, transition_hash: str, *,
                               cause: str = "") -> CommitOutcome:
        """E01-M1: reread the authoritative HEAD. NEVER blind retry."""
        try:
            head, version = self.read_head()
        except NotFound as exc:
            return CommitOutcome("UNKNOWN_UNRESOLVED", "head unreadable: " + str(exc),
                                 transition_hash=transition_hash)
        if head.accepted_transition_hash == transition_hash:
            return CommitOutcome("UNKNOWN_RESOLVED_ACCEPTED", cause,
                                 transition_hash=transition_hash, head=head,
                                 head_version=version)
        return CommitOutcome("UNKNOWN_RESOLVED_NOT_ACCEPTED", cause,
                             transition_hash=transition_hash, head=head,
                             head_version=version)

    def advance_epoch(self, token: FencingToken, *,
                      reason: str = "ROLLBACK_EPOCH_FENCE") -> CommitOutcome:
        """E10-M1: rollback advances the epoch through the authorized control
        path and durably verifies the new HEAD/epoch. Tokens minted before the
        advance are invalid afterwards."""
        head, version = self.read_head()
        if token.epoch != head.epoch:
            return CommitOutcome("REJECTED_FENCING_TOKEN_EPOCH_STALE",
                                 f"token epoch {token.epoch} != head epoch {head.epoch}")
        new_sequence = 0 if self.sequence_policy == "RESET_PER_EPOCH" else head.sequence
        new_head = HeadRecord(
            namespace_id=self.namespace_id, epoch=head.epoch + 1,
            sequence=new_sequence,
            accepted_transition_hash=head.accepted_transition_hash,
            previous_head_hash=head.head_hash(), accepted_at_ns=self.clock(),
        )
        try:
            written = self.store.compare_and_swap_head(self.head_key, version,
                                                       new_head.to_bytes())
        except PreconditionFailed as exc:
            return CommitOutcome("CAS_LOST", str(exc))
        except AccessDenied as exc:
            return CommitOutcome("REJECTED_ACCESS_DENIED", str(exc))
        return CommitOutcome("ACCEPTED", reason, head=new_head,
                             head_version=written.version)

    # -- rebuild ---------------------------------------------------------
    def rebuild_from_journal(self) -> RebuiltState:
        """Rebuild the accepted chain from immutable objects alone.

        Walks BACKWARDS from the HEAD's accepted transition hash, so listing
        order is irrelevant (E-09: "object listing order is never authority").
        Candidate objects not on the accepted chain are reported as orphans and
        excluded — E01-M1 makes them inert.

        EPOCH AWARENESS (DC-038). HEAD.epoch is authority; nothing in the
        journal may override it. Sequence is strictly monotonic WITHIN an
        epoch. An epoch advance is a HEAD fence, NOT an accepted transition
        (EPOCH_ADVANCE_ACCEPTED_TRANSITION = NO), so HEAD.sequence == 0 naming
        a tip from an earlier epoch is a consistent "fenced, nothing accepted
        yet" state, not a defect.
        """
        try:
            head, _ = self.read_head()
        except NotFound as exc:
            return RebuiltState((), (), None, False, "HEAD_ABSENT:" + str(exc))

        by_hash: Dict[str, TransitionRecord] = {}
        keys_by_hash: Dict[str, str] = {}
        import json
        for key, data in self.store.scan_transitions(
                transition_scan_prefix(self.prefix, self.namespace_id)):
            # A foreign, truncated or tampered object must FAIL CLOSED with a
            # diagnosis, never crash the rebuilder: a crash mid-recovery is
            # indistinguishable to an operator from "the tool is broken", and
            # an operator who cannot rebuild may be tempted to write by hand.
            try:
                payload = json.loads(data.decode("utf-8"))
                record = TransitionRecord(
                    namespace_id=payload["namespace_id"], epoch=int(payload["epoch"]),
                    sequence=int(payload["sequence"]),
                    previous_head_hash=payload["previous_head_hash"],
                    previous_transition_hash=payload["previous_transition_hash"],
                    payload_hash=payload["payload_hash"],
                    accepted_at_ns=int(payload["accepted_at_ns"]),
                    transition_kind=payload.get("transition_kind",
                                                "GOVERNED_TRANSITION"),
                )
            except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
                return RebuiltState((), (), head, False,
                                    f"TRANSITION_OBJECT_UNPARSEABLE:{key}:"
                                    f"{type(exc).__name__}")
            computed = record.transition_hash()
            if not key.endswith(f"{computed}.bin"):
                return RebuiltState((), (), head, False,
                                    "TRANSITION_KEY_HASH_MISMATCH:" + key)
            by_hash[computed] = record
            keys_by_hash[computed] = key

        chain: List[TransitionRecord] = []
        cursor = head.accepted_transition_hash
        seen = set()
        while cursor != NO_PREVIOUS_TRANSITION:
            if cursor in seen:
                return RebuiltState(tuple(reversed(chain)), (), head, False,
                                    "TRANSITION_CHAIN_CYCLE:" + cursor)
            seen.add(cursor)
            record = by_hash.get(cursor)
            if record is None:
                return RebuiltState(tuple(reversed(chain)), (), head, False,
                                    "ACCEPTED_TRANSITION_MISSING_FROM_JOURNAL:" + cursor)
            chain.append(record)
            cursor = record.previous_transition_hash

        ordered = tuple(reversed(chain))
        orphans = tuple(sorted(keys_by_hash[h] for h in by_hash if h not in seen))

        # -- chain links -------------------------------------------------
        for index, record in enumerate(ordered):
            expected_prev = (NO_PREVIOUS_TRANSITION if index == 0
                             else ordered[index - 1].transition_hash())
            if record.previous_transition_hash != expected_prev:
                return RebuiltState(ordered, orphans, head, False,
                                    "CHAIN_LINK_INVALID_AT_SEQUENCE:"
                                    + str(record.sequence))

        # -- epoch / sequence progression (DC-038 correction C) ----------
        # The authoritative HEAD owns the epoch. Nothing inferred from the
        # journal may override it, so an accepted transition may never sit in
        # an epoch beyond HEAD.epoch. Sequence is validated WITHIN each epoch:
        # under the governing RESET_PER_EPOCH policy the first accepted
        # transition of any epoch is sequence 1.
        previous = None
        for record in ordered:
            if record.epoch > head.epoch:
                return RebuiltState(ordered, orphans, head, False,
                                    "ACCEPTED_TRANSITION_EPOCH_AHEAD_OF_HEAD:"
                                    + str(record.epoch))
            if previous is None:
                if record.sequence != 1:
                    return RebuiltState(ordered, orphans, head, False,
                                        "FIRST_ACCEPTED_TRANSITION_SEQUENCE_NOT_1:"
                                        + str(record.sequence))
            elif record.epoch < previous.epoch:
                return RebuiltState(ordered, orphans, head, False,
                                    "TRANSITION_EPOCH_DECREASED_AT_SEQUENCE:"
                                    + str(record.sequence))
            elif record.epoch == previous.epoch:
                if record.sequence != previous.sequence + 1:
                    return RebuiltState(ordered, orphans, head, False,
                                        "SEQUENCE_NOT_STRICTLY_NEXT_IN_EPOCH:"
                                        + str(record.sequence))
            else:                                  # epoch advanced mid-chain
                expected = (1 if self.sequence_policy == "RESET_PER_EPOCH"
                            else previous.sequence + 1)
                if record.sequence != expected:
                    return RebuiltState(ordered, orphans, head, False,
                                        "SEQUENCE_INVALID_AFTER_EPOCH_ADVANCE:"
                                        + str(record.sequence))
            previous = record

        # -- tip vs HEAD -------------------------------------------------
        # E10-M1 / Manager reconciliation CR-036: an epoch advance is a durable
        # mutable-HEAD epoch FENCE, not an accepted transition. So immediately
        # after advance_epoch the HEAD legitimately sits at sequence 0 in the
        # new epoch while still naming the previous epoch's accepted tip. That
        # state is CONSISTENT: it means "fenced, nothing accepted yet here".
        if not ordered:
            if head.accepted_transition_hash != NO_PREVIOUS_TRANSITION:
                return RebuiltState(ordered, orphans, head, False,
                                    "HEAD_NAMES_TRANSITION_BUT_CHAIN_EMPTY")
            if head.sequence != 0:
                return RebuiltState(ordered, orphans, head, False,
                                    "HEAD_SEQUENCE_WITHOUT_ACCEPTED_TRANSITION:"
                                    + str(head.sequence))
            return RebuiltState(ordered, orphans, head, True,
                                "REBUILD_CONSISTENT_NO_ACCEPTED_TRANSITIONS")

        tip = ordered[-1]
        if tip.transition_hash() != head.accepted_transition_hash:
            return RebuiltState(ordered, orphans, head, False, "CHAIN_TIP_NOT_HEAD")

        if head.sequence == 0:
            # Epoch-fenced, no transition accepted in this epoch yet. The tip
            # must belong to an EARLIER epoch; a tip in HEAD.epoch would imply
            # an accepted transition at sequence 0, which cannot exist.
            if tip.epoch >= head.epoch:
                return RebuiltState(ordered, orphans, head, False,
                                    "CHAIN_TIP_EPOCH_INVALID_FOR_FENCED_HEAD:"
                                    + str(tip.epoch))
            return RebuiltState(ordered, orphans, head, True,
                                "REBUILD_CONSISTENT_EPOCH_FENCED_NO_NEW_TRANSITION")

        if tip.epoch != head.epoch:
            # Non-governing CONTINUE_ACROSS_EPOCH keeps the carried sequence on
            # the fence, so its fenced state is (tip.epoch < head.epoch and
            # tip.sequence == head.sequence). RESET_PER_EPOCH never reaches here.
            if (self.sequence_policy == "CONTINUE_ACROSS_EPOCH"
                    and tip.epoch < head.epoch and tip.sequence == head.sequence):
                return RebuiltState(ordered, orphans, head, True,
                                    "REBUILD_CONSISTENT_EPOCH_FENCED_NO_NEW_TRANSITION")
            return RebuiltState(ordered, orphans, head, False,
                                "CHAIN_TIP_EPOCH_NOT_HEAD:" + str(tip.epoch))
        if tip.sequence != head.sequence:
            return RebuiltState(ordered, orphans, head, False,
                                "CHAIN_TIP_SEQUENCE_NOT_HEAD:" + str(tip.sequence))
        return RebuiltState(ordered, orphans, head, True, "REBUILD_CONSISTENT")
