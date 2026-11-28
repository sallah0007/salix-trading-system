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
if __name__ == "__main__": unittest.main()
