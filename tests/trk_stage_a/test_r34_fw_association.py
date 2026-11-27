import unittest
from stage_a.errors import Refusal
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from stage_a.fw.association import FwAssociation, HELD_PAYLOAD
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
ID = FI("FW", "B1", "XAUUSD", "W1"); OTHER = FI("FW", "B1", "XAUUSD", "W2"); ML = FI("ML", "B1", "XAUUSD", "W1")
class Assoc(unittest.TestCase):
    def mk(self):
        s = FinalResolutionStore(); s.resolve("R1", ID, lambda: "OUT1"); return s, FwAssociation(s)
    def test_request_must_be_bound_by_the_store_and_have_an_outcome_and_be_fw(self):
        s, a = self.mk(); self.assertEqual(a.associate_request("R1", ID), "OUT1")
        s.resolve("R2", ID, lambda: "NEVER"); self.assertEqual(a.associate_request("R2", ID), "OUT1")                      # many-to-one: new request id, same stored outcome, no re-evaluation
        self.assertEqual(s.evaluations, 1)
        self.assertEqual(code(a.associate_request, "R9", ID), "FW_REQUEST_NOT_BOUND_TO_IDENTITY_BY_STORE")                    # never seen by the store
        self.assertEqual(code(a.associate_request, "R1", OTHER), "FW_REQUEST_NOT_BOUND_TO_IDENTITY_BY_STORE")                 # right request, other window
        s.resolve("R1", ML, lambda: "MLOUT"); self.assertEqual(code(a.associate_request, "R1", ML), "FW_ASSOCIATION_NOT_AN_FW_REQUEST")
    def test_returns_have_permitted_classes_unbound_payload_and_are_immutable(self):
        s, a = self.mk(); r = a.record_return("F1", "R1", "EVIDENCE"); self.assertEqual((r.payload_binding, r.resolution_identity), (HELD_PAYLOAD, ID))
        self.assertIs(a.record_return("F1", "R1", "EVIDENCE"), r)                                                              # identical retry
        self.assertEqual(code(a.record_return, "F1", "R1", "REQUEST"), "FW_RETURN_IMMUTABLE")
        self.assertEqual(code(a.record_return, "F2", "R1", "FEATURE"), "FW_RETURN_CLASS_NOT_PERMITTED")
        self.assertEqual(code(a.record_return, "F2", "R1", "EVIDENCE", payload={"x": 1}), "FW_RETURN_PAYLOAD_NOT_ACCEPTED_UNBOUND")
        self.assertEqual(code(a.record_return, "F3", "RX", "EVIDENCE"), "FW_RETURN_FOR_UNASSOCIATED_REQUEST")
        self.assertEqual(code(a.record_return, "F4", "R1", "LINEAGE"), "FW_LINEAGE_RETURN_WITHOUT_LINEAGE_REF"); self.assertEqual(code(a.record_return, "F4", "R1", "REQUEST", lineage_ref="L"), "FW_LINEAGE_REF_ON_NON_LINEAGE_RETURN")
    def test_lineage_is_found_by_identity_and_a_later_return_never_rewrites_the_outcome(self):
        s, a = self.mk(); a.record_return("L1", "R1", "LINEAGE", lineage_ref="LIN-1"); s.resolve("R2", ID, lambda: "X"); a.record_return("E2", "R2", "EVIDENCE")
        self.assertTrue(a.has_lineage_return(ID, "LIN-1")); self.assertFalse(a.has_lineage_return(ID, "LIN-2")); self.assertFalse(a.has_lineage_return(OTHER, "LIN-1"))
        self.assertEqual([r.return_id for r in a.returns_for(ID)], ["L1", "E2"]); self.assertEqual(s.outcome_for(ID), "OUT1")
if __name__ == "__main__": unittest.main()

class FinalOutcomeImmutability(unittest.TestCase):
    def H1(self): return {"PACKAGE_HASH": "original", "OMISSIONS": [{"reason": "original"}]}
    def test_public_reads_and_the_evaluators_object_cannot_rewrite_the_stored_final_outcome(self):
        s = FinalResolutionStore(); a = FwAssociation(s); mine = self.H1(); first = s.resolve("R1", ID, lambda: mine)
        mine["OMISSIONS"][0]["reason"] = "EVALUATOR_MUTATED"; first["OMISSIONS"][0]["reason"] = "RESOLVE_RETURN_MUTATED"                     # evaluator-owned object and the resolve() return
        got = a.associate_request("R1", ID); self.assertEqual(got, self.H1()); got["OMISSIONS"][0]["reason"] = "ASSOC_READ_MUTATED"; got["PACKAGE_HASH"] = "x"
        s.outcome_for(ID)["OMISSIONS"].append("y")
        retry = s.resolve("R2", ID, lambda: {"never": 1}); self.assertEqual(retry, self.H1()); retry["OMISSIONS"][0]["reason"] = "RETRY_RETURN_MUTATED"; self.assertEqual(s.resolve("R3", ID, lambda: {"never": 1}), self.H1()); self.assertEqual(s.evaluations, 1)                       # genuine same-identity retry returns the ORIGINAL
        a.record_return("L1", "R1", "LINEAGE", lineage_ref="LIN-1"); self.assertEqual(s.outcome_for(ID), self.H1())                        # a later return preserves the outcome
