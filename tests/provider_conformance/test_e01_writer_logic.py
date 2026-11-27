"""Logic-only unit tests for the restricted authority writer.

No network, no boto3, no credentials. These prove the WRITER's validation
order and outcomes. They are explicitly NOT provider evidence (E07-M1): the
in-memory store models a well-behaved provider and can prove nothing about a
real one.
"""
from __future__ import annotations

import itertools
import unittest

from tests.provider_conformance.authority_writer import (FencingToken,
                                                         RestrictedAuthorityWriter,
                                                         SEQUENCE_POLICIES)
from tests.provider_conformance.canonical import sha256_hex
from tests.provider_conformance.memory_store import MemoryObjectStore
from tests.provider_conformance.model import (NO_PREVIOUS_TRANSITION, HeadRecord,
                                              head_key, is_authority_key,
                                              parse_transition_key, probe_key,
                                              sequence_from_transition_key,
                                              transition_key,
                                              transition_scan_prefix)
from tests.provider_conformance.store_port import (AccessDenied, NotFound,
                                                   PreconditionFailed)

PREFIX = "unit"


def new_writer(store=None, *, namespace="ns-1", policy="RESET_PER_EPOCH",
               writer_id="authority-writer-1"):
    store = store or MemoryObjectStore()
    counter = itertools.count(1_000)
    return RestrictedAuthorityWriter(store, prefix=PREFIX, namespace_id=namespace,
                                     clock=lambda: next(counter),
                                     writer_id=writer_id, sequence_policy=policy)


def started(writer, transitions=0):
    writer.initialise_namespace(sha256_hex(b"genesis"))
    for index in range(transitions):
        outcome = writer.commit(writer.propose(sha256_hex(f"p{index}".encode())),
                                writer.issue_fencing_token())
        assert outcome.accepted, outcome.status
    return writer


class GenesisAndCas(unittest.TestCase):
    def test_genesis_is_create_only(self):
        writer = new_writer()
        first = writer.initialise_namespace(sha256_hex(b"g"))
        second = writer.initialise_namespace(sha256_hex(b"g"))
        self.assertTrue(first.accepted)
        self.assertEqual(second.status, "REJECTED_NAMESPACE_EXISTS")
        head, _ = writer.read_head()
        self.assertEqual((head.epoch, head.sequence), (1, 0))

    def test_commit_advances_head_and_writes_immutable_transition(self):
        writer = started(new_writer())
        outcome = writer.commit(writer.propose(sha256_hex(b"p")),
                                writer.issue_fencing_token())
        self.assertTrue(outcome.accepted)
        head, _ = writer.read_head()
        self.assertEqual(head.sequence, 1)
        self.assertEqual(head.accepted_transition_hash, outcome.transition_hash)
        key = transition_key(PREFIX, writer.namespace_id, 1, 1, outcome.transition_hash)
        self.assertTrue(writer.store.read_transition(key).data)

    def test_commit_on_absent_namespace_fails_closed(self):
        writer = new_writer()
        with self.assertRaises(NotFound):
            writer.propose(sha256_hex(b"p"))

    def test_stale_observed_version_loses_the_cas(self):
        """The provider precondition, not the writer, decides this one."""
        writer = started(new_writer())
        stale = writer.propose(sha256_hex(b"stale"))
        stale_snapshot = stale
        self.assertTrue(writer.commit(writer.propose(sha256_hex(b"win")),
                                      writer.issue_fencing_token()).accepted)
        # Same sequence as the winner: refused semantically, before any CAS.
        replay = writer.commit(stale, writer.issue_fencing_token())
        self.assertEqual(replay.status, "REJECTED_SEQUENCE_NOT_STRICTLY_NEXT")
        # Self-consistent against its own snapshot, but that snapshot is now
        # stale: the PROVIDER precondition refuses it, not the writer.
        writer.commit(writer.propose(sha256_hex(b"advance2")),
                      writer.issue_fencing_token())
        head, _ = writer.read_head()
        lost = writer.commit(stale_snapshot, writer.issue_fencing_token(),
                             use_observed_snapshot=True)
        self.assertEqual(lost.status, "CAS_LOST")
        after, _ = writer.read_head()
        self.assertEqual(after.accepted_transition_hash, head.accepted_transition_hash)


class SemanticPreconditions(unittest.TestCase):
    """Each precondition is rejected INDEPENDENTLY, before the CAS."""

    def setUp(self):
        self.writer = started(new_writer(), transitions=1)
        self.head, _ = self.writer.read_head()

    def _commit(self, **overrides):
        return self.writer.commit(self.writer.propose(sha256_hex(b"x"), **overrides),
                                  self.writer.issue_fencing_token())

    def test_stale_epoch_rejected_even_though_etag_is_current(self):
        advanced = self.writer.advance_epoch(self.writer.issue_fencing_token())
        self.assertTrue(advanced.accepted)
        head, version = self.writer.read_head()
        outcome = self._commit(epoch=head.epoch - 1, sequence=head.sequence + 1)
        self.assertEqual(outcome.status, "REJECTED_TRANSITION_EPOCH_STALE")
        # The request really did hold the current ETag: the refusal is semantic.
        self.assertEqual(self.writer.propose(sha256_hex(b"x")).observed_head_version,
                         version)
        after, _ = self.writer.read_head()
        self.assertEqual(after.epoch, head.epoch)

    def test_future_epoch_rejected(self):
        self.assertEqual(self._commit(epoch=self.head.epoch + 1).status,
                         "REJECTED_TRANSITION_EPOCH_AHEAD_OF_HEAD")

    def test_sequence_must_be_strictly_next(self):
        for sequence in (self.head.sequence, self.head.sequence + 2, 0):
            self.assertEqual(self._commit(sequence=sequence).status,
                             "REJECTED_SEQUENCE_NOT_STRICTLY_NEXT", sequence)

    def test_previous_head_hash_must_match(self):
        self.assertEqual(self._commit(previous_head_hash="0" * 64).status,
                         "REJECTED_PREVIOUS_HEAD_HASH_MISMATCH")

    def test_transition_chain_must_match(self):
        self.assertEqual(self._commit(previous_transition_hash="0" * 64).status,
                         "REJECTED_TRANSITION_CHAIN_BROKEN")

    def test_payload_hash_required(self):
        outcome = self.writer.commit(self.writer.propose("   "),
                                     self.writer.issue_fencing_token())
        self.assertEqual(outcome.status, "REJECTED_PAYLOAD_HASH_REQUIRED")

    def test_rejections_write_nothing(self):
        before = dict(self.writer.store._objects)
        for overrides in ({"epoch": 99}, {"sequence": 99},
                          {"previous_head_hash": "0" * 64},
                          {"previous_transition_hash": "0" * 64}):
            self._commit(**overrides)
        self.assertEqual(self.writer.store._objects, before)


class FencingAndRollback(unittest.TestCase):
    def test_stale_token_rejected_after_epoch_advance(self):
        writer = started(new_writer(), transitions=1)
        delayed_token = writer.issue_fencing_token()
        delayed_request = writer.propose(sha256_hex(b"delayed"))
        self.assertTrue(writer.advance_epoch(writer.issue_fencing_token()).accepted)
        outcome = writer.commit(delayed_request, delayed_token)
        self.assertEqual(outcome.status, "REJECTED_FENCING_TOKEN_EPOCH_STALE")

    def test_forged_future_token_rejected(self):
        writer = started(new_writer(), transitions=1)
        outcome = writer.commit(writer.propose(sha256_hex(b"f")),
                                writer.issue_fencing_token(epoch=99))
        self.assertEqual(outcome.status, "REJECTED_FENCING_TOKEN_EPOCH_UNKNOWN")

    def test_epoch_advance_requires_current_token(self):
        writer = started(new_writer(), transitions=1)
        stale = writer.issue_fencing_token()
        self.assertTrue(writer.advance_epoch(writer.issue_fencing_token()).accepted)
        second = writer.advance_epoch(stale)
        self.assertEqual(second.status, "REJECTED_FENCING_TOKEN_EPOCH_STALE")

    def test_post_rollback_writes_work_under_the_new_epoch(self):
        writer = started(new_writer(), transitions=1)
        writer.advance_epoch(writer.issue_fencing_token())
        outcome = writer.commit(writer.propose(sha256_hex(b"post")),
                                writer.issue_fencing_token())
        self.assertTrue(outcome.accepted, outcome.status)
        head, _ = writer.read_head()
        self.assertEqual(head.epoch, 2)

    def test_both_sequence_policies_are_implemented(self):
        self.assertEqual(SEQUENCE_POLICIES,
                         ("RESET_PER_EPOCH", "CONTINUE_ACROSS_EPOCH"))
        for policy, expected in (("RESET_PER_EPOCH", 0), ("CONTINUE_ACROSS_EPOCH", 1)):
            writer = started(new_writer(policy=policy), transitions=1)
            writer.advance_epoch(writer.issue_fencing_token())
            head, _ = writer.read_head()
            self.assertEqual(head.sequence, expected, policy)
        with self.assertRaises(ValueError):
            new_writer(policy="INVENTED")


class UnknownCommit(unittest.TestCase):
    def test_unknown_outcome_resolves_by_reread_when_write_landed(self):
        store = MemoryObjectStore()
        writer = started(new_writer(store), transitions=1)
        store.fail_next_cas_as_unknown = True
        store.unknown_write_applies = True
        outcome = writer.commit(writer.propose(sha256_hex(b"u")),
                                writer.issue_fencing_token())
        self.assertEqual(outcome.status, "UNKNOWN_RESOLVED_ACCEPTED")
        self.assertTrue(outcome.accepted)
        head, _ = writer.read_head()
        self.assertEqual(head.accepted_transition_hash, outcome.transition_hash)

    def test_unknown_outcome_resolves_not_accepted_when_write_did_not_land(self):
        store = MemoryObjectStore()
        writer = started(new_writer(store), transitions=1)
        before, _ = writer.read_head()
        store.fail_next_cas_as_unknown = True
        store.unknown_write_applies = False
        outcome = writer.commit(writer.propose(sha256_hex(b"u")),
                                writer.issue_fencing_token())
        self.assertEqual(outcome.status, "UNKNOWN_RESOLVED_NOT_ACCEPTED")
        self.assertFalse(outcome.accepted)
        after, _ = writer.read_head()
        self.assertEqual(after.accepted_transition_hash,
                         before.accepted_transition_hash)

    def test_replaying_the_same_request_cannot_mint_a_second_acceptance(self):
        store = MemoryObjectStore()
        writer = started(new_writer(store), transitions=1)
        request = writer.propose(sha256_hex(b"once"))
        first = writer.commit(request, writer.issue_fencing_token())
        self.assertTrue(first.accepted)
        head_after_first, _ = writer.read_head()
        replay = writer.commit(request, writer.issue_fencing_token())
        self.assertFalse(replay.accepted)
        head_after_replay, _ = writer.read_head()
        self.assertEqual(head_after_replay.accepted_transition_hash,
                         head_after_first.accepted_transition_hash)
        self.assertEqual(head_after_replay.sequence, head_after_first.sequence)

    def test_retry_requires_a_fresh_transition_identity(self):
        """E01-M1: fresh accepted_at -> fresh hash -> fresh immutable key."""
        writer = started(new_writer(), transitions=1)
        request = writer.propose(sha256_hex(b"retry"))
        retried = request.transition.with_accepted_at(request.transition.accepted_at_ns + 1)
        self.assertNotEqual(retried.transition_hash(),
                            request.transition.transition_hash())


class Concurrency(unittest.TestCase):
    def test_one_winner_and_the_loser_is_inert(self):
        store = MemoryObjectStore()
        writer_a = started(new_writer(store, writer_id="a"))
        writer_b = new_writer(store, writer_id="b")
        request_a = writer_a.propose(sha256_hex(b"a"))
        request_b = writer_b.propose(sha256_hex(b"b"))
        token_a = writer_a.issue_fencing_token()
        token_b = writer_b.issue_fencing_token()
        outcome_a = writer_a.commit(request_a, token_a, use_observed_snapshot=True)
        outcome_b = writer_b.commit(request_b, token_b, use_observed_snapshot=True)
        self.assertTrue(outcome_a.accepted)
        self.assertEqual(outcome_b.status, "CAS_LOST")
        head, _ = writer_a.read_head()
        self.assertEqual(head.accepted_transition_hash, outcome_a.transition_hash)
        rebuilt = writer_a.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent, rebuilt.detail)
        self.assertEqual(len(rebuilt.chain), 1)
        # The loser's candidate object exists but is not on the accepted chain.
        self.assertEqual(len(rebuilt.orphans), 1)


class JournalRebuild(unittest.TestCase):
    def test_rebuild_walks_the_chain_not_the_listing_order(self):
        writer = started(new_writer(), transitions=4)
        rebuilt = writer.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent, rebuilt.detail)
        self.assertEqual([t.sequence for t in rebuilt.chain], [1, 2, 3, 4])
        head, _ = writer.read_head()
        self.assertEqual(rebuilt.chain[-1].transition_hash(),
                         head.accepted_transition_hash)

    def test_orphan_candidates_are_excluded_and_reported(self):
        writer = started(new_writer(), transitions=2)
        orphan = writer.propose(sha256_hex(b"orphan"), sequence=77)
        key = transition_key(PREFIX, writer.namespace_id, 1, 77,
                             orphan.transition.transition_hash())
        writer.store.append_transition_if_absent(key, orphan.transition.to_bytes())
        rebuilt = writer.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent)
        self.assertEqual(len(rebuilt.chain), 2)
        self.assertEqual(rebuilt.orphans, (key,))

    def test_missing_accepted_transition_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        head, _ = writer.read_head()
        victim = [k for k in writer.store._objects
                  if k.endswith(f"{head.accepted_transition_hash}.bin")][0]
        del writer.store._objects[victim]
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "ACCEPTED_TRANSITION_MISSING_FROM_JOURNAL"), rebuilt.detail)

    def test_tampered_transition_body_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        victim = [k for k in writer.store._objects if k.endswith(".bin")][0]
        tampered = writer.store._objects[victim].replace(b'"sequence":1',
                                                         b'"sequence":9')
        writer.store._objects[victim] = tampered
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith("TRANSITION_KEY_HASH_MISMATCH"),
                        rebuilt.detail)


class BypassBoundary(unittest.TestCase):
    def test_raw_put_head_overwrites_when_permission_allows_it(self):
        """The failure the boundary must prevent, shown explicitly: with the
        current ETag and no permission boundary, a direct HEAD put wins."""
        store = MemoryObjectStore()
        writer = started(new_writer(store), transitions=1)
        head, version = writer.read_head()
        rolled_back = HeadRecord(
            namespace_id=writer.namespace_id, epoch=head.epoch, sequence=0,
            accepted_transition_hash="0" * 64,
            previous_head_hash=head.previous_head_hash, accepted_at_ns=1)
        store.raw_put_head(head_key(PREFIX, writer.namespace_id),
                           rolled_back.to_bytes(), expected_version=version)
        after, _ = writer.read_head()
        self.assertEqual(after.sequence, 0)
        self.assertNotEqual(after.accepted_transition_hash,
                            head.accepted_transition_hash)

    def test_permission_denial_is_the_boundary_that_holds(self):
        store = MemoryObjectStore()
        writer = started(new_writer(store), transitions=1)
        head, version = writer.read_head()
        ordinary = MemoryObjectStore()
        ordinary._objects = store._objects
        ordinary._versions = store._versions
        ordinary._head_write_denied = True          # simulated policy denial
        with self.assertRaises(AccessDenied):
            ordinary.raw_put_head(head_key(PREFIX, writer.namespace_id), b"{}",
                                  expected_version=version)
        after, _ = writer.read_head()
        self.assertEqual(after.accepted_transition_hash,
                         head.accepted_transition_hash)


class EpochAwareRebuild038(unittest.TestCase):
    """DC-038 correction C/D — governing policy RESET_PER_EPOCH.

    The defect this pins: before DC-038, rebuild_from_journal() demanded that
    the accepted tip's sequence equal HEAD.sequence. Immediately after
    advance_epoch() the HEAD legitimately sits at sequence 0 in the new epoch
    while still naming the previous epoch's tip, so a perfectly healthy journal
    was reported CHAIN_TIP_SEQUENCE_NOT_HEAD. That is a false inconsistency on
    the exact path a rollback recovery depends on.

    An epoch advance is a durable mutable-HEAD fence, NOT an accepted
    transition (EPOCH_ADVANCE_ACCEPTED_TRANSITION = NO).
    """

    def test_D_governing_sequence_for_reset_per_epoch(self):
        # 1. commit transitions in epoch 1
        writer = started(new_writer(policy="RESET_PER_EPOCH"), transitions=2)
        head, _ = writer.read_head()
        self.assertEqual((head.epoch, head.sequence), (1, 2))

        # 2. rebuild => consistent
        first = writer.rebuild_from_journal()
        self.assertTrue(first.consistent, first.detail)
        self.assertEqual(first.detail, "REBUILD_CONSISTENT")
        self.assertEqual([(t.epoch, t.sequence) for t in first.chain], [(1, 1), (1, 2)])

        # 3. advance epoch under RESET_PER_EPOCH
        advanced = writer.advance_epoch(writer.issue_fencing_token())
        self.assertTrue(advanced.accepted, advanced.status)

        # 4./5. immediate rebuild BEFORE any new transition => consistent,
        #       HEAD epoch advanced and sequence reset to 0
        fenced_head, _ = writer.read_head()
        self.assertEqual((fenced_head.epoch, fenced_head.sequence), (2, 0))
        fenced = writer.rebuild_from_journal()
        self.assertTrue(fenced.consistent, fenced.detail)
        self.assertEqual(fenced.detail,
                         "REBUILD_CONSISTENT_EPOCH_FENCED_NO_NEW_TRANSITION")
        # The fence did NOT journal a new accepted transition.
        self.assertEqual(len(fenced.chain), 2)
        self.assertEqual(fenced_head.accepted_transition_hash,
                         first.chain[-1].transition_hash())

        # 6. first transition in the new epoch => sequence 1
        outcome = writer.commit(writer.propose(sha256_hex(b"post")),
                                writer.issue_fencing_token())
        self.assertTrue(outcome.accepted, outcome.status)
        after, _ = writer.read_head()
        self.assertEqual((after.epoch, after.sequence), (2, 1))

        # 7. rebuild again => consistent, chain crosses the epoch boundary
        final = writer.rebuild_from_journal()
        self.assertTrue(final.consistent, final.detail)
        self.assertEqual(final.detail, "REBUILD_CONSISTENT")
        self.assertEqual([(t.epoch, t.sequence) for t in final.chain],
                         [(1, 1), (1, 2), (2, 1)])

        # 8. the stale pre-advance token is still rejected
        stale_token = FencingToken(writer.namespace_id, 1, "pre-advance")
        rejected = writer.commit(writer.propose(sha256_hex(b"stale")), stale_token)
        self.assertEqual(rejected.status, "REJECTED_FENCING_TOKEN_EPOCH_STALE")
        unchanged, _ = writer.read_head()
        self.assertEqual((unchanged.epoch, unchanged.sequence), (2, 1))

    def test_epoch_advance_journals_no_accepted_transition(self):
        writer = started(new_writer(), transitions=1)
        before = {k for k in writer.store._objects if k.endswith(".bin")}
        writer.advance_epoch(writer.issue_fencing_token())
        after = {k for k in writer.store._objects if k.endswith(".bin")}
        self.assertEqual(before, after)

    def test_repeated_advances_without_transitions_stay_consistent(self):
        writer = started(new_writer(), transitions=1)
        for expected_epoch in (2, 3, 4):
            writer.advance_epoch(writer.issue_fencing_token())
            head, _ = writer.read_head()
            self.assertEqual((head.epoch, head.sequence), (expected_epoch, 0))
            rebuilt = writer.rebuild_from_journal()
            self.assertTrue(rebuilt.consistent, rebuilt.detail)
            self.assertEqual(len(rebuilt.chain), 1)

    def test_fenced_genesis_namespace_rebuilds_consistently(self):
        """Epoch advanced before ANY transition was ever accepted."""
        writer = started(new_writer())
        writer.advance_epoch(writer.issue_fencing_token())
        head, _ = writer.read_head()
        self.assertEqual((head.epoch, head.sequence), (2, 0))
        rebuilt = writer.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent, rebuilt.detail)
        self.assertEqual(rebuilt.detail, "REBUILD_CONSISTENT_NO_ACCEPTED_TRANSITIONS")
        self.assertEqual(rebuilt.chain, ())

    def test_alternate_policy_regression_only_non_governing(self):
        """CONTINUE_ACROSS_EPOCH is retained as regression coverage only. It
        does NOT govern: RESET_PER_EPOCH is the decided policy."""
        writer = started(new_writer(policy="CONTINUE_ACROSS_EPOCH"), transitions=2)
        writer.advance_epoch(writer.issue_fencing_token())
        head, _ = writer.read_head()
        self.assertEqual((head.epoch, head.sequence), (2, 2))
        fenced = writer.rebuild_from_journal()
        self.assertTrue(fenced.consistent, fenced.detail)
        outcome = writer.commit(writer.propose(sha256_hex(b"post")),
                                writer.issue_fencing_token())
        self.assertTrue(outcome.accepted)
        after, _ = writer.read_head()
        self.assertEqual((after.epoch, after.sequence), (2, 3))
        self.assertTrue(writer.rebuild_from_journal().consistent)

    # -- the rebuild must still fail closed ------------------------------
    def test_journal_may_not_override_the_authoritative_head_epoch(self):
        """An accepted transition claiming an epoch beyond HEAD is refused: no
        journal-only inference may promote the HEAD epoch."""
        writer = started(new_writer(), transitions=1)
        head, _ = writer.read_head()
        forged = writer.propose(sha256_hex(b"forged"), epoch=9, sequence=1)
        key = transition_key(PREFIX, writer.namespace_id, 9, 1,
                             forged.transition.transition_hash())
        writer.store.append_transition_if_absent(key, forged.transition.to_bytes())
        # Point the HEAD at the forged transition without advancing its epoch.
        rolled = HeadRecord(
            namespace_id=writer.namespace_id, epoch=head.epoch, sequence=1,
            accepted_transition_hash=forged.transition.transition_hash(),
            previous_head_hash=head.head_hash(), accepted_at_ns=1)
        writer.store.raw_put_head(head_key(PREFIX, writer.namespace_id),
                                  rolled.to_bytes())
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "ACCEPTED_TRANSITION_EPOCH_AHEAD_OF_HEAD"), rebuilt.detail)

    def test_sequence_gap_within_an_epoch_fails_closed(self):
        writer = started(new_writer(), transitions=1)
        head, _ = writer.read_head()
        gapped = writer.propose(sha256_hex(b"gap"), sequence=5)
        t = gapped.transition
        key = transition_key(PREFIX, writer.namespace_id, t.epoch, t.sequence,
                             t.transition_hash())
        writer.store.append_transition_if_absent(key, t.to_bytes())
        rolled = HeadRecord(
            namespace_id=writer.namespace_id, epoch=t.epoch, sequence=5,
            accepted_transition_hash=t.transition_hash(),
            previous_head_hash=head.head_hash(), accepted_at_ns=1)
        writer.store.raw_put_head(head_key(PREFIX, writer.namespace_id),
                                  rolled.to_bytes())
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "SEQUENCE_NOT_STRICTLY_NEXT_IN_EPOCH"), rebuilt.detail)

    def test_head_naming_no_transition_but_claiming_sequence_fails_closed(self):
        writer = started(new_writer())
        head, _ = writer.read_head()
        lying = HeadRecord(
            namespace_id=writer.namespace_id, epoch=1, sequence=7,
            accepted_transition_hash=NO_PREVIOUS_TRANSITION,
            previous_head_hash=head.head_hash(), accepted_at_ns=1)
        writer.store.raw_put_head(head_key(PREFIX, writer.namespace_id),
                                  lying.to_bytes())
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "HEAD_SEQUENCE_WITHOUT_ACCEPTED_TRANSITION"), rebuilt.detail)

    def test_orphans_still_excluded_after_an_epoch_advance(self):
        writer = started(new_writer(), transitions=2)
        orphan = writer.propose(sha256_hex(b"orphan"), sequence=88)
        orphan_key = transition_key(PREFIX, writer.namespace_id, 1, 88,
                                    orphan.transition.transition_hash())
        writer.store.append_transition_if_absent(orphan_key,
                                                 orphan.transition.to_bytes())
        writer.advance_epoch(writer.issue_fencing_token())
        rebuilt = writer.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent, rebuilt.detail)
        self.assertEqual(len(rebuilt.chain), 2)
        self.assertEqual(rebuilt.orphans, (orphan_key,))

    def test_missing_accepted_transition_still_fails_closed_after_advance(self):
        writer = started(new_writer(), transitions=2)
        head, _ = writer.read_head()
        victim = [k for k in writer.store._objects
                  if k.endswith(f"{head.accepted_transition_hash}.bin")][0]
        del writer.store._objects[victim]
        writer.advance_epoch(writer.issue_fencing_token())
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "ACCEPTED_TRANSITION_MISSING_FROM_JOURNAL"), rebuilt.detail)

    # -- fail-closed branches of the corrected tip/epoch rules -----------
    def _forge_head(self, writer, *, epoch, sequence, tip_hash):
        """Write a HEAD directly, bypassing the writer.

        This is the bypass probe, used here to manufacture the corrupt states a
        rebuilder must diagnose. It is not a governed path.
        """
        head, _ = writer.read_head()
        forged = HeadRecord(
            namespace_id=writer.namespace_id, epoch=epoch, sequence=sequence,
            accepted_transition_hash=tip_hash,
            previous_head_hash=head.head_hash(), accepted_at_ns=1)
        writer.store.raw_put_head(head_key(PREFIX, writer.namespace_id),
                                  forged.to_bytes())

    def _plant(self, writer, *, epoch, sequence, previous_transition_hash,
               payload=b"planted"):
        request = writer.propose(sha256_hex(payload), epoch=epoch, sequence=sequence,
                                 previous_transition_hash=previous_transition_hash)
        t = request.transition
        writer.store.append_transition_if_absent(
            transition_key(PREFIX, writer.namespace_id, epoch, sequence,
                           t.transition_hash()),
            t.to_bytes())
        return t

    def test_fenced_head_with_tip_in_the_same_epoch_fails_closed(self):
        """HEAD.sequence == 0 means 'nothing accepted in this epoch yet', so a
        tip inside HEAD.epoch is a contradiction: sequence 0 is never an
        accepted transition."""
        writer = started(new_writer(), transitions=1)
        head, _ = writer.read_head()
        self._forge_head(writer, epoch=head.epoch, sequence=0,
                         tip_hash=head.accepted_transition_hash)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "CHAIN_TIP_EPOCH_INVALID_FOR_FENCED_HEAD"), rebuilt.detail)

    def test_first_accepted_transition_must_be_sequence_1(self):
        writer = started(new_writer())
        planted = self._plant(writer, epoch=1, sequence=3,
                              previous_transition_hash=NO_PREVIOUS_TRANSITION)
        self._forge_head(writer, epoch=1, sequence=3,
                         tip_hash=planted.transition_hash())
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "FIRST_ACCEPTED_TRANSITION_SEQUENCE_NOT_1"), rebuilt.detail)

    def test_epoch_decrease_along_the_chain_fails_closed(self):
        writer = started(new_writer())
        first = self._plant(writer, epoch=2, sequence=1,
                            previous_transition_hash=NO_PREVIOUS_TRANSITION)
        second = self._plant(writer, epoch=1, sequence=1,
                             previous_transition_hash=first.transition_hash(),
                             payload=b"older-epoch")
        self._forge_head(writer, epoch=2, sequence=1,
                         tip_hash=second.transition_hash())
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "TRANSITION_EPOCH_DECREASED_AT_SEQUENCE"), rebuilt.detail)

    def test_tip_epoch_must_equal_head_epoch_once_sequence_advanced(self):
        writer = started(new_writer(), transitions=1)
        head, _ = writer.read_head()
        writer.advance_epoch(writer.issue_fencing_token())
        # HEAD claims a transition was accepted in epoch 2 while the tip is the
        # epoch-1 transition: an epoch advance never accepts a transition.
        self._forge_head(writer, epoch=2, sequence=1,
                         tip_hash=head.accepted_transition_hash)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith("CHAIN_TIP_EPOCH_NOT_HEAD"),
                        rebuilt.detail)

    def test_tip_sequence_must_equal_head_sequence(self):
        writer = started(new_writer(), transitions=2)
        head, _ = writer.read_head()
        self._forge_head(writer, epoch=head.epoch, sequence=5,
                         tip_hash=head.accepted_transition_hash)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith("CHAIN_TIP_SEQUENCE_NOT_HEAD"),
                        rebuilt.detail)


class ScanFromSequence038(unittest.TestCase):
    """DC-038 F: from_sequence is honoured, but never silently hides an object
    whose key carries no parseable sequence."""

    def test_from_sequence_filters_by_key_sequence(self):
        writer = started(new_writer(), transitions=3)
        prefix = transition_scan_prefix(PREFIX, writer.namespace_id)
        all_keys = [k for k, _ in writer.store.scan_transitions(prefix)]
        self.assertEqual(len(all_keys), 3)
        from_two = [k for k, _ in writer.store.scan_transitions(prefix, from_sequence=2)]
        self.assertEqual(len(from_two), 2)
        self.assertEqual([sequence_from_transition_key(k) for k in sorted(from_two)],
                         [2, 3])
        self.assertEqual(list(writer.store.scan_transitions(prefix, from_sequence=99)),
                         [])

    def test_unparseable_key_is_never_hidden_by_from_sequence(self):
        writer = started(new_writer(), transitions=1)
        prefix = transition_scan_prefix(PREFIX, writer.namespace_id)
        foreign = prefix + "1/transitions/NOT-A-SEQUENCE.bin"
        writer.store.append_transition_if_absent(foreign, b"{}")
        keys = [k for k, _ in writer.store.scan_transitions(prefix, from_sequence=99)]
        self.assertIn(foreign, keys)

    def test_foreign_key_layout_fails_closed(self):
        """A non-canonical key is diagnosed, never silently skipped: skipping
        is how a tampered journal looks clean."""
        writer = started(new_writer(), transitions=1)
        prefix = transition_scan_prefix(PREFIX, writer.namespace_id)
        writer.store.append_transition_if_absent(
            prefix + "1/transitions/NOT-A-SEQUENCE.bin", b"{}")
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith("TRANSITION_KEY_LAYOUT_INVALID"),
                        rebuilt.detail)

    def test_corrupt_body_under_a_canonical_key_fails_closed(self):
        """A canonical key is diagnosed on its BODY, not crashed on."""
        for body in (b'{"namespace_id":"x"}',      # missing required fields
                     b"not json at all",
                     b"\xff\xfe\x00binary"):
            writer = started(new_writer(), transitions=1)
            key = transition_key(PREFIX, writer.namespace_id, 1, 5, "a" * 64)
            writer.store.append_transition_if_absent(key, body)
            rebuilt = writer.rebuild_from_journal()
            self.assertFalse(rebuilt.consistent, body)
            self.assertTrue(rebuilt.detail.startswith("TRANSITION_OBJECT_UNPARSEABLE"),
                            rebuilt.detail)


class TransitionKeyBinding039(unittest.TestCase):
    """DC-039 / R2-L1 — the transition KEY is identity, not decoration.

    Reproduced on c76b9e7 before fixing: a valid body copied under a wrong
    sequence prefix, or under a wrong epoch path, was collapsed by hash. The
    rebuild returned REBUILD_CONSISTENT and reported no orphan, so a
    from_sequence scan and a full rebuild could observe different key
    identities while both looked clean.
    """

    def _copy_under(self, writer, *, epoch, sequence, remove_original=False):
        source = sorted(k for k in writer.store._objects if k.endswith(".bin"))[0]
        body = writer.store._objects[source]
        transition_hash = source.rsplit("-", 1)[1][:-len(".bin")]
        target = transition_key(PREFIX, writer.namespace_id, epoch, sequence,
                                transition_hash)
        writer.store._objects[target] = body
        writer.store._versions[target] = '"copied"'
        if remove_original:
            del writer.store._objects[source]
        return source, target

    # A ------------------------------------------------------------------
    def test_A_canonical_key_body_and_hash_rebuild_consistently(self):
        writer = started(new_writer(), transitions=3)
        rebuilt = writer.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent, rebuilt.detail)
        self.assertEqual(rebuilt.detail, "REBUILD_CONSISTENT")
        for record in rebuilt.chain:
            key = transition_key(PREFIX, writer.namespace_id, record.epoch,
                                 record.sequence, record.transition_hash())
            parsed = parse_transition_key(key, prefix=PREFIX,
                                          namespace_id=writer.namespace_id)
            self.assertEqual(parsed.epoch, record.epoch)
            self.assertEqual(parsed.sequence, record.sequence)
            self.assertEqual(parsed.transition_hash, record.transition_hash())

    # B ------------------------------------------------------------------
    def test_B_same_body_under_a_wrong_sequence_prefix_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        self._copy_under(writer, epoch=1, sequence=77)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "DUPLICATE_TRANSITION_HASH_UNDER_DISTINCT_KEYS"), rebuilt.detail)

    def test_B2_lone_copy_under_a_wrong_sequence_prefix_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        self._copy_under(writer, epoch=1, sequence=77, remove_original=True)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith("TRANSITION_KEY_SEQUENCE_MISMATCH"),
                        rebuilt.detail)

    # C ------------------------------------------------------------------
    def test_C_same_body_under_a_wrong_epoch_path_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        source = sorted(k for k in writer.store._objects if k.endswith(".bin"))[0]
        sequence = int(source.rsplit("/", 1)[1].split("-")[0])
        self._copy_under(writer, epoch=9, sequence=sequence)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "DUPLICATE_TRANSITION_HASH_UNDER_DISTINCT_KEYS"), rebuilt.detail)

    def test_C2_lone_copy_under_a_wrong_epoch_path_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        source = sorted(k for k in writer.store._objects if k.endswith(".bin"))[0]
        sequence = int(source.rsplit("/", 1)[1].split("-")[0])
        self._copy_under(writer, epoch=9, sequence=sequence, remove_original=True)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith("TRANSITION_KEY_EPOCH_MISMATCH"),
                        rebuilt.detail)

    # D ------------------------------------------------------------------
    def test_D_duplicate_hash_under_two_distinct_keys_fails_closed(self):
        writer = started(new_writer(), transitions=2)
        source, target = self._copy_under(writer, epoch=2, sequence=1)
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertTrue(rebuilt.detail.startswith(
            "DUPLICATE_TRANSITION_HASH_UNDER_DISTINCT_KEYS"), rebuilt.detail)
        # The diagnostic names BOTH keys, in sorted order, so it is
        # reproducible whatever order the provider lists objects in.
        self.assertIn(" | ".join(sorted((source, target))), rebuilt.detail)

    def test_D2_duplicate_diagnostic_is_listing_order_independent(self):
        details = []
        for reverse in (False, True):
            writer = started(new_writer(), transitions=2)
            self._copy_under(writer, epoch=2, sequence=1)
            store = writer.store
            original_scan = store.scan_transitions

            def scan(prefix, from_sequence=0, _rev=reverse):
                items = list(original_scan(prefix, from_sequence))
                items.sort(key=lambda item: item[0], reverse=_rev)
                return iter(items)

            store.scan_transitions = scan
            details.append(writer.rebuild_from_journal().detail)
        self.assertEqual(details[0], details[1])

    # E ------------------------------------------------------------------
    def test_E_malformed_key_layouts_fail_closed(self):
        namespace = "ns-1"
        base = f"{PREFIX}/stage-a/v1/coordination/{namespace}/epochs"
        good = transition_key(PREFIX, namespace, 1, 1, "a" * 64)
        self.assertIsNotNone(parse_transition_key(good, prefix=PREFIX,
                                                  namespace_id=namespace))
        seq20 = "0" * 19 + "1"          # the one valid 20-digit spelling
        malformed = (
            f"{base}/1/transitions/1-{'a' * 64}.bin",              # unpadded
            f"{base}/1/transitions/{'0' * 18}1-{'a' * 64}.bin",     # 19 digits
            f"{base}/1/transitions/{'0' * 20}1-{'a' * 64}.bin",     # 21 digits
            f"{base}/1/transitions/{seq20}-{'a' * 63}.bin",         # short hash
            f"{base}/1/transitions/{seq20}-{'A' * 64}.bin",         # upper-case hash
            f"{base}/01/transitions/{seq20}-{'a' * 64}.bin",        # padded epoch
            f"{base}/x/transitions/{seq20}-{'a' * 64}.bin",         # non-numeric epoch
            f"{base}/1/transitions/{seq20}-{'a' * 64}.txt",         # wrong extension
            f"{base}/1/{seq20}-{'a' * 64}.bin",                     # missing segment
            good.replace(f"/{namespace}/", "/other-namespace/"),    # other namespace
            good.replace(PREFIX + "/", "other-prefix/"),            # other prefix
        )
        for key in malformed:
            self.assertIsNone(parse_transition_key(key, prefix=PREFIX,
                                                   namespace_id=namespace), key)
        writer = started(new_writer(namespace=namespace), transitions=1)
        writer.store.append_transition_if_absent(malformed[0], b"{}")
        rebuilt = writer.rebuild_from_journal()
        self.assertFalse(rebuilt.consistent)
        self.assertEqual(rebuilt.detail, "TRANSITION_KEY_LAYOUT_INVALID:" + malformed[0])

    # F ------------------------------------------------------------------
    def test_F_orphans_and_from_sequence_semantics_are_preserved(self):
        writer = started(new_writer(), transitions=2)
        orphan = writer.propose(sha256_hex(b"orphan"), sequence=88)
        orphan_key = transition_key(PREFIX, writer.namespace_id, 1, 88,
                                    orphan.transition.transition_hash())
        writer.store.append_transition_if_absent(orphan_key,
                                                 orphan.transition.to_bytes())
        rebuilt = writer.rebuild_from_journal()
        self.assertTrue(rebuilt.consistent, rebuilt.detail)
        self.assertEqual(rebuilt.orphans, (orphan_key,))
        prefix = transition_scan_prefix(PREFIX, writer.namespace_id)
        self.assertEqual(
            len([k for k, _ in writer.store.scan_transitions(prefix, from_sequence=2)]),
            2)


if __name__ == "__main__":
    unittest.main()
