"""R24: accepted-manifest read-back joins the journal's CANONICAL_ACCEPTED record to the stored bytes with independent re-derivation; every break fails closed. Simulation acceptance is the only producible
acceptance here, so these prove byte/identity integrity of the read-back, NOT authority of the acceptance."""
import json, unittest
from stage_a.errors import Refusal
from stage_a.identifiers import Scope, FeatureKey
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker.accepted_manifest import read_accepted_manifest, RECORDED_LINEAGE
from .fixtures import Rig, package
from .test_r24_core import code

def accepted():
    rig = Rig(); p = package(); rig.issue(p); o = rig.pipe.run(p); assert o.accepted_ok
    fk = FeatureKey(Scope("XAUUSD", "H4"), "mom3", "1"); return rig, fk, rig.journals.journal(fk.namespace())

class Readback(unittest.TestCase):
    def test_positive_returns_the_stored_manifest_and_recorded_lineage_references(self):
        rig, fk, j = accepted(); r = read_accepted_manifest(j, rig.store, fk)
        self.assertEqual((r.feature_key, r.manifest.feature_id, r.manifest.feature_version), (fk.key(), "mom3", "1")); self.assertEqual([k for k, _ in r.recorded_lineage], list(RECORDED_LINEAGE))
        self.assertEqual(r.accepted_seq, j.read_from(1)[0].seq)
    def test_no_accepted_record_and_wrong_version_fail_closed(self):
        rig, fk, j = accepted(); self.assertEqual(code(read_accepted_manifest, j, rig.store, FeatureKey(Scope("XAUUSD", "H4"), "mom3", "2")), "NO_ACCEPTED_RECORD")
        empty = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), fk.namespace(), "w"); empty.acquire_epoch(); self.assertEqual(code(read_accepted_manifest, empty, rig.store, fk), "NO_ACCEPTED_RECORD")
    def test_absent_altered_and_noncanonical_bytes_fail_closed(self):
        rig, fk, j = accepted(); key = "artifact/" + json.loads(j.read_from(1)[0].body_json)["manifest_hash"]; good = rig.store.get(key)[0]
        class Other(InMemoryObjectStore):
            def __init__(s, raw): super().__init__(); s.raw = raw
            def get(s, k): return None if s.raw is None else (s.raw,)
        self.assertEqual(code(read_accepted_manifest, j, Other(None), fk), "ACCEPTED_ARTIFACT_ABSENT")
        self.assertIn(code(read_accepted_manifest, j, Other(good[:-1] + bytes([good[-1] ^ 1])), fk), ("ACCEPTED_ARTIFACT_UNPARSEABLE", "ACCEPTED_ARTIFACT_NOT_CANONICAL", "ACCEPTED_ARTIFACT_HASH_MISMATCH"))
        self.assertEqual(code(read_accepted_manifest, j, Other(b"not a manifest"), fk), "ACCEPTED_ARTIFACT_UNPARSEABLE")
    def test_a_different_valid_manifest_under_the_recorded_hash_key_is_refused_by_the_independent_hash_check(self):
        from stage_a.composer.expression.manifest import Manifest
        from stage_a.composer.expression.canonical_encoding import encode_manifest
        from .fixtures import momentum_manifest
        rig, fk, j = accepted(); other = encode_manifest(Manifest.from_dict(momentum_manifest(window=4)))
        class Swap(InMemoryObjectStore):
            def get(s, k): return (other,)
        self.assertEqual(code(read_accepted_manifest, j, Swap(), fk), "ACCEPTED_ARTIFACT_HASH_MISMATCH")
    def test_record_field_and_key_corruption_fail_closed(self):
        rig, fk, j = accepted(); body = json.loads(j.read_from(1)[0].body_json)
        for drop in ("graph_hash", "verification_hash"):
            b = {k: v for k, v in body.items() if k != drop}; jj = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), fk.namespace(), "w"); jj.acquire_epoch()
            try: jj.append(jj.head(), "CANONICAL_ACCEPTED", b)
            except Refusal: continue
            self.assertIn(code(read_accepted_manifest, jj, rig.store, fk), ("ACCEPTED_RECORD_FIELD_MISSING", "NO_ACCEPTED_RECORD", "TRANSITION_BODY_INCOMPLETE"))
class Forged(unittest.TestCase):
    """Records forged so that exactly ONE independent check can catch the break (defences are not mutually redundant)."""
    def setUp(self):
        self.rig, self.fk, self.j = accepted(); self.body = json.loads(self.j.read_from(1)[0].body_json); self.good = self.rig.store.get("artifact/" + self.body["manifest_hash"])[0]
    def jour(self, **ch):
        b = dict(self.body); b.update(ch); jj = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), self.fk.namespace(), "w"); jj.acquire_epoch(); jj.append(jj.head(), "CANONICAL_ACCEPTED", b); return jj
    class One(InMemoryObjectStore):
        def __init__(s, raw): super().__init__(); s.raw = raw
        def get(s, k): return (s.raw,)
    def test_each_recorded_hash_is_independently_recomputed(self):
        for f in ("manifest_hash", "graph_hash", "program_hash"):
            self.assertEqual(code(read_accepted_manifest, self.jour(**{f: "f" * 64}), self.One(self.good), self.fk), "ACCEPTED_ARTIFACT_HASH_MISMATCH", f)
        self.assertEqual(read_accepted_manifest(self.jour(), self.One(self.good), self.fk).manifest_hash, self.body["manifest_hash"])          # positive control with the same helper
    def test_noncanonical_bytes_are_refused_even_when_they_parse(self):
        self.assertEqual(code(read_accepted_manifest, self.j, self.One(self.good + b" "), self.fk), "ACCEPTED_ARTIFACT_NOT_CANONICAL")
    def test_artifact_with_other_identity_but_matching_recorded_hashes_is_refused(self):
        from stage_a.composer.expression.manifest import Manifest
        from stage_a.composer.expression.artifacts import build_artifact
        from .fixtures import momentum_manifest
        a = build_artifact(Manifest.from_dict(momentum_manifest(version="2")))
        jj = self.jour(manifest_hash=a.manifest_hash, graph_hash=a.graph_hash, program_hash=a.program_hash)
        self.assertEqual(code(read_accepted_manifest, jj, self.One(a.manifest_bytes), self.fk), "ACCEPTED_ARTIFACT_IDENTITY_MISMATCH")
    def test_a_record_under_another_namespace_is_refused_by_replay(self):
        self.assertEqual(code(read_accepted_manifest, self.jour(feature_key="XAUUSD/H4/mom3/9"), self.One(self.good), self.fk), "CROSS_NAMESPACE_RECORD")
if __name__ == "__main__": unittest.main()
