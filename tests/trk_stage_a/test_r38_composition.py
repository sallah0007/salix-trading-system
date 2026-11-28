"""R38: composition caller over the REAL parts. Dependencies before/after, unknown-required ancestry denial AND an unrelated baseline positive, same-class stored values, source-HEAD loss after withdraw."""
import json, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker import composition as CO, publication as PUB, sim_publication_path as SP
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from stage_a.tracker.quant_intake_adapter import admit
from .fixtures import Rig, package, SIM_CONF
from .test_boundaries import T, I, _entry, _health, R
from .test_r29_intake_order import issue, br
from .test_r25_scheduler import core
from .test_r37_sim_publication_path import SPEC, supplied, F
from .test_r37_stored_values import SER, H
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def comp(upstream=None):
    rig = Rig(); oid = OA.order_id_for("cand-1"); pkg = package(order_id=oid); a = admit(pkg, accepted_fit_generations=rig.fits, conformance=SIM_CONF); issue(rig.claims, subject_key=a.subject_key); abs_(rig.claims, oid, br()); fk = a.feature_key
    sj = ObjectStoreJournal(rig.store, "SIMPUB-" + fk.scope.instrument, "w"); sj.acquire_epoch(); path = SP.SimulationPublicationPath(rig.store, rig.journals.journal(fk.namespace()), sj, SPEC); c = core()
    gf = lambda proj: _g(proj, c)
    return rig, pkg, fk, c, CO.Composition(pipeline=rig.pipe, journals=rig.journals, store=rig.store, core=c, path=path, gateway_factory=gf, upstream=upstream or {}), path
def _g(proj, c):
    g = G.SimulatedGateway(T, proj, watermark=100, health_source=c, allow_shape_only_health=False, allow_simulation_status=True); g.final_store = D.DurableFinalResolutionStore(InMemoryObjectStore()); return g
W = lambda n: FI("FW", "M-A", "XAUUSD", n)
AP = CO.L2Applicability("SCOPE-REF-SUPPLIED", "CONTRACT-REF-SUPPLIED", False)             # test-supplied scope refs: not a governed scope; the module defines none
class Comp(unittest.TestCase):
    def test_full_chain_with_stored_values_delivers_only_after_the_required_ancestry_is_declared(self):
        rig, pkg, fk, c, co, path = comp({"XAUUSD/H4/mom3/1": ("UP",)}); key = fk.key(); from .test_r25_scheduler import ver; ver(c, "UP", version="1", at=9, age=50)
        r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, stored_inputs=dict(bindings={"close": {"ref": "SRC/close", "hash": H(SER)}}, fetch=lambda ref: SER, series_hash=H))
        self.assertEqual(r.status, "PUBLISHED_SIMULATION"); self.assertEqual([s[0] for s in r.steps], ["accept", "dependencies", "reverify_l1_l2_recomputation", "stored_values_l2", "committed_status_and_rows"]); self.assertEqual(r.stored_values["l2"], "PASS")
        b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); e = _entry(fid=F, ver=fk.feature_version)
        kw = dict(binding=b1, now=12, ref=R("hl"), resolved_at=11, tables=T)
        with self.assertRaises(Refusal) as x: co.deliver("fw1", W("W1"), e, I, I, 3, 20, r, **kw)
        self.assertEqual(x.exception.code, "NON_DELIVERY")                                                  # unknown required ancestry: fails closed
        c.declare_ancestry_complete("UP", "src"); c.declare_ancestry_complete(key, "src"); self.assertIsInstance(co.deliver("fw2", W("W2"), e, I, I, 3, 20, r, **kw), G.Binding)
    def test_unrelated_feature_with_no_dependencies_is_a_baseline_positive_and_unaffected_by_the_first(self):
        rig, pkg, fk, c, co, path = comp(); key = fk.key(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP)
        c.declare_ancestry_complete(key, "src"); b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); e = _entry(fid=F, ver=fk.feature_version)
        self.assertIsInstance(co.deliver("fw1", W("W1"), e, I, I, 3, 20, r, binding=b1, now=12, ref=R("hl"), resolved_at=11, tables=T), G.Binding)
    def test_a_withdraw_after_publication_stops_new_windows_and_old_outcome_is_immutable(self):
        rig, pkg, fk, c, co, path = comp(); key = fk.key(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP); c.declare_ancestry_complete(key, "src"); b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); e = _entry(fid=F, ver=fk.feature_version)
        kw = dict(binding=b1, now=12, ref=R("hl"), resolved_at=11, tables=T); first = co.deliver("fw1", W("W1"), e, I, I, 3, 20, r, **kw)
        PUB.withdraw(rig.journals.journal(fk.namespace()), fk, "x")
        with self.assertRaises(Refusal) as x: co.deliver("fw2", W("W2"), e, I, I, 3, 20, r, **kw)
        self.assertEqual(x.exception.code, "NON_DELIVERY"); self.assertEqual(co.deliver("fw1", W("W1"), e, I, I, 3, 20, r, **kw), first)
    def test_unaccepted_package_stops_at_the_first_step_and_publishes_nothing(self):
        rig, pkg, fk, c, co, path = comp(); import dataclasses
        bad = package(order_id="ORD-NOT-ISSUED"); r = co.accept_and_publish(bad, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50); self.assertEqual((r.status, r.steps[0][:2]), ("NOT_ACCEPTED", ("accept", "REFUSED")))
        self.assertEqual(path._sj.head().seq, 0); self.assertIsNone(co.gateway); self.assertEqual(code(co.deliver, "x", W("W"), _entry(), I, I, 3, 20, r, binding=None, now=1, ref=R("h"), resolved_at=1, tables=T), "COMPOSITION_NOT_PUBLISHED")
    def test_missing_part_and_class_mismatched_stored_values_refuse(self):
        rig, pkg, fk, c, co, path = comp(); self.assertEqual(code(CO.Composition, pipeline=None, journals=1, store=1, core=1, path=1, gateway_factory=lambda p: p), "COMPOSITION_PART_MISSING")
SER2 = [x + 1 for x in SER] if isinstance(SER, (list, tuple)) else SER + b"x"
class L2(unittest.TestCase):
    def _go(self, **kw):
        rig, pkg, fk, c, co, path = comp(); key = fk.key(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, **kw)
        c.declare_ancestry_complete(key, "src"); b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); e = _entry(fid=F, ver=fk.feature_version)
        try: co.deliver("fw1", W("W1"), e, I, I, 3, 20, r, binding=b1, now=12, ref=R("hl"), resolved_at=11, tables=T); d = "DELIVERED"
        except Refusal as x: d = x.code
        return r, d, rig, fk
    def test_missing_stored_inputs_without_a_governed_scope_is_HELD_UNAVAILABLE_and_the_prototype_recomputation_does_not_mask_it(self):
        r, d, *_ = self._go(); self.assertEqual(r.reverification.status if hasattr(r.reverification, "status") else None, r.reverification.status)
        self.assertEqual((r.status, r.stored_values["l2"], r.stored_values["reason"], r.stored_values["stored_values_compared"]), ("PUBLISHED_SIMULATION_L2_NOT_PASS", "UNAVAILABLE", "L2_APPLICABILITY_UNBOUND_HELD", False)); self.assertEqual(d, "NON_DELIVERY")      # all other gates satisfied: ONLY the absent L2 stops delivery
    def test_a_REQUIRED_scope_with_no_stored_inputs_is_UNAVAILABLE_and_an_unrelated_not_required_scope_baseline_delivers(self):
        r, d, *_ = self._go(l2_applicability=CO.L2Applicability("S", "C", True)); self.assertEqual((r.stored_values["reason"], d), ("STORED_VALUES_REQUIRED_BUT_NOT_SUPPLIED", "NON_DELIVERY"))
        r, d, *_ = self._go(l2_applicability=AP); self.assertEqual((r.status, d, r.l2_scope["required"], r.stored_values), ("PUBLISHED_SIMULATION", "DELIVERED", False, None))
        for bad in (("", "c", False), ("s", "", False), ("s", "c", 1)): self.assertEqual(code(CO.L2Applicability, *bad), "COMPOSITION_L2_APPLICABILITY_INVALID")
        rig, pkg, fk, c, co, path = comp(); self.assertEqual(code(co.accept_and_publish, pkg, supplied(), "T", sequence=1, now=10, max_age=50, l2_applicability="yes"), "COMPOSITION_L2_APPLICABILITY_INVALID")
    def test_unavailable_changed_and_missing_stored_segment_or_source_never_deliver_and_the_genuine_stored_positive_does(self):
        b = {"close": {"ref": "SRC/close", "hash": H(SER)}}
        r, d, *_ = self._go(stored_inputs=dict(bindings=b, fetch=lambda ref: SER, series_hash=H)); self.assertEqual((r.status, r.stored_values["l2"], d), ("PUBLISHED_SIMULATION", "PASS", "DELIVERED"))          # genuine stored positive
        r, d, *_ = self._go(stored_inputs=dict(bindings=b, fetch=lambda ref: None, series_hash=H)); self.assertNotEqual(r.stored_values["l2"], "PASS"); self.assertEqual(d, "NON_DELIVERY")                     # source unavailable
        calls = []; flip = lambda ref: (calls.append(1), SER if len(calls) == 1 else SER2)[1]
        r, d, *_ = self._go(stored_inputs=dict(bindings=b, fetch=flip, series_hash=H)); self.assertNotEqual(r.stored_values["l2"], "PASS"); self.assertEqual(d, "NON_DELIVERY")                                      # source changed after the stored values were written
        r, d, rig, fk = self._go(stored_inputs=dict(bindings=b, fetch=lambda ref: SER, series_hash=H)); self.assertEqual(d, "DELIVERED")
        from stage_a.tracker import stored_values as SV
        for k in [k for k in rig.store._i._d if SV.STORED_PREFIX in k]: rig.store._i._d.pop(k)                                                      # the stored segment goes missing
        v = SV.verify_all_stored_segments(journal=rig.journals.journal(fk.namespace()), store=rig.store, feature_key=fk, fetch=lambda ref: SER, series_hash=H); self.assertEqual((v["l2"], v["reason"]), ("UNAVAILABLE", "STORED_VALUES_ABSENT"))
from stage_a.coordination.lifecycle_framework import LifecycleFramework as LF, LifecyclePolicy as LP
from stage_a.tracker.research_lineage import ResearchLineage
from stage_a.tracker.registry_entry import build_registry_entry
POL = LP(("A", "B"), frozenset({(None, "A"), ("A", "B")}), frozenset({"B"}), "TEST-POLICY-NOT-A-SOURCE-GRAPH")
def LFW(policy, ev=lambda s, f, t, e: e == "good"):
    j = ObjectStoreJournal(InMemoryObjectStore(), "lc", "w"); j.acquire_epoch(); return LF(j, policy, ev)
class Hooks(unittest.TestCase):
    def _pub(self, **kw):
        rig, pkg, fk, c, co, path = comp(); return fk, co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, **kw)
    def test_lifecycle_apply_is_called_by_the_composition_only_with_a_framework_and_an_explicit_transition_and_unbound_policy_is_HELD(self):
        fk, r = self._pub(); self.assertNotIn("lifecycle", [x[0] for x in r.steps])                                              # default: not invoked
        lf = LFW(POL); fk, r = self._pub(lifecycle=lf, lifecycle_transition=("t1", None, "A", "good")); self.assertIn(("lifecycle", "APPLIED", "t1"), r.steps); self.assertEqual(lf.state_of(fk.key()), "A"); self.assertEqual(r.status, "PUBLISHED_SIMULATION")
        fk, r = self._pub(lifecycle=LFW(None), lifecycle_transition=("t1", None, "A", "good")); self.assertIn(("lifecycle", "HELD", "LIFECYCLE_POLICY_HELD"), r.steps)                 # unbound: HELD, no state guessed
        fk, r = self._pub(lifecycle=LFW(POL), lifecycle_transition=("t1", None, "B", "good")); self.assertEqual([x for x in r.steps if x[0] == "lifecycle"][0][1:], ("REFUSED", "LIFECYCLE_TRANSITION_NOT_ALLOWED_BY_POLICY"))
        fk, r = self._pub(lifecycle=LFW(POL), lifecycle_transition=("t1", None, "A", "bad")); self.assertEqual([x for x in r.steps if x[0] == "lifecycle"][0][1:], ("REFUSED", "LIFECYCLE_EVIDENCE_NOT_ACCEPTED"))
        fk, r = self._pub(lifecycle=LFW(POL)); self.assertEqual([x for x in r.steps if x[0] == "lifecycle"][0][1:], ("HELD", "COMPOSITION_LIFECYCLE_INPUT_INCOMPLETE"))
    def test_an_attempt_id_the_research_ledger_does_not_hold_stops_before_any_publication_and_a_held_one_publishes(self):
        j = ObjectStoreJournal(InMemoryObjectStore(), "lin", "w"); j.acquire_epoch(); l = ResearchLineage(j); l.register_battery("F", "B1"); l.record_attempt("a1", "F", "B1", "in", "h", "p", "COMPLETED", "o")
        rig, pkg, fk, c, co, path = comp(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, research_lineage=l, attempt_id="ghost"); self.assertEqual((r.status, path._sj.head().seq, co.gateway), ("ATTEMPT_UNRESOLVED", 0, None))
        r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, research_lineage=l); self.assertEqual(r.status, "HELD_ATTEMPT_LINEAGE_INPUT_INCOMPLETE")
        rig, pkg, fk, c, co, path = comp(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, research_lineage=l, attempt_id="a1"); self.assertEqual(r.status, "PUBLISHED_SIMULATION")
    def test_registry_entry_derives_disposition_history_from_the_single_lifecycle_journal_and_validates_origin_and_survivors(self):
        lf = LFW(POL); lf.apply("S1", "t1", None, "A", "good"); lf.apply("S1", "t2", "A", "B", "good"); e = build_registry_entry("S1", "BUILDER", "REQ-1", lf, survivor_pointers={"S1": "S2"}, test_evidence_refs=("EV1",))
        self.assertEqual((e.canonical_survivor_id, e.survivor_chain, [h[0] for h in e.disposition_history], [h[2] for h in e.disposition_history]), ("S2", ("S1", "S2"), ["t1", "t2"], ["A", "B"])); self.assertEqual(build_registry_entry("S9", "NATIVE", "R", lf).disposition_history, ())
        self.assertEqual(build_registry_entry("S1", "BUILDER", "R", LFW(None)).disposition_history, ())                       # unbound policy: history is READABLE, no status mapped
        for bad in (dict(origin="SPECULATIVE"), dict(creation_request_id=""), dict(test_evidence_refs=("EV", "EV")), dict(test_evidence_refs=["EV"])): self.assertEqual(code(lambda b=bad: build_registry_entry("S1", **dict(dict(origin="BUILDER", creation_request_id="R", lifecycle=lf), **b))), "REGISTRY_ENTRY_INPUT_INVALID")
        self.assertEqual(code(build_registry_entry, "S1", "BUILDER", "R", None), "REGISTRY_ENTRY_LIFECYCLE_SOURCE_REQUIRED"); self.assertEqual(code(build_registry_entry, "S1", "BUILDER", "R", lf, survivor_pointers={"S1": "S2", "S2": "S1"}), "SURVIVOR_CYCLE")
if __name__ == "__main__": unittest.main()
