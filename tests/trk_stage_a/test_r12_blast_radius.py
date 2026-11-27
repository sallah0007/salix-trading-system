"""R12: blast radius over supplied lineage. OB2 positive control, proven/undetermined separation, no status copying."""
import unittest
from stage_a.errors import Refusal
from stage_a.fw.lanes import ConsumerManifest as M
from stage_a.health import blast_radius as B
from stage_a.fw.lanes import closure_contains_target as CT, closure_features as CF
Q, A, X, Y = b"quant", b"base-a", b"feat-x", b"feat-y"
def run(consumers, deps=None, **kw): return B.blast_radius(Q, {m.manifest_id: m for m in consumers}, deps if deps is not None else {Q: (), A: (), X: (Q,), Y: (X,)}, CT, closure_features=CF, **kw)
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
        self.assertEqual(run([M("base", "FW", (A,))], {Q: (), A: ()}, unread_features=[A])["base"].verdict, B.UNDETERMINED)   # R18: unread must be in THIS consumer's closure
    def test_proven_dependency_wins_over_unread_ancestry(self):
        r = run([M("m", "FW", (Q,), derived_from="missing")]); self.assertEqual(r["m"].verdict, B.AFFECTED)
    def test_output_carries_no_health_state_and_is_deterministic(self):
        r1 = run([M("base", "FW", (A,)), M("model", "FW", (Q,))]); r2 = run([M("model", "FW", (Q,)), M("base", "FW", (A,))])
        self.assertEqual(r1, r2); self.assertEqual(list(r1), ["base", "model"])
        self.assertFalse(any("state" in f for f in B.CarriedUpstreamImpact.__dataclass_fields__))
    def test_failed_subject_must_be_an_identity(self):
        for bad in ("quant", b"", None):
            with self.assertRaises(Refusal): B.blast_radius(bad, {}, {}, CT, CF)
    def test_feature_dependency_cycle_terminates(self):
        r = run([M("m", "FW", (X,))], {Q: (X,), X: (Q,)}); self.assertEqual(r["m"].verdict, B.AFFECTED)
class Use(unittest.TestCase):
    def test_consumer_use_matrix(self):
        aff = B.CarriedUpstreamImpact("c", B.AFFECTED, Q); un = B.CarriedUpstreamImpact("c", B.UNAFFECTED, Q); ud = B.CarriedUpstreamImpact("c", B.UNDETERMINED, Q, (), "DERIVED_FROM_UNRESOLVED")
        self.assertEqual(B.consumer_use(aff, True), "BLOCK_PROVEN_DEPENDENCY"); self.assertEqual(B.consumer_use(aff, False), "BLOCK_PROVEN_DEPENDENCY")
        self.assertEqual(B.consumer_use(un, True), "ALLOW_PROVEN_INDEPENDENT"); self.assertEqual(B.consumer_use(un, False), "ALLOW_PROVEN_INDEPENDENT")
        self.assertEqual(B.consumer_use(ud, True), "REFUSE_UNPROVEN_INDEPENDENCE")
        self.assertEqual(B.consumer_use(ud, False), "NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE")
    def test_end_to_end_required_orphan_refused_while_independent_branch_allowed(self):
        r = run([M("ok", "FW", (A,)), M("orphan", "FW", (A,), derived_from="missing")])
        self.assertEqual(B.consumer_use(r["ok"], True), "ALLOW_PROVEN_INDEPENDENT"); self.assertEqual(B.consumer_use(r["orphan"], True), "REFUSE_UNPROVEN_INDEPENDENCE")

class ConsumerSpecific(unittest.TestCase):
    """R18 (Codex reproduction): incompleteness is judged over the consumer's OWN dependency closure, never globally."""
    BASE = M("independent-baseline", "ML", ())
    def test_empty_resolved_closure_is_not_contaminated_by_unrelated_unread_lineage(self):
        for deps, kw in (({b"unrelated": (b"unread-parent",)}, {}), ({b"unrelated": ()}, {"unread_features": (b"other-unread",)})):
            r = B.blast_radius(b"failed", {self.BASE.manifest_id: self.BASE}, deps, CT, CF, **kw)[self.BASE.manifest_id]
            self.assertEqual(r.verdict, B.UNAFFECTED, deps); self.assertEqual(B.consumer_use(r, True), "ALLOW_PROVEN_INDEPENDENT")
    def test_a_required_consumer_whose_own_ancestry_features_are_unread_is_still_refused(self):
        m = M("c", "FW", (A,))
        for deps, kw in (({A: (b"unread-parent",)}, {}), ({A: ()}, {"unread_features": (A,)}), ({A: (X,), X: ()}, {"unread_features": (X,)}), ({}, {})):
            r = run([m], deps, **kw)["c"]
            self.assertEqual((r.verdict, B.consumer_use(r, True)), (B.UNDETERMINED, "REFUSE_UNPROVEN_INDEPENDENCE"), (deps, kw))
    def test_unread_lineage_in_a_derived_ancestors_closure_counts_for_the_child(self):
        r = run([M("parent", "FW", (A,)), M("child", "FW", (), derived_from="parent")], {A: (b"unread",)})
        self.assertEqual(r["child"].verdict, B.UNDETERMINED)
    def test_mixed_batch_only_the_consumer_with_unread_closure_is_undetermined(self):
        r = run([M("ok", "FW", (A,)), M("bad", "FW", (X,))], {A: (), X: (b"unread",)}, unread_features=[b"other"])
        self.assertEqual((r["ok"].verdict, r["bad"].verdict), (B.UNAFFECTED, B.UNDETERMINED))
    def test_proven_and_cross_instrument_propagation_preserved(self):
        r = run([M("viaY", "ML", (Y,)), M("free", "ML", ())], {Q: (), X: (Q,), Y: (X,)}, unread_features=[b"elsewhere"])
        self.assertEqual((r["viaY"].verdict, r["free"].verdict), (B.AFFECTED, B.UNAFFECTED))
    def test_omitted_or_non_callable_closure_proof_is_refused_not_silently_global(self):         # R19: the R18 opt-in default retained the original over-blocking
        for kw in ({}, {"closure_features": None}, {"closure_features": "x"}):
            with self.assertRaises(Refusal) as c: B.blast_radius(b"failed", {"independent-baseline": self.BASE}, {b"unrelated": (b"unread-parent",)}, CT, **kw)
            self.assertEqual(c.exception.code, "CLOSURE_PROOF_ADAPTER_REQUIRED")
        with self.assertRaises(Refusal): B.blast_radius(b"failed", {}, {}, None, CF)
    def test_cyclic_feature_lineage_is_never_proven_independence(self):                           # R19 (Codex reproduction): m('cyclic','ML',(a,)), a<->b
        m = M("cyclic", "ML", (b"a",))
        r = B.blast_radius(b"failed", {"cyclic": m}, {b"a": (b"b",), b"b": (b"a",)}, CT, CF)["cyclic"]
        self.assertEqual((r.verdict, r.reason, B.consumer_use(r, True)), (B.UNDETERMINED, "FEATURE_LINEAGE_CYCLIC", "REFUSE_UNPROVEN_INDEPENDENCE"))
        for deps in ({b"a": (b"a",)}, {b"a": (b"b",), b"b": (b"c",), b"c": (b"a",)}):
            self.assertEqual(B.blast_radius(b"failed", {"cyclic": m}, deps, CT, CF)["cyclic"].reason, "FEATURE_LINEAGE_CYCLIC", deps)
    def test_a_cycle_elsewhere_does_not_contaminate_a_resolved_consumer(self):
        r = B.blast_radius(b"failed", {"ok": M("ok", "ML", (A,)), "bad": M("bad", "ML", (b"a",))}, {A: (), b"a": (b"b",), b"b": (b"a",)}, CT, CF)
        self.assertEqual((r["ok"].verdict, r["bad"].verdict), (B.UNAFFECTED, B.UNDETERMINED))
    def test_diamond_lineage_is_not_a_cycle(self):
        r = B.blast_radius(b"failed", {"d": M("d", "ML", (b"t",))}, {b"t": (b"l", b"r"), b"l": (b"base",), b"r": (b"base",), b"base": ()}, CT, CF)
        self.assertEqual(r["d"].verdict, B.UNAFFECTED)
class GraphKeyBinding(unittest.TestCase):
    """The Health closure seam must not treat a misbound ancestry as proven independence, nor assume a validating caller."""
    def test_misbound_derivation_key_is_undetermined_in_both_probes(self):
        child = M("child", "FW", (A,), derived_from="p"); wrong = M("other-id", "FW", (Q,))           # graph key 'p' holds a manifest whose id is different
        graph = {"child": child, "p": wrong}
        for fn, args in ((CT, (child, Q, graph)), (CF, (child, graph))):
            with self.assertRaises(Refusal) as c: fn(*args)
            self.assertEqual(c.exception.code, "GRAPH_KEY_MISMATCH")
        r = B.blast_radius(Q, graph, {Q: (), A: ()}, CT, closure_features=CF)
        self.assertEqual((r["child"].verdict, r["child"].reason), (B.UNDETERMINED, "GRAPH_KEY_MISMATCH"))
    def test_consumer_registered_under_a_foreign_key_is_undetermined(self):
        r = B.blast_radius(Q, {"x": M("y", "FW", (A,))}, {A: ()}, CT, closure_features=CF)
        self.assertEqual((r["x"].verdict, r["x"].reason), (B.UNDETERMINED, "CONSUMER_KEY_MISMATCH"))
    def test_correctly_bound_chain_is_unchanged(self):
        r = run([M("parent", "FW", (A,)), M("child", "FW", (), derived_from="parent")]); self.assertEqual(r["child"].verdict, B.UNAFFECTED)
class ProbeEdges(unittest.TestCase):
    def test_upstream_incomplete_directly(self):
        D = B.upstream_lineage_defect
        self.assertIsNone(D([X], Q, {X: (Q,)}, ()))                                  # reaching the failed subject is proof, not 'unread lineage'
        self.assertEqual(D([X], Q, {X: (A,)}, ()), "FEATURE_LINEAGE_INCOMPLETE")      # A's own lineage never supplied
        self.assertIsNone(D([], Q, {}, [b"z"]))
    def test_artifact_closure_features_count_toward_the_closure(self):
        self.assertEqual(CF(M("a", "ML", (A,), artifact_closure_features=(X,)), {}), {A, X})
        self.assertEqual(run([M("a", "ML", (), artifact_closure_features=(b"unread-art",))], {})["a"].verdict, B.UNDETERMINED)
    def test_closure_features_refuses_cycles_directly(self):
        a, b = M("a", "FW", (A,), derived_from="b"), M("b", "FW", (A,), derived_from="a")
        with self.assertRaises(Refusal) as c: CF(a, {"a": a, "b": b})
        self.assertEqual(c.exception.code, "DERIVATION_CYCLE")
    def test_a_closure_probe_that_refuses_makes_the_consumer_undetermined_with_its_code(self):
        def bad(m, consumers): raise Refusal("x", code="PROBE_REFUSED")
        r = B.blast_radius(Q, {"c": M("c", "FW", (A,))}, {A: ()}, CT, closure_features=bad)["c"]
        self.assertEqual((r.verdict, r.reason), (B.UNDETERMINED, "PROBE_REFUSED"))
if __name__ == "__main__": unittest.main()

class FailedSubjectEndpoint(unittest.TestCase):
    def test_the_failed_subject_is_a_proof_endpoint_even_with_no_lineage_of_its_own(self):
        self.assertIsNone(B.upstream_lineage_defect([b"f"], b"f", {}, ()))
        self.assertEqual(B.upstream_lineage_defect([b"x"], b"f", {}, ()), "FEATURE_LINEAGE_INCOMPLETE")
