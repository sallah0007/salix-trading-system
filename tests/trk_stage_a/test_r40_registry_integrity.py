"""R40: integrated Registry-377 checker over actual entry/lifecycle/relationship/B19 objects, plus the SAME-OBJECT composition route: a held feature is denied while an unrelated feature through the SAME Rig/Core/pipeline delivers."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.tracker import registry_integrity as RI, version_diff as VD, relationship_store as RS, composition as CO, sim_publication_path as SP, evidence_resolver as ER, l2_scope as L2S
from stage_a.tracker.registry_entry import build_registry_entry
from stage_a.tracker.evidence_truth import EvidenceRecord, TransitionClaim
from stage_a.health import adapters as AD
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.coordination.lifecycle_framework import LifecycleFramework as LF, LifecyclePolicy as LP
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from stage_a.tracker.quant_intake_adapter import admit
from .fixtures import Rig, package, SIM_CONF, momentum_manifest, IDENTITY_FIELDS
from .test_r29_intake_order import issue, br, rec
from .test_r25_scheduler import core
from .test_boundaries import T, I, _entry, R
from .test_r37_sim_publication_path import SPEC, supplied
from .test_r37_version_diff import S, BASE
from .test_r38_composition import _g, AP, RES
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
POL = LP(("A", "B"), frozenset({(None, "A"), ("A", "B")}), frozenset({"B"}), "TEST-POLICY-NOT-A-SOURCE-GRAPH")
def lf(): j = ObjectStoreJournal(InMemoryObjectStore(), "lc", "w"); j.acquire_epoch(); f = LF(j, POL, lambda s, a, b, e: e == "good"); f.apply("S1", "t1", None, "A", "good"); return f
def ev(ref="E1", **o):
    d = dict(ref=ref, subject="S1", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B", vintage="V", dependencies=(), result="PASS", available_at=10, max_age=100, revoked=False, current=True, approval_state="APPROVED"); d.update(o); return EvidenceRecord(**d)
def claim(**o):
    d = dict(subject="S1", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B", vintage="V", dependencies=(), expected_result="PASS", required_approval="APPROVED", evidence_refs=("E1",)); d.update(o); return TransitionClaim(**d)
class Fx:
    def __init__(self, admitted=True, ptr=None, content=None):
        self.lf = lf(); j = ObjectStoreJournal(InMemoryObjectStore(), "evid", "w"); j.acquire_epoch(); self.es = ER.JournalEvidenceStore(j, "candidate"); self.es.put(ev())
        if admitted: self.es.admission = "TEST-ADMISSION-NOT-A-GOVERNED-ONE"
        self.res = ER.EvidenceResolver(self.es); self.pins = {"E1": self.es.snapshot()[1]["E1"][1]}
        self.ptr = ptr if ptr is not None else {"S1": "S2"}; self.C = content or {"S1": dict(BASE), "S2": dict(BASE, source_path="p2")}
        rj = ObjectStoreJournal(InMemoryObjectStore(), "rel", "w"); rj.acquire_epoch(); self.rs = RS.RelationshipStore(rj, lambda x: x in self.C, schema=S, content_of=self.C.get); self.rs.append(VD.compute(S, "S1", self.C["S1"], "S2", self.C["S2"]))
        self.entry = build_registry_entry("S1", "BUILDER", "REQ-1", self.lf, survivor_pointers=self.ptr, test_evidence_refs=("E1",))
    def run(self, **o):
        kw = dict(lifecycle=self.lf, relationships=self.rs, schema_version="DS1", survivor_pointers=self.ptr, owner_check=lambda x: x in self.C, evidence_resolver=self.res, evidence_claim=claim(), evidence_pins=self.pins, now=20, watermark=15, creation_request_known=lambda r, s: r == "REQ-1" and s == "S1"); kw.update(o)
        return RI.check_registry_entry(kw.pop("entry", self.entry), **kw)
st = lambda rep: {f.check: (f.state, f.code) for f in rep.findings}
class Checker(unittest.TestCase):
    def test_everything_bound_and_admitted_passes_as_facts_only_and_is_never_authoritative(self):
        r = Fx().run(); self.assertEqual((r.overall, r.authoritative), ("CHECKS_PASS_FACTS_ONLY", False)); self.assertTrue(all(f.state == "OK" for f in r.findings)); o = AD.from_registry_integrity(r); self.assertEqual((o.kind, o.scope, o.facts["overall"]), ("REGISTRY_INTEGRITY", "SUBJECT", "CHECKS_PASS_FACTS_ONLY")); self.assertIsNone(AD.from_registry_integrity(object()).facts)
    def test_unadmitted_evidence_store_unbound_sources_and_missing_refs_are_UNKNOWN_never_health(self):
        self.assertEqual(st(Fx(admitted=False).run())["evidence_admission"], ("UNKNOWN", "EVIDENCE_STORE_NOT_ADMITTED_HELD")); self.assertEqual(Fx(admitted=False).run().overall, "UNKNOWN")
        f = Fx()
        for kw, chk, why in ((dict(creation_request_known=None), "entry_integrity", "CREATION_REQUEST_SOURCE_UNBOUND"), (dict(creation_request_known=lambda r, s: None), "entry_integrity", "CREATION_REQUEST_UNRESOLVED"), (dict(owner_check=None), "survivor_chain", "OWNER_CHECK_UNBOUND"), (dict(relationships=None), "relationship", "RELATIONSHIP_STORE_OR_SCHEMA_UNBOUND"), (dict(evidence_resolver=None), "load_bearing_evidence", "EVIDENCE_RESOLVER_OR_CLAIM_UNBOUND"), (dict(schema_version="DSX"), "relationship", "NO_RECORD_UNDER_CURRENT_SCHEMA")):
            r = f.run(**kw); self.assertEqual((r.overall, st(r)[chk]), ("UNKNOWN", ("UNKNOWN", why)), why)
        e2 = build_registry_entry("S1", "BUILDER", "REQ-1", f.lf, survivor_pointers=f.ptr); self.assertEqual(st(f.run(entry=e2))["load_bearing_evidence"], ("UNKNOWN", "NO_EVIDENCE_REFS_ON_ENTRY"))
    def test_foreign_stale_revoked_altered_or_unbound_claims_are_NOT_LIVE_SAFE(self):
        f = Fx(); self.assertEqual(st(f.run(evidence_claim=claim(subject="OTHER")))["load_bearing_evidence"], ("NOT_LIVE_SAFE", "EVIDENCE_CLAIM_DOES_NOT_BIND_ENTRY")); self.assertEqual(st(f.run(evidence_claim=claim(evidence_refs=("E1", "E2"))))["load_bearing_evidence"][0], "NOT_LIVE_SAFE")
        self.assertEqual(st(f.run(now=1000))["load_bearing_evidence"][0], "NOT_LIVE_SAFE"); self.assertEqual(st(f.run(evidence_pins={"E1": "0" * 64}))["load_bearing_evidence"][0], "NOT_LIVE_SAFE")
        self.assertEqual(st(f.run(evidence_claim=claim(version_or_hash="v2")))["load_bearing_evidence"][0], "NOT_LIVE_SAFE")
        f.es.revoke("E1", "r"); r = f.run(); self.assertEqual((r.overall, st(r)["load_bearing_evidence"][0]), ("NOT_LIVE_SAFE", "NOT_LIVE_SAFE"))
    def test_entry_history_survivor_chain_and_relationship_defects_are_NOT_LIVE_SAFE(self):
        f = Fx(); forged = dataclasses.replace(f.entry, disposition_history=(("t9", None, "B", "good", "p"),)); self.assertEqual(st(f.run(entry=forged))["entry_integrity"], ("NOT_LIVE_SAFE", "DISPOSITION_HISTORY_DIFFERS_FROM_LIFECYCLE_JOURNAL"))
        self.assertEqual(st(f.run(creation_request_known=lambda r, s: False))["entry_integrity"], ("NOT_LIVE_SAFE", "CREATION_REQUEST_NOT_ASSOCIATED_WITH_SUBJECT")); self.assertEqual(st(f.run(entry=dataclasses.replace(f.entry, origin="X")))["entry_integrity"][0], "NOT_LIVE_SAFE")
        self.assertEqual(st(f.run(owner_check=lambda x: x == "S1"))["survivor_chain"], ("NOT_LIVE_SAFE", "SURVIVOR_NOT_LIVE_IN_OWNING_JOURNAL")); self.assertEqual(st(f.run(survivor_pointers={"S1": "S2", "S2": "S1"}))["survivor_chain"], ("NOT_LIVE_SAFE", "SURVIVOR_CYCLE"))
        self.assertEqual(st(f.run(survivor_pointers={"S1": "S3"}))["survivor_chain"][0], "NOT_LIVE_SAFE")                                       # entry chain differs from the pointers
        f.C["S2"]["source_path"] = "p9"; f.C["S2"]["formula"] = "fz"; self.assertEqual(st(f.run())["relationship"], ("NOT_LIVE_SAFE", "RECORD_DOES_NOT_MATCH_RECOMPUTATION"))             # content moved: the compute path no longer reproduces the record
        g = Fx(ptr={}); self.assertEqual(st(g.run(survivor_pointers={}))["relationship"], ("OK", "NO_SURVIVOR_POINTER"))
    def test_safe_quarantine_does_not_wait_for_context_metadata_and_restoration_stays_held(self):
        good, bad = Fx().run(), Fx(admitted=False).run(); self.assertEqual(RI.quarantine_decision(bad), {"quarantine": "PERMITTED_NOT_WAITING_FOR_CONTEXT_METADATA", "restoration": "HELD_MISSING_GOVERNED_METADATA"})
        self.assertEqual(RI.quarantine_decision(bad, {"ctx": 1})["restoration"], "HELD_INTEGRITY_NOT_PASSING"); self.assertEqual(RI.quarantine_decision(good)["restoration"], "HELD_MISSING_GOVERNED_METADATA"); self.assertTrue(RI.quarantine_decision(good, {"ctx": 1})["restoration"].startswith("METADATA_AND_CHECKS_PRESENT_TRANSITION_STILL_NEEDS_LIFECYCLE_AUTHORITY"))
        self.assertEqual(code(RI.quarantine_decision, object()), "REGISTRY_INTEGRITY_INPUT_INVALID"); self.assertEqual(code(RI.check_registry_entry, object(), lifecycle=None), "REGISTRY_INTEGRITY_INPUT_INVALID")
FB = bytes(range(48, 64))
class SameObjects(unittest.TestCase):
    """ONE Rig (store/claims/journals/pipeline) and ONE Core: feature A is held by the integrity gate and required-ancestry, feature B (unrelated) is delivered through the same objects."""
    def _feature(self, rig, c, fid, n):
        oid = OA.order_id_for("cand-%d" % n); p = package(momentum_manifest(feature_id=fid, window=2 + n), identity_fields=dict(IDENTITY_FIELDS, parameters={"lookback_bars": 2 + n}), request_id="REQ-%d" % n, attempt_id="ATT-%d" % n, order_id=oid); a = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF); issue(rig.claims, rec(CANDIDATE_IDENTITY="cand-%d" % n), subject_key=a.subject_key); abs_(rig.claims, oid, br(CANDIDATE_IDENTITY="cand-%d" % n))
        fk = a.feature_key; sj = ObjectStoreJournal(rig.store, "SIMPUB-%s-%s" % (fk.scope.instrument, fid), "w"); sj.acquire_epoch(); path = SP.SimulationPublicationPath(rig.store, rig.journals.journal(fk.namespace()), sj, SPEC)
        return p, fk, CO.Composition(pipeline=rig.pipe, journals=rig.journals, store=rig.store, core=c, path=path, gateway_factory=lambda proj: _g(proj, c), l2_scope_resolver=RES)
    def _deliver(self, co, c, fk, r, tag, fid=None):
        fid = fid or supplied().feature_id
        c.declare_ancestry_complete(fk.key(), "src"); b = G.HealthBinding(fid, fk.feature_version, I, I); c.associate_subject(fk.key(), b, "assoc"); e = _entry(fid=fid, ver=fk.feature_version)
        try: return co.deliver("fw-" + tag, FI("FW", "M-A", "XAUUSD", tag), e, I, I, 3, 20, r, binding=b, now=12, ref=R("hl-" + tag), resolved_at=11, tables=T)
        except Refusal as x: return x.code
    def test_a_registry_held_feature_is_denied_while_an_unrelated_feature_on_the_same_rig_and_core_delivers(self):
        rig = Rig(); c = core(); pa, fka, coa = self._feature(rig, c, "mom3", 1); pb, fkb, cob = self._feature(rig, c, "mom4", 2)
        bad = Fx(admitted=False); gate_bad = lambda key, fk: bad.run(); good = Fx(); gate_good = lambda key, fk: good.run()
        ra = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, registry_gate=gate_bad); self.assertEqual(ra.status, "HELD_REGISTRY_INTEGRITY_UNKNOWN"); self.assertIsNone(coa.gateway); self.assertEqual(code(coa.deliver, "x", FI("FW", "M-A", "XAUUSD", "x"), _entry(), I, I, 3, 20, ra, binding=None, now=1, ref=R("h"), resolved_at=1, tables=T), "COMPOSITION_NOT_PUBLISHED")
        rb = cob.accept_and_publish(pb, supplied(feature_id=bytes(range(48, 64))), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, registry_gate=gate_good); self.assertEqual(rb.status, "PUBLISHED_SIMULATION")
        self.assertTrue(rig.journals.journal(fka.namespace()).head().seq >= 1)                                                       # A WAS accepted (acceptance is not undone); only publication is held
        self.assertIsInstance(self._deliver(cob, c, fkb, rb, "B1", FB), G.Binding)                                                   # the unrelated feature DELIVERS through the same Rig/Core/pipeline/Gateway code
    def test_required_unknown_ancestry_denies_one_feature_while_the_unrelated_baseline_delivers_on_the_same_objects_then_the_declared_ancestry_delivers_it(self):
        from .test_r25_scheduler import ver
        rig = Rig(); c = core(); pa, fka, coa = self._feature(rig, c, "mom3", 1); pb, fkb, cob = self._feature(rig, c, "mom4", 2); coa._up = {fka.key(): ("UP",)}; ver(c, "UP", version="1", at=9, age=50); good = Fx(); gate = lambda key, fk: good.run()
        ra = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, registry_gate=gate); rb = cob.accept_and_publish(pb, supplied(feature_id=bytes(range(48, 64))), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, registry_gate=gate)
        self.assertEqual((ra.status, rb.status), ("PUBLISHED_SIMULATION", "PUBLISHED_SIMULATION"))
        self.assertEqual(self._deliver(coa, c, fka, ra, "A1"), "NON_DELIVERY")                                                     # required upstream ancestry unknown: denied
        self.assertIsInstance(self._deliver(cob, c, fkb, rb, "B1", FB), G.Binding)                                                    # unrelated baseline, SAME objects, delivers
        c.declare_ancestry_complete("UP", "src"); self.assertIsInstance(self._deliver(coa, c, fka, ra, "A2"), G.Binding)          # after the declared ancestry the denied feature delivers
if __name__ == "__main__": unittest.main()
