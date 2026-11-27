"""R12: blast radius over supplied lineage. OB2 positive control, proven/undetermined separation, no status copying."""
import unittest
from stage_a.errors import Refusal
from stage_a.fw.lanes import ConsumerManifest as M
from stage_a.health import blast_radius as B
Q, A, X, Y = b"quant", b"base-a", b"feat-x", b"feat-y"
def run(consumers, deps=None, **kw): return B.blast_radius(Q, {m.manifest_id: m for m in consumers}, deps if deps is not None else {Q: (), A: (), X: (Q,), Y: (X,)}, **kw)
class T(unittest.TestCase):
    def test_ob2_unrelated_baseline_is_not_blocked_while_quant_consumer_is(self):
        r = run([M("base", "FW", (A,)), M("model", "FW", (Q,))])
        self.assertEqual(r["base"].verdict, B.UNAFFECTED); self.assertFalse(B.must_block(r["base"]))
        self.assertEqual(r["model"].verdict, B.AFFECTED); self.assertTrue(B.must_block(r["model"]))
    def test_transitive_feature_dependency_is_proven(self):
        r = run([M("viaY", "ML", (Y,))]); self.assertEqual(r["viaY"].verdict, B.AFFECTED); self.assertIn(Y, r["viaY"].via)
    def test_hidden_ancestry_through_derivation_and_artifact_closure(self):
        g = [M("parent", "FW", (Q,)), M("child", "FW", (A,), derived_from="parent"), M("art", "ML", (A,), artifact_closure_features=(X,))]
        r = run(g); self.assertEqual(r["child"].verdict, B.AFFECTED); self.assertEqual(r["art"].verdict, B.AFFECTED)
    def test_unresolved_ancestry_is_undetermined_not_unaffected_and_not_blocked(self):
        r = run([M("orphan", "FW", (A,), derived_from="missing")])
        self.assertEqual(r["orphan"].verdict, B.UNDETERMINED); self.assertEqual(r["orphan"].reason, "DERIVED_FROM_UNRESOLVED"); self.assertFalse(B.must_block(r["orphan"]))
    def test_derivation_cycle_is_undetermined(self):
        r = run([M("a", "FW", (A,), derived_from="b"), M("b", "FW", (A,), derived_from="a")]); self.assertEqual(r["a"].verdict, B.UNDETERMINED)
    def test_incomplete_feature_lineage_makes_absence_undetermined(self):
        deps = {Q: (), X: (Q,), A: (b"never-supplied",)}
        self.assertEqual(run([M("base", "FW", (A,))], deps)["base"].verdict, B.UNDETERMINED)
        self.assertEqual(run([M("base", "FW", (A,))], {Q: (), A: ()}, unread_features=[b"z"])["base"].verdict, B.UNDETERMINED)
    def test_proven_dependency_wins_over_unread_ancestry(self):
        r = run([M("m", "FW", (Q,), derived_from="missing")]); self.assertEqual(r["m"].verdict, B.AFFECTED)
    def test_output_carries_no_health_state_and_is_deterministic(self):
        r1 = run([M("base", "FW", (A,)), M("model", "FW", (Q,))]); r2 = run([M("model", "FW", (Q,)), M("base", "FW", (A,))])
        self.assertEqual(r1, r2); self.assertEqual(list(r1), ["base", "model"])
        self.assertFalse(any("state" in f for f in B.CarriedUpstreamImpact.__dataclass_fields__))
    def test_failed_subject_must_be_an_identity(self):
        for bad in ("quant", b"", None):
            with self.assertRaises(Refusal): B.blast_radius(bad, {}, {})
    def test_feature_dependency_cycle_terminates(self):
        r = run([M("m", "FW", (X,))], {Q: (X,), X: (Q,)}); self.assertEqual(r["m"].verdict, B.AFFECTED)
if __name__ == "__main__": unittest.main()
