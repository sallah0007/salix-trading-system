"""R11: SQE_OPSET_V1_1 arithmetic alignment (Parent V1.2 Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM lines 116-204; Annex V1.2 Drive
13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA lines 84-121). Materializer / verifier agreement on domain failures, certification outcomes, signed zero.
Mutants: mutation_sweep_r11.py."""
import struct, unittest
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.evaluator import encode_const
from stage_a.composer.expression import opcodes
from stage_a.tracker.verification.stateful_verifier import verify_materialization
from stage_a.tracker.verification import independent_traversal as it
from stage_a.tracker.quant_certification import certify
from .fixtures import momentum_manifest
from .test_verifier_independence import good_world, run, real, failing_checks, KEY
from stage_a.tracker.verification.verification_result import PASS, FAIL

def man(nodes, ops, caps, out):
    m = momentum_manifest(); m["nodes"] = nodes; m["output"] = out; m["declared_opcodes"] = ops; m["declared_capabilities"] = caps
    return m
A = {"id": "a", "op": "input", "name": "close"}
SQRT = lambda: man([A, {"id": "s", "op": "sqrt", "args": ["a"]}], ["input", "sqrt"], ["ELEMENTARY_BINARY64", "INPUT_SERIES"], "s")
DIV = lambda: man([A, {"id": "z", "op": "const", "value": encode_const(0.0)}, {"id": "q", "op": "div", "args": ["a", "z"]}],
                  ["const", "div", "input"], ["ARITH_BINARY64", "CONST_BINARY64", "INPUT_SERIES"], "q")
NEG = lambda: man([A, {"id": "n", "op": "neg", "args": ["a"]}], ["input", "neg"], ["ARITH_BINARY64", "INPUT_SERIES"], "n")

class DomainFailureAgreement(unittest.TestCase):
    def test_probe_domain_failure_is_recorded_identically_and_verifies(self):
        # the verifier-authored edge probe contains negatives/zeros, so sqrt and div-by-zero programs hit domain failures on it
        for mk in (SQRT, DIV):
            store, M, rec, declared = good_world(mk())
            self.assertEqual(rec["probe_batch"], {"error": "DOMAIN_FAILURE"}); self.assertEqual(rec["probe_incremental"], {"error": "DOMAIN_FAILURE"})
            self.assertEqual(run(real, store, rec, declared).status, PASS, failing_checks(run(real, store, rec, declared)))
    def test_materializer_claiming_values_where_reference_refuses_fails(self):
        store, M, rec, declared = good_world(SQRT())
        rec = dict(rec, probe_batch=[None] * 48)                         # a materializer that returned values instead of refusing
        r = run(real, store, rec, declared); self.assertEqual(r.status, FAIL); self.assertIn("equivalence_probe_batch", failing_checks(r))
    def test_reference_refuses_with_the_same_category(self):
        for mk in (SQRT, DIV):
            from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
            p = parse(enc_bytes(Manifest.from_dict(mk()).data))
            with self.assertRaises(it.RefEvalError) as e: it.reference_evaluate(p, it.make_probe(p["inputs"]))
            self.assertEqual(str(e.exception), "DOMAIN_FAILURE")
    def test_certification_proves_causality_on_a_domain_safe_transform_when_the_edge_probe_refuses(self):
        probe = it.make_probe(["close"])
        for mk in (SQRT, DIV):
            c = certify(Manifest.from_dict(mk()), probe)
            if mk is SQRT:
                self.assertEqual(c.status, "CERTIFIED", c.reasons)         # edge probe refuses; safe transform (positive) proves prefix causality
            else:
                self.assertEqual(c.status, "REFUSED")                      # x/0 refuses on EVERY row, even domain-safe: causality unproven -> not certified
                self.assertIn("prefix_causality", ",".join(c.reasons))
    def test_certification_still_catches_a_noncausal_outcome_when_values_exist(self):
        c = certify(Manifest.from_dict(momentum_manifest()), it.make_probe(["close"]))
        self.assertEqual(c.status, "CERTIFIED", c.reasons)

PASSTHROUGH = lambda: man([A], ["input"], ["INPUT_SERIES"], "a")
class SignedZeroAtOutputBoundary(unittest.TestCase):
    def test_input_that_is_the_output_is_canonicalised_by_all_three_implementations(self):
        from stage_a.composer.expression.evaluator import evaluate
        M = Manifest.from_dict(PASSTHROUGH())
        self.assertEqual(struct.pack(">d", evaluate(M, {"close": [-0.0]})[0]), struct.pack(">d", 0.0))
        store, M, rec, declared = good_world(PASSTHROUGH())
        z = struct.pack(">d", 0.0).hex()
        self.assertEqual(rec["probe_batch"][5], z); self.assertEqual(rec["probe_incremental"][5], z)     # edge probe holds -0.0 at t=5
        self.assertEqual(run(real, store, rec, declared).status, PASS)
        from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
        p = parse(enc_bytes(M.data)); self.assertEqual(struct.pack(">d", it.reference_evaluate(p, {"close": [-0.0]})[0]), struct.pack(">d", 0.0))

class SignedZeroInReference(unittest.TestCase):
    def test_reference_canonicalises_signed_zero(self):
        from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
        p = parse(enc_bytes(Manifest.from_dict(NEG()).data))
        out = it.reference_evaluate(p, {"close": [0.0, -0.0, 2.0]})
        self.assertEqual([struct.pack(">d", x) for x in out], [struct.pack(">d", 0.0), struct.pack(">d", 0.0), struct.pack(">d", -2.0)])
    def test_reference_preserves_subnormals(self):
        from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
        p = parse(enc_bytes(Manifest.from_dict(NEG()).data))
        self.assertEqual(it.reference_evaluate(p, {"close": [5e-324]}), [-5e-324])

class OpsetSurface(unittest.TestCase):
    def test_log_absent_from_both_tables_and_listed_as_not_admitted(self):
        self.assertNotIn("log", opcodes.OPCODES); self.assertNotIn("log", it._OPS)
        self.assertEqual(opcodes.NOT_ADMITTED_PROFILE_ONLY, frozenset({"log"}))
    def test_every_admitted_opcode_has_a_source_mapping_or_is_a_labelled_structural_construct(self):
        mapped = {"add", "sub", "mul", "div", "neg", "abs", "sqrt", "min", "max", "rolling_sum", "rolling_mean"}
        structural = {"input", "const", "lag"}
        self.assertEqual(set(opcodes.OPCODES), mapped | structural)          # adding an opcode forces this mapping to be revisited
    def test_independent_table_equals_composer_table(self):
        self.assertEqual({k: (v.arity, v.windowed, v.capability) for k, v in opcodes.OPCODES.items()}, dict(it._OPS))

if __name__ == "__main__":
    unittest.main()
