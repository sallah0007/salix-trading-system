"""R38 finding 2: the projection's authority class is DERIVED from the actual carrier (read-only property), never a mutable label. Not a Python security sandbox claim."""
import json, unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker import chain_status as C
from stage_a.tracker.status_projection import StatusProjection
from stage_a.gateway import contracts as G
from tests.trk_stage_a import test_boundaries as B
from .test_r12_status_projection import MV, decode, commit
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def jr(sim):
    st = InMemoryObjectStore(); st = SimulationStore(st) if sim else st
    j = ObjectStoreJournal(st, "ns", "w"); j.acquire_epoch(); return j
def proj(sim, **kw):
    j = jr(sim); commit(j, 1, C.CURRENT); p = StatusProjection(j, decode, simulation=sim, **kw); p.refresh(); return p
def res(p, allow=False):
    g = G.SimulatedGateway(B.T, p, watermark=100, allow_shape_only_health=True, allow_simulation_status=allow); g.publish(B._row()); return g.resolve("r", B._entry(), B.I, B.I, 3, 10, B._health(), True)
class Cls(unittest.TestCase):
    def test_assignment_and_deletion_of_the_label_cannot_bypass_the_default_gateway(self):
        p = proj(True); self.assertEqual(res(p).reason, "STATUS_SOURCE_SIMULATION_NOT_ALLOWED")
        with self.assertRaises(AttributeError): p.simulation = False
        with self.assertRaises(AttributeError): del p.simulation
        with self.assertRaises(AttributeError): p.carrier_class = "QUALIFIED"
        self.assertTrue(p.simulation); self.assertEqual(res(p).reason, "STATUS_SOURCE_SIMULATION_NOT_ALLOWED")
        p.__dict__["simulation"] = False                                   # an instance-dict shadow cannot beat the data descriptor
        self.assertTrue(p.simulation); self.assertEqual(res(p).reason, "STATUS_SOURCE_SIMULATION_NOT_ALLOWED")
    def test_explicit_sim_opt_in_positive_and_ordinary_qualified_positive(self):
        self.assertIsInstance(res(proj(True), allow=True), G.Binding)
        q = proj(False); self.assertEqual((q.carrier_class, q.simulation), ("QUALIFIED", False)); self.assertIsInstance(res(q), G.Binding)
    def test_constructor_mismatch_negative_both_directions(self):
        self.assertEqual(code(StatusProjection, jr(False), decode, simulation=True), "SIMULATION_PROJECTION_REQUIRES_SIMULATION_JOURNAL")
        self.assertEqual(code(StatusProjection, jr(True), decode, simulation=False), "SIMULATION_NOT_ELIGIBLE")
    def test_a_missing_or_foreign_class_is_never_defaulted_to_qualified(self):
        class Foreign:                                                      # authoritative-looking object with no derived class
            authoritative = True
            def status_at(self, mv, fence): return C.StatusFact(MV, 1, C.CURRENT, 1, False)
        self.assertEqual(res(Foreign()).reason, "STATUS_SOURCE_CLASS_UNKNOWN")
        class Lying(Foreign): carrier_class = "SOMETHING"; 
        self.assertEqual(res(Lying()).reason, "STATUS_SOURCE_CLASS_UNKNOWN")
        class SimFlag(Foreign): simulation = True
        self.assertEqual(res(SimFlag()).reason, "STATUS_SOURCE_SIMULATION_NOT_ALLOWED")
    def test_the_projection_with_an_unknown_carrier_reports_no_class(self):
        p = proj(False); p._j = object(); self.assertIsNone(p.carrier_class); self.assertFalse(p.simulation)
if __name__ == "__main__": unittest.main()
