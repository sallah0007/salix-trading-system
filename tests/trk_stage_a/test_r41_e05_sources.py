"""R41: E05 source adapters for the manifest and scheduler/replay owning objects with rebuild rehearsal: canonical REF+hash, drift, concurrent head movement, recovery, legacy objects untouched."""
import unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.storage import e05_sources as S
from stage_a.storage.e05_index import E05Index
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.keys import artifact_key
from stage_a.composer.expression.canonical_encoding import encode_manifest
from stage_a.tracker.verification.independent_hashing import manifest_digest
from stage_a.ops import workers as W
from .fixtures import package, SIM_CONF
from stage_a.tracker.quant_intake_adapter import admit
def manifest_bytes(**kw):
    pkg = package(**kw); adm = admit(pkg, accepted_fit_generations={}, conformance=SIM_CONF); return encode_manifest(adm.manifest)
class Src(unittest.TestCase):
    def setUp(self):
        self.s = InMemoryObjectStore(); self.raw = manifest_bytes(); self.mh = manifest_digest(self.raw); self.s.put_if_absent(artifact_key(self.mh), self.raw)
        self.q = W.JobQueue(); self.q.submit(W.Job("j1", "tracker.verify", "idem-1", (("manifest", self.mh),)))
        self.sources = {"manifest": S.object_prefix_source(self.s, "stagea_manifest_index", "artifact/", S.manifest_row_of(lambda mh: "CURRENT_HELD_ENUM")),
                        "sched": S.queue_source("stagea_scheduler_queue", self.q, lambda j: dict(job_id=j.job_id, priority_class="p", next_eligible_at=0, family_id="f"))}
        self.res = S.combined_resolver(S.object_resolver(self.s), S.queue_resolver(self.q)); self.ix = E05Index()
    def test_rebuild_projects_manifest_and_scheduler_rows_with_canonical_ref_and_hash(self):
        heads = self.ix.rebuild(self.sources); self.assertEqual(set(heads), {"manifest", "sched"})
        r = self.ix.lookup("stagea_manifest_index", {"manifest_hash": self.mh}, self.res); self.assertFalse(r.authoritative); self.assertEqual(r["ref"], "object:" + artifact_key(self.mh)); self.assertEqual(r["status_currentness"], "CURRENT_HELD_ENUM")
        self.assertIsNotNone(self.ix.lookup("stagea_scheduler_queue", {"job_id": "j1"}, self.res)); self.assertEqual(self.ix.verify_all(self.res), 2)
    def test_replaced_canonical_object_is_drift_not_a_silently_current_row(self):
        self.ix.rebuild(self.sources); g = self.s.get(artifact_key(self.mh)); self.s.put_if_match(artifact_key(self.mh), g[0] + b" ", g[1])
        with self.assertRaises(IntegrityFailure): self.ix.lookup("stagea_manifest_index", {"manifest_hash": self.mh}, self.res)
        with self.assertRaises(Refusal): self.ix.rebuild(self.sources)               # the changed bytes no longer hash to their content address: the source refuses rather than projecting it
    def test_a_head_that_moves_during_the_read_is_retried_then_refused_when_it_never_settles(self):
        head, rows = self.sources["manifest"]; n = [0]
        def moving_rows():
            n[0] += 1; self.s.put_if_absent("artifact/zz%d" % n[0], b"x"); return iter(())
        self.assertRaises(Refusal, self.ix.rebuild, {"m": (head, moving_rows)}, max_attempts=2)
    def test_the_index_is_rebuildable_after_loss_and_legacy_objects_are_untouched(self):
        self.ix.rebuild(self.sources); before = self.s.get(artifact_key(self.mh)); self.ix = E05Index(); self.assertIsNone(self.ix.lookup("stagea_manifest_index", {"manifest_hash": self.mh}, self.res))
        self.ix.rebuild(self.sources); self.assertIsNotNone(self.ix.lookup("stagea_manifest_index", {"manifest_hash": self.mh}, self.res)); self.assertEqual(self.s.get(artifact_key(self.mh)), before)
    def test_a_queue_row_disappears_when_the_job_completes_and_a_missing_currentness_authority_refuses(self):
        self.q.complete("idem-1"); self.ix.rebuild(self.sources); self.assertIsNone(self.ix.lookup("stagea_scheduler_queue", {"job_id": "j1"}, self.res))
        bad = {"m": S.object_prefix_source(self.s, "stagea_manifest_index", "artifact/", S.manifest_row_of(lambda mh: None))}
        with self.assertRaises(Refusal) as c: self.ix.rebuild(bad)
        self.assertEqual(c.exception.code, "E05_SOURCE_CURRENTNESS_NOT_SUPPLIED")
    def test_the_source_head_moves_when_bytes_are_replaced_under_the_same_key(self):
        head, _ = self.sources["manifest"]; h0 = head(); g = self.s.get(artifact_key(self.mh)); self.s.put_if_match(artifact_key(self.mh), g[0], g[1]); self.assertNotEqual(head(), h0)
if __name__ == "__main__": unittest.main()
