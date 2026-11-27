"""R20: simulation taint must survive the durable/downstream path. Authority class is a property of the store (no canonical field invented)."""
import unittest
from stage_a.errors import Refusal
from stage_a.replay import replay
from stage_a.currentness import resolve_asof, EVENTUAL
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore, authority_class_of, SIMULATION, QUALIFIED
from stage_a.storage.postgres_read_model import ReadModel as RM
from stage_a.tracker import publication
from stage_a.tracker.pipeline import TrackerPipeline
from stage_a.tracker.registry import FeatureJournalSet
from tracker_component.claims import ClaimService
from .fixtures import Rig, package, ANCHOR, SIM_DUTIES, SIM_CONF, FixedClock
NS = "XAUUSD/H4/mom3"
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
class Boundary(unittest.TestCase):
    def setUp(self):
        self.r = Rig(simulation=True); self.p = package(); self.r.issue(self.p); self.o = self.r.pipe.run(self.p)
    def test_simulated_acceptance_lands_in_a_simulation_journal_only(self):
        self.assertTrue(self.o.accepted_ok and self.o.simulation)
        self.assertEqual(self.r.journals.authority_class, SIMULATION)
        self.assertEqual(authority_class_of(self.r.journals.journal(NS)), SIMULATION)
        self.assertTrue(all(k.startswith("SIMULATION/") for k in self.r.raw_store.list_prefix("")))      # nothing in the ordinary keyspace
    def test_ordinary_reader_of_the_same_bucket_sees_no_simulated_record(self):
        j = FeatureJournalSet(self.r.raw_store, "reader").journal(NS)           # a QUALIFIED reader after restart/cache rebuild over the same bucket
        self.assertEqual(j.read_from(1), []); self.assertEqual(replay(NS, j.read_from(1)), {})
        self.assertIsNone(resolve_asof(NS, j.read_from(1), mode=EVENTUAL).available_version)
    def test_publication_status_projection_and_read_model_refuse_a_simulation_journal(self):
        j = self.r.journals.journal(NS)
        self.assertEqual(code(publication.publish, j, self.o.admission.feature_key, self.o.verification), "SIMULATION_NOT_ELIGIBLE")
        self.assertEqual(code(RM().rebuild, NS, j), "SIMULATION_NOT_ELIGIBLE")
        from stage_a.tracker.status_projection import StatusProjection as P
        self.assertEqual(code(P, j, lambda r: None), "SIMULATION_NOT_ELIGIBLE")
        self.assertEqual([s.status for s in replay(NS, j.read_from(1)).values()], ["CANONICAL_ACCEPTED"])   # still never PUBLISHABLE
    def test_flag_cannot_choose_the_namespace_class(self):
        plain = InMemoryObjectStore(); sim = SimulationStore(InMemoryObjectStore())
        def mk(store, simulation):
            from tracker_component.journal_port import GENESIS_HEAD
            from stage_a.coordination.object_store_journal import ObjectStoreJournal
            cj = ObjectStoreJournal(store, "claims", "w"); cj.acquire_epoch()
            return TrackerPipeline(store=store, claims=ClaimService(cj, ANCHOR), journals=FeatureJournalSet(store, "w"), clock=FixedClock(), events=None, simulation=simulation)
        self.assertEqual(code(mk, plain, True), "AUTHORITY_CLASS_MISMATCH")        # simulation flag + qualified store: refuse
        self.assertEqual(code(mk, sim, False), "AUTHORITY_CLASS_MISMATCH")         # qualified flag + simulation store: refuse
        mk(plain, False); mk(sim, True)
    def test_mixed_class_components_refuse(self):
        sim = SimulationStore(InMemoryObjectStore()); plain = InMemoryObjectStore()
        from stage_a.coordination.object_store_journal import ObjectStoreJournal
        cj = ObjectStoreJournal(plain, "claims", "w"); cj.acquire_epoch()
        with self.assertRaises(Refusal) as c: TrackerPipeline(store=sim, claims=ClaimService(cj, ANCHOR), journals=FeatureJournalSet(sim, "w"), clock=FixedClock(), events=None, simulation=True)
        self.assertEqual(c.exception.code, "AUTHORITY_CLASS_MISMATCH")
    def test_unknown_carrier_fails_closed_and_nesting_or_subclass_is_refused(self):
        self.assertEqual(code(authority_class_of, object()), "UNKNOWN_CARRIER")
        self.assertEqual(code(SimulationStore, SimulationStore(InMemoryObjectStore())), "BAD_SIMULATION_STORE")
        class Sub(SimulationStore): pass
        self.assertEqual(code(authority_class_of, Sub(InMemoryObjectStore())), "UNKNOWN_CARRIER")          # a subclass cannot claim the simulation class
    def test_qualified_journal_still_publishes(self):                                  # positive control: the guard is not a blanket refusal
        from .fixtures import qualified_journal_from_simulated
        q = qualified_journal_from_simulated(self.r)
        self.assertEqual(authority_class_of(q), QUALIFIED)
        publication.publish(q, self.o.admission.feature_key, self.o.verification)
        self.assertEqual(resolve_asof(NS, q.read_from(1), mode=EVENTUAL).available_version, "1")
if __name__ == "__main__": unittest.main()

class ReadModelEveryEntryPoint(unittest.TestCase):
    def test_status_and_verify_each_refuse_a_simulation_journal_even_after_a_qualified_rebuild(self):
        from .fixtures import qualified_journal_from_simulated
        r = Rig(simulation=True); p = package(); r.issue(p); o = r.pipe.run(p)
        q = qualified_journal_from_simulated(r); m = RM(); m.rebuild(NS, q)
        sim = r.journals.journal(NS)
        self.assertEqual(code(m.status, NS, "1", sim), "SIMULATION_NOT_ELIGIBLE")
        self.assertEqual(code(m.verify_against, NS, sim), "SIMULATION_NOT_ELIGIBLE")
        self.assertEqual(m.status(NS, "1", q), "CANONICAL_ACCEPTED")                     # positive control
class Lineage(unittest.TestCase):
    def test_request_claim_lineage_alone_is_reported(self):
        r = Rig(simulation=True); p = package(); r.issue(p); r.pipe.run(p)
        self.assertEqual(r.claims.lineage("NO-SUCH-ORDER", p.request_id), ["REQUEST_CLAIM_EXISTS"])
        self.assertEqual(r.claims.lineage("NO-SUCH-ORDER", "NO-SUCH-REQUEST"), [])


class LabelSpoofing(unittest.TestCase):
    """R21: the class is derived from the carrier's type/keyspace; a public label (assigned, deleted, missing, spoofed) is ignored."""
    def build(self, store, simulation):
        from stage_a.coordination.object_store_journal import ObjectStoreJournal
        from stage_a.observability import EventSink
        cj = ObjectStoreJournal(store, "claims", "w"); cj.acquire_epoch(); c = ClaimService(cj, ANCHOR)
        return c, TrackerPipeline(store=store, claims=c, journals=FeatureJournalSet(store, "w"), clock=FixedClock(), events=EventSink(), conformance_source=lambda p: SIM_CONF,
                                  duty_source=lambda p, a: SIM_DUTIES, simulation=simulation)
    def test_codex_repro_labelling_an_ordinary_store_simulation_is_refused(self):
        s = InMemoryObjectStore(); s.authority_class = SIMULATION
        self.assertEqual(authority_class_of(s), QUALIFIED)
        self.assertEqual(code(self.build, s, True), "AUTHORITY_CLASS_MISMATCH")
    def test_deleting_or_assigning_labels_on_the_real_carrier_changes_nothing(self):
        r = Rig(simulation=True); p = package(); r.issue(p); o = r.pipe.run(p); ns = o.admission.feature_key.namespace()
        for obj in (r.store, r.journals, r.journals.journal(ns), r.claims):
            for val in (QUALIFIED, "LIVE", None):
                try: obj.authority_class = val
                except AttributeError: pass                                  # read-only property carriers refuse assignment
            try: del obj.authority_class
            except AttributeError: pass
            self.assertEqual(authority_class_of(obj), SIMULATION)
        self.assertEqual(code(publication.publish, r.journals.journal(ns), o.admission.feature_key, o.verification), "SIMULATION_NOT_ELIGIBLE")
        self.assertTrue(all(k.startswith("SIMULATION/") for k in r.raw_store.list_prefix("")))
    def test_wrapper_loss_cannot_surface_the_simulated_record_as_ordinary(self):
        r = Rig(simulation=True); p = package(); r.issue(p); o = r.pipe.run(p); ns = o.admission.feature_key.namespace()
        raw = r.store._i                                                     # the wrapper is stripped: a journal over the raw store sees the ORDINARY keyspace only
        from stage_a.coordination.object_store_journal import ObjectStoreJournal
        j = ObjectStoreJournal(raw, ns, "after-loss"); j.acquire_epoch()
        self.assertEqual(authority_class_of(j), QUALIFIED); self.assertEqual(j.read_from(1), [])
        self.assertEqual(code(publication.publish, j, o.admission.feature_key, o.verification), "NOT_ACCEPTED")     # nothing to publish: no simulated record became ordinary
    def test_restart_over_the_same_bucket_keeps_the_class(self):
        r = Rig(simulation=True); p = package(); r.issue(p); r.pipe.run(p)
        r2 = Rig(store=r.raw_store, simulation=True)
        self.assertEqual(authority_class_of(r2.journals), SIMULATION); self.assertTrue(r2.pipe.run(p).accepted_ok)       # idempotent replay on the simulation keyspace
    def test_ordinary_unrelated_positive_control(self):
        s = InMemoryObjectStore(); self.assertEqual(authority_class_of(s), QUALIFIED)
        c, pipe = self.build(s, False); self.assertEqual(authority_class_of(pipe._journals), QUALIFIED)
        self.assertEqual(authority_class_of(c), QUALIFIED)
