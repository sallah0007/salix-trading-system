"""Logic-only unit tests for the restricted authority writer.

No network, no boto3, no credentials. These prove the WRITER's validation
order and outcomes. They are explicitly NOT provider evidence (E07-M1): the
in-memory store models a well-behaved provider and can prove nothing about a
real one.
"""
from __future__ import annotations

import itertools
import unittest

from tests.provider_conformance.authority_writer import (RestrictedAuthorityWriter,
                                                         SEQUENCE_POLICIES)
from tests.provider_conformance.canonical import sha256_hex
from tests.provider_conformance.memory_store import MemoryObjectStore
from tests.provider_conformance.model import (HeadRecord, head_key,
                                              transition_key)
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


if __name__ == "__main__":
    unittest.main()
