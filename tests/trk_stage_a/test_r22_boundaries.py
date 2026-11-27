"""R22 corrective boundary cases from the PR45 review (D1 adapter inheritance, D2 ML gateway=None / consumer-request association)."""
import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore, authority_class_of, approve_test_adapter, _APPROVED_TEST_ADAPTERS, QUALIFIED, require_qualified
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.gateway import contracts as G
from stage_a.ml import receiver as ML
from .test_boundaries import _entry, _gw, _health, I, J, R, NONE_
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
class AdapterInheritance(unittest.TestCase):
    def test_codex_repro_subclass_delegating_to_a_simulation_store_is_not_qualified(self):
        sim = SimulationStore(InMemoryObjectStore())
        class Wrapper(InMemoryObjectStore):
            def get(self, k): return sim.get(k)
            def put_if_absent(self, k, d): return sim.put_if_absent(k, d)
            def put_if_match(self, k, d, e): return sim.put_if_match(k, d, e)
            def list_prefix(self, p): return sim.list_prefix(p)
        w = Wrapper()
        self.assertEqual(code(authority_class_of, w), "UNKNOWN_CARRIER")
        self.assertEqual(code(ObjectStoreJournal, w, "ns", "w") or code(lambda: authority_class_of(ObjectStoreJournal(w, "ns", "w"))), "UNKNOWN_CARRIER")
        self.assertEqual(code(require_qualified, w, "publication"), "UNKNOWN_CARRIER")
    def test_exact_approved_type_is_still_qualified_positive_control_and_explicit_approval_works(self):
        self.assertEqual(authority_class_of(InMemoryObjectStore()), QUALIFIED)
        class Fault(InMemoryObjectStore): pass
        self.assertEqual(code(authority_class_of, Fault()), "UNKNOWN_CARRIER")
        approve_test_adapter(Fault)
        try: self.assertEqual(authority_class_of(Fault()), QUALIFIED)          # explicit, reviewed approval (not a security sandbox)
        finally: _APPROVED_TEST_ADAPTERS.remove(Fault)
class MlGatewayRequired(unittest.TestCase):
    def setUp(self):
        self.gw = _gw(); self.e = _entry(opt=True, fid=J); self.good = self.gw.resolve("o", self.e, I, I, 3, 10, _health())
    def row(self, gw, outs, **k): return ML.build_row("r", R("gen"), [self.e], outs, gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, **k)
    def test_codex_repro_gateway_none_with_matching_never_issued_absence_is_refused(self):
        fake = G.AbsenceApplied("never-issued", self.good.feature_id, self.good.feature_version, self.e.absence_rule_ref)
        self.assertEqual(code(self.row, None, [fake]), "GATEWAY_REQUIRED_FOR_VERIFIED_ML_ROW")
        self.assertEqual(code(self.row, None, [self.good]), "GATEWAY_REQUIRED_FOR_VERIFIED_ML_ROW")
    def test_issued_outcome_positive_control_and_consumer_request_association(self):
        self.assertTrue(self.row(self.gw, [self.good]).included)
        k = (self.e.feature_id, self.e.feature_version)
        self.assertTrue(self.row(self.gw, [self.good], expected_request_ids={k: "o"}).included)
        other = self.gw.resolve("other-consumer", self.e, I, I, 3, 10, _health())           # genuinely ISSUED, but for another request
        self.assertEqual(code(self.row, self.gw, [other], expected_request_ids={k: "o"}), "OUTCOME_FOR_DIFFERENT_CONSUMER_REQUEST")
if __name__ == "__main__": unittest.main()
