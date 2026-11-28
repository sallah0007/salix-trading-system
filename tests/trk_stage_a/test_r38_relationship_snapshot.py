"""R38: owner-bound relationship store + Health adapter; snapshot manifest bound to the Core's owning observations."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.health import adapters as AD
from stage_a.tracker import version_diff as VD, relationship_store as RS, snapshot_binding as SB, registry_semantics as REG
from .test_r38_composition import comp
from .test_r26_snapshot import SealedResolution as SR
from .test_r37_registry_semantics import man
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Rel(unittest.TestCase):
    def setUp(self):
        self.rig, self.pkg, self.fk, c, co, path = comp(); co.accept_and_publish(self.pkg, __import__("tests.trk_stage_a.test_r37_sim_publication_path", fromlist=["x"]).supplied(), "SIM_CUR", sequence=1, now=10, max_age=50); self.a = self.fk.key()
        self.j = ObjectStoreJournal(InMemoryObjectStore(), "rel", "w"); self.j.acquire_epoch(); self.own = RS.journal_owner_check(self.rig.journals); self.st = RS.RelationshipStore(self.j, self.own)
    def mk(self, pred, succ): return VD.Relationship(pred, succ, "S1", VD.COMPUTED, ("f",), VD.PROVENANCE_CHANGE, "", (), "rid-" + succ)
    def test_owner_must_resolve_for_both_versions_before_append_and_reference(self):
        ghost = "XAUUSD/H4/mom3/9"; self.assertTrue(self.own(self.a)); self.assertFalse(self.own(ghost)); self.assertEqual(code(self.st.append, self.mk(self.a, ghost)), "RELATIONSHIP_OWNER_NOT_RESOLVED"); self.assertEqual(self.j.head().seq, 0)
        r = self.st.successor_reference(self.a, ghost, "S1"); self.assertEqual((r.state, r.claim_allowed, r.reason), ("OWNER_NOT_RESOLVED", False, "VERSION_NOT_LIVE_IN_OWNING_JOURNAL"))
    def test_reference_has_no_delivery_field_missing_record_fails_the_claim_and_a_computed_record_allows_it(self):
        self.assertFalse(hasattr(RS.RelationshipReference, "existing_version_deliverable")); self.assertNotIn("existing_version_deliverable", [f.name for f in dataclasses.fields(RS.RelationshipReference)])
        class Both(RS.RelationshipStore): pass
        own2 = lambda s: s in (self.a, "X/Y/z/2"); st = RS.RelationshipStore(self.j, own2); r = st.successor_reference(self.a, "X/Y/z/2", "S1"); self.assertEqual((r.state, r.claim_allowed), ("RELATIONSHIP_UNCOMPUTED", False))
        rel = self.mk(self.a, "X/Y/z/2"); st.append(rel); self.assertIsNone(st.append(rel)); r = st.successor_reference(self.a, "X/Y/z/2", "S1"); self.assertEqual((r.claim_allowed, r.relationship_class, r.record_id), (True, VD.PROVENANCE_CHANGE, "rid-X/Y/z/2"))
        self.assertEqual(st.successor_reference(self.a, "X/Y/z/2", "S2").reason, "NO_RECORD_UNDER_CURRENT_SCHEMA"); self.assertEqual(code(st.append, dataclasses.replace(rel, relationship_class=VD.SCOPE_CHANGE)), "RELATIONSHIP_IMMUTABLE_PER_SCHEMA_VERSION")
        self.assertEqual(st.pinned("rid-X/Y/z/2"), rel); self.assertEqual(RS.RelationshipStore(self.j, own2).successor_reference(self.a, "X/Y/z/2", "S1").record_id, "rid-X/Y/z/2")                    # restart: replayed from the journal
    def test_withdrawn_version_no_longer_resolves_and_health_observation_is_facts_only(self):
        from stage_a.tracker import publication as PUB
        own2 = lambda s: s in (self.a, "X/Y/z/2"); st = RS.RelationshipStore(self.j, lambda s: self.own(s) if s == self.a else True); st.append(self.mk(self.a, "X/Y/z/2")); o = AD.from_relationship_reference(st.successor_reference(self.a, "X/Y/z/2", "S1")); self.assertEqual((o.kind, o.scope, o.facts["claim_allowed"], o.admitted), ("VERSION_RELATIONSHIP", "SUBJECT", True, False)); self.assertNotIn("deliverable", str(o.facts))
        PUB.withdraw(self.rig.journals.journal(self.fk.namespace()), self.fk, "w"); r = st.successor_reference(self.a, "X/Y/z/2", "S1"); self.assertEqual((r.state, r.claim_allowed), ("OWNER_NOT_RESOLVED", False))
        self.assertIsNone(AD.from_relationship_reference(object()).facts); self.assertEqual(code(RS.RelationshipStore, self.j, None), "RELATIONSHIP_OWNER_CHECK_REQUIRED")
class Bind(unittest.TestCase):
    def _resolved(self, vint="v1"):
        h = SR.__new__(SR); c = SR.core(h); k = {n: SR.put(h, c, tf, n, av, vint) for n, tf, av in (("P4", "H4", 5), ("P1", "H1", 8))}; out = c.resolve_sealed_snapshot("XAUUSD", 10, 10, [k["P4"], k["P1"]], {"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]}, {"H4": 9, "H1": 10}); return c, out
    def test_manifest_agreeing_with_every_owned_field_binds_and_lists_the_unbound_fields(self):
        c, out = self._resolved("ORIGINAL_AS_OBSERVED"); b = SB.bind_snapshot_manifest(c, self._mv(), out["resolved_manifest_hash"]); self.assertEqual((b.authoritative, b.base_seal_hash), (False, out["base_seal_hash"])); self.assertIn("source_provider_identity", b.unbound_fields)
    def _mv(self, **o):
        d = dict(instrument_id="XAUUSD", query_asof=10, snapshot_fence_ts=10, data_vintage_mode="ORIGINAL_AS_OBSERVED", timeframe_watermarks=(("H1", 10), ("H4", 9))); d.update(o); return man(**d)
    def test_each_owned_field_disagreement_refuses(self):
        c0, o0 = self._resolved(); self.assertEqual(code(SB.bind_snapshot_manifest, c0, self._mv(), o0["resolved_manifest_hash"]), "SNAPSHOT_VINTAGE_LABEL_NOT_COMPARABLE_HELD")
        c, out = self._resolved("ORIGINAL_AS_OBSERVED"); mh = out["resolved_manifest_hash"]; self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(data_vintage_mode="CURRENT_RECOMPUTED"), mh), "SNAPSHOT_VINTAGE_LABEL_NOT_COMPARABLE_HELD")                       # core vintage label 'v1' is not the manifest mode vocabulary: never guessed
        for kw, want in ((dict(instrument_id="EURUSD"), "SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS"), (dict(query_asof=9), "SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS"), (dict(timeframe_watermarks=(("H1", 10),)), "SNAPSHOT_TIMEFRAME_SET_DISAGREES"), (dict(timeframe_watermarks=(("H1", 10), ("H4", 8))), "SNAPSHOT_WATERMARK_DISAGREES_WITH_OWNING_RESOLUTION")):
            self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(**kw), mh), want, kw)
        self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(), "0" * 64), "SNAPSHOT_RESOLVED_MANIFEST_NOT_IN_CORE"); self.assertEqual(code(SB.bind_snapshot_manifest, c, "x", mh), "SNAPSHOT_BINDING_INPUT_INVALID")
if __name__ == "__main__": unittest.main()
