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
from .test_r37_version_diff import S, BASE
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Rel(unittest.TestCase):
    def setUp(self):
        self.rig, self.pkg, self.fk, c, co, path = comp(); co.accept_and_publish(self.pkg, __import__("tests.trk_stage_a.test_r37_sim_publication_path", fromlist=["x"]).supplied(), "SIM_CUR", sequence=1, now=10, max_age=50); self.a = self.fk.key()
        self.j = ObjectStoreJournal(InMemoryObjectStore(), "rel", "w"); self.j.acquire_epoch(); self.own = RS.journal_owner_check(self.rig.journals); self.st = RS.RelationshipStore(self.j, self.own)
    def mk(self, pred, succ): return VD.Relationship(pred, succ, "DS1", VD.COMPUTED, ("f",), VD.PROVENANCE_CHANGE, "", (), "rid-" + succ)
    def test_owner_must_resolve_for_both_versions_before_append_and_reference(self):
        ghost = "XAUUSD/H4/mom3/9"; self.assertTrue(self.own(self.a)); self.assertFalse(self.own(ghost)); self.assertEqual(code(self.st.append, self.mk(self.a, ghost)), "RELATIONSHIP_OWNER_NOT_RESOLVED"); self.assertEqual(self.j.head().seq, 0)
        r = self.st.successor_reference(self.a, ghost, "DS1"); self.assertEqual((r.state, r.claim_allowed, r.reason), ("OWNER_NOT_RESOLVED", False, "VERSION_NOT_LIVE_IN_OWNING_JOURNAL"))
    def _st(self, own=None, verifier=None, schema=None, content=True):
        C = {self.a: dict(BASE), "X/Y/z/2": dict(BASE, source_path="p2"), "X/Y/z/3": dict(BASE), "X/Y/z/4": dict(BASE, formula="f2"), "X/Y/z/5": dict(BASE, source_path="p2", instrument_set="E")}
        return RS.RelationshipStore(self.j, own or (lambda x: x in C), schema=schema or S, content_of=(C.get if content else None), defect_verifier=verifier), C
    def test_reference_has_no_delivery_field_missing_record_fails_the_claim_and_a_GENUINE_computed_record_allows_it(self):
        self.assertFalse(hasattr(RS.RelationshipReference, "existing_version_deliverable")); self.assertNotIn("existing_version_deliverable", [f.name for f in dataclasses.fields(RS.RelationshipReference)])
        st, C = self._st(); a = self.a; self.assertEqual((st.successor_reference(a, "X/Y/z/2", "DS1").state, st.successor_reference(a, "X/Y/z/2", "DS1").claim_allowed), ("RELATIONSHIP_UNCOMPUTED", False))
        rel = VD.compute(S, a, C[a], "X/Y/z/2", C["X/Y/z/2"]); st.append(rel); self.assertIsNone(st.append(rel)); r = st.successor_reference(a, "X/Y/z/2", "DS1"); self.assertEqual((r.claim_allowed, r.relationship_class, r.record_id), (True, VD.PROVENANCE_CHANGE, rel.record_id))
        self.assertEqual(st.successor_reference(a, "X/Y/z/2", "S2").reason, "NO_RECORD_UNDER_CURRENT_SCHEMA"); self.assertEqual(st.pinned(rel.record_id), rel)
        n = VD.compute(S, a, C[a], "X/Y/z/3", C["X/Y/z/3"]); st.append(n); u = st.successor_reference(a, "X/Y/z/3", "DS1"); self.assertEqual((u.state, u.relationship_class, u.claim_allowed), (VD.COMPUTED, None, False))      # genuine but NO class: fails closed
        h = VD.compute(S, a, C[a], "X/Y/z/5", C["X/Y/z/5"]); st.append(h); self.assertEqual((st.successor_reference(a, "X/Y/z/5", "DS1").reason, st.successor_reference(a, "X/Y/z/5", "DS1").claim_allowed), ("COMBINATION_NOT_DEFINED_HELD", False))
        self.assertEqual(self._st()[0].successor_reference(a, "X/Y/z/2", "DS1").record_id, rel.record_id)                                   # restart: replayed AND re-verified
    def test_hand_authored_forged_unknown_class_and_wrong_owning_content_are_refused(self):
        st, C = self._st(); a = self.a; good = VD.compute(S, a, C[a], "X/Y/z/4", C["X/Y/z/4"]); self.assertEqual(good.relationship_class, VD.MATERIAL_ALTERNATIVE)
        arb = VD.Relationship(a, "X/Y/z/4", "DS1", VD.COMPUTED, ("formula",), VD.CORRECTION, "", (), "arbitrary-not-a-hash"); self.assertEqual(code(st.append, arb), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")
        from stage_a.storage.byte_primitives import canonical_bytes, domain_hash
        body = {"predecessor": a, "successor": "X/Y/z/4", "schema_version": "DS1", "state": VD.COMPUTED, "changed_fields": ["formula"], "class": VD.CORRECTION, "reason": "", "evidence_refs": []}
        forged = dataclasses.replace(arb, record_id=domain_hash("SALIX_FEATURE_VERSION_RELATIONSHIP_CANDIDATE_V1", canonical_bytes(body))); self.assertEqual(code(st.append, forged), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")      # self-consistent class+hash, still not the compute result
        self.assertEqual(code(st.append, dataclasses.replace(good, relationship_class="BRAND_NEW_CLASS")), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION"); self.assertEqual(code(st.append, dataclasses.replace(good, record_id="0" * 64)), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")
        self.assertEqual(code(st.append, dataclasses.replace(good, schema_version="S0")), "RELATIONSHIP_SCHEMA_NOT_THE_CURRENT_BOUND_SCHEMA"); self.assertEqual(self.j.head().seq, 0)
        wrong = VD.compute(S, a, C[a], "X/Y/z/4", dict(C["X/Y/z/4"], formula="f9")); self.assertEqual(wrong.changed_fields, good.changed_fields); self.assertNotEqual(wrong.record_id, good.record_id) if wrong.record_id != good.record_id else None
        wrong_src = VD.compute(S, a, dict(C[a], source_path="other"), "X/Y/z/4", C["X/Y/z/4"]); self.assertNotEqual(wrong_src, good); self.assertEqual(code(st.append, wrong_src), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")      # computed over content that is NOT the owner's
        self.assertEqual(self._st(content=False)[0].__class__, RS.RelationshipStore); u, _ = self._st(content=False); self.assertEqual(code(u.append, good), "RELATIONSHIP_RECOMPUTATION_INPUTS_NOT_BOUND_HELD")
        C.pop("X/Y/z/4"); st2 = RS.RelationshipStore(self.j, lambda x: True, schema=S, content_of=C.get); self.assertEqual(code(st2.append, good), "RELATIONSHIP_OWNING_CONTENT_NOT_RESOLVED")
    def test_correction_needs_the_supplied_verifier_and_evidence_and_unbound_inputs_are_HELD(self):
        ver = lambda refs: refs == ("EV1",); st, C = self._st(verifier=ver); a = self.a
        cor = VD.compute(S, a, C[a], "X/Y/z/4", C["X/Y/z/4"], defect_verifier=ver, defect_evidence_refs=("EV1",), attributable_fields=("formula",)); self.assertEqual(cor.relationship_class, VD.CORRECTION)
        self.assertEqual(code(st.append, cor), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")                                   # attributable fields not supplied => the compute path yields MATERIAL_ALTERNATIVE
        st.append(cor, attributable_fields=("formula",)); r = st.successor_reference(a, "X/Y/z/4", "DS1"); self.assertEqual((r.relationship_class, r.claim_allowed), (VD.CORRECTION, True))
        j2 = ObjectStoreJournal(InMemoryObjectStore(), "r2", "w"); j2.acquire_epoch(); nov = RS.RelationshipStore(j2, lambda x: True, schema=S, content_of=C.get); self.assertEqual(code(nov.append, cor, ("formula",)), "RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")   # no verifier => CORRECTION impossible
        j3 = ObjectStoreJournal(InMemoryObjectStore(), "r3", "w"); j3.acquire_epoch(); un = RS.RelationshipStore(j3, lambda x: True); self.assertEqual(code(un.append, cor), "RELATIONSHIP_SCHEMA_NOT_THE_CURRENT_BOUND_SCHEMA")
        nc = RS.RelationshipStore(j3, lambda x: True, schema=S); self.assertEqual(code(nc.append, cor), "RELATIONSHIP_RECOMPUTATION_INPUTS_NOT_BOUND_HELD"); self.assertEqual(j3.head().seq, 0)
        r = RS.RelationshipStore(self.j, lambda x: True, schema=S).successor_reference(a, "X/Y/z/4", "DS1"); self.assertEqual((r.claim_allowed, r.reason), (False, "RELATIONSHIP_RECOMPUTATION_INPUTS_NOT_BOUND_HELD"))      # a stored record without recompute inputs never allows the claim
    def test_a_stored_record_that_the_compute_path_no_longer_reproduces_fails_the_claim_closed(self):
        st, C = self._st(); a = self.a; st.append(VD.compute(S, a, C[a], "X/Y/z/2", C["X/Y/z/2"])); C["X/Y/z/2"]["source_path"] = "p9"; C["X/Y/z/2"]["formula"] = "fz"
        r = st.successor_reference(a, "X/Y/z/2", "DS1"); self.assertEqual((r.claim_allowed, r.reason), (False, "RECORD_DOES_NOT_MATCH_RECOMPUTATION"))
        self.j.append(self.j.head(), "VERSION_RELATIONSHIP", {"predecessor": a, "successor": "X/Y/z/7", "schema_version": "DS1", "state": VD.COMPUTED, "changed_fields": ["formula"], "class": VD.CORRECTION, "reason": "", "evidence_refs": [], "record_id": "arbitrary"})
        C["X/Y/z/7"] = dict(BASE, formula="f7"); st2 = RS.RelationshipStore(self.j, lambda x: True, schema=S, content_of=C.get); self.assertFalse(st2.successor_reference(a, "X/Y/z/7", "DS1").claim_allowed)                # a hand-written journal record is not authority either
    def test_withdrawn_version_no_longer_resolves_and_health_observation_is_facts_only(self):
        from stage_a.tracker import publication as PUB
        st, C = self._st(own=lambda s: self.own(s) if s == self.a else True); st.append(VD.compute(S, self.a, C[self.a], "X/Y/z/2", C["X/Y/z/2"])); o = AD.from_relationship_reference(st.successor_reference(self.a, "X/Y/z/2", "DS1")); self.assertEqual((o.kind, o.scope, o.facts["claim_allowed"], o.admitted), ("VERSION_RELATIONSHIP", "SUBJECT", True, False)); self.assertNotIn("deliverable", str(o.facts))
        PUB.withdraw(self.rig.journals.journal(self.fk.namespace()), self.fk, "w"); r = st.successor_reference(self.a, "X/Y/z/2", "DS1"); self.assertEqual((r.state, r.claim_allowed), ("OWNER_NOT_RESOLVED", False))
        self.assertIsNone(AD.from_relationship_reference(object()).facts); self.assertEqual(code(RS.RelationshipStore, self.j, None), "RELATIONSHIP_OWNER_CHECK_REQUIRED")
class Bind(unittest.TestCase):
    def _resolved(self, vint="v1", complete=True):
        h = SR.__new__(SR); c = SR.core(h); k = {n: SR.put(h, c, tf, n, av, vint) for n, tf, av in (("P4", "H4", 5), ("P1", "H1", 8))}; out = c.resolve_sealed_snapshot("XAUUSD", 10, 10, [k["P4"], k["P1"]], {"H4": [(k["P4"], complete)], "H1": [(k["P1"], True)]}, {"H4": 9, "H1": 10}); return c, out
    def test_manifest_agreeing_with_every_owned_field_binds_and_lists_the_unbound_fields(self):
        c, out = self._resolved("ORIGINAL_AS_OBSERVED"); b = SB.bind_snapshot_manifest(c, self._mv(), out["resolved_manifest_hash"]); self.assertEqual((b.authoritative, b.base_seal_hash), (False, out["base_seal_hash"])); self.assertIn("utc_identity", b.unbound_fields)
    def _mv(self, **o):
        d = dict(instrument_id="XAUUSD", query_asof=10, snapshot_fence_ts=10, data_vintage_mode="ORIGINAL_AS_OBSERVED", timeframe_watermarks=(("H1", 10), ("H4", 9)), source_provider_identity="source_provider-v", raw_source_version="raw_source_version-v", broker_utc_rule_version="broker_utc_rule-v"); d.update(o); return man(**d)
    def test_an_UNRESOLVED_composition_and_unowned_or_disagreeing_slots_refuse_and_complete_true_binds(self):
        c, out = self._resolved("ORIGINAL_AS_OBSERVED", complete=False); self.assertEqual(out["state"], "UNRESOLVED"); mh = out["resolved_manifest_hash"]
        self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(), mh), "SNAPSHOT_COMPOSITION_NOT_SINGLE_VINTAGE_RESOLVED")
        c, out = self._resolved("ORIGINAL_AS_OBSERVED"); mh = out["resolved_manifest_hash"]; self.assertEqual(out["state"], "RESOLVED"); self.assertIsNotNone(SB.bind_snapshot_manifest(c, self._mv(), mh))
        self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(timeframe_or_event_class="D1"), mh), "SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS")
        for f in ("source_provider_identity", "raw_source_version", "broker_utc_rule_version"): self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(**{f: "OTHER"}), mh), "SNAPSHOT_FIELD_DISAGREES_WITH_RECORDED_OBSERVATION_FACTS", f)
        b = SB.bind_snapshot_manifest(c, self._mv(), mh); self.assertNotIn("source_provider_identity", b.unbound_fields); self.assertIn("utc_identity", b.unbound_fields)
    def test_each_owned_field_disagreement_refuses(self):
        c0, o0 = self._resolved(); self.assertEqual(code(SB.bind_snapshot_manifest, c0, self._mv(), o0["resolved_manifest_hash"]), "SNAPSHOT_VINTAGE_LABEL_NOT_COMPARABLE_HELD")
        c, out = self._resolved("ORIGINAL_AS_OBSERVED"); mh = out["resolved_manifest_hash"]; self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(data_vintage_mode="CURRENT_RECOMPUTED"), mh), "SNAPSHOT_VINTAGE_LABEL_NOT_COMPARABLE_HELD")                       # core vintage label 'v1' is not the manifest mode vocabulary: never guessed
        for kw, want in ((dict(instrument_id="EURUSD"), "SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS"), (dict(query_asof=9), "SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS"), (dict(timeframe_watermarks=(("H1", 10),)), "SNAPSHOT_TIMEFRAME_SET_DISAGREES"), (dict(timeframe_watermarks=(("H1", 10), ("H4", 8))), "SNAPSHOT_WATERMARK_DISAGREES_WITH_OWNING_RESOLUTION")):
            self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(**kw), mh), want, kw)
        class Stub:
            def resolved_manifest(self, h): return dict(c.resolved_manifest(mh), mixed_policy="P1")
        self.assertEqual(code(SB.bind_snapshot_manifest, Stub(), self._mv(), mh), "SNAPSHOT_COMPOSITION_NOT_SINGLE_VINTAGE_RESOLVED")
        self.assertEqual(code(SB.bind_snapshot_manifest, c, self._mv(), "0" * 64), "SNAPSHOT_RESOLVED_MANIFEST_NOT_IN_CORE"); self.assertEqual(code(SB.bind_snapshot_manifest, c, "x", mh), "SNAPSHOT_BINDING_INPUT_INVALID")
if __name__ == "__main__": unittest.main()
