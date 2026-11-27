import copy, random, struct, unittest
from stage_a.errors import Refusal
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.schema import validate_manifest
from stage_a.composer.expression.canonical_encoding import encode_manifest, encode_graph, encode_program
from stage_a.composer.expression.hashing import manifest_hash, graph_hash, program_hash
from stage_a.composer.expression.capability import check_declared, extract_opcodes, required_capabilities
from stage_a.composer.expression.evaluator import evaluate, encode_const, decode_const
from stage_a.composer.expression.fit_generation import check_fit_refs
from stage_a.composer.expression.artifacts import build_artifact
from stage_a.tracker.materialization.stateful_materializer import IncrementalEvaluator
from .fixtures import momentum_manifest

def code(fn, *a, **k):
    try:
        fn(*a, **k)
    except Refusal as e:
        return e.code
    return None

class Schema(unittest.TestCase):
    def mutate(self, f):
        m = momentum_manifest(); f(m); return code(Manifest.from_dict, m)
    def test_valid(self):
        Manifest.from_dict(momentum_manifest())
    def test_refusals_by_code(self):
        cases = {
            "MANIFEST_FIELD_SET": lambda m: m.update(extra=1),
            "MANIFEST_SCHEMA_ID": lambda m: m.update(schema="OTHER"),
            "DUPLICATE_NODE_ID": lambda m: m["nodes"].append(dict(m["nodes"][0])),
            "UNKNOWN_OPCODE": lambda m: m["nodes"][2].update(op="mystery"),
            "EMULATED_OPCODE_REFUSED": lambda m: m["nodes"][2].update(op="exp"),
            "ARITY": lambda m: m["nodes"][2].update(args=["a"]),
            "DANGLING_ARG": lambda m: m["nodes"][2].update(args=["a", "zz"]),
            "CYCLE": lambda m: m["nodes"][1].update(args=["d"]),
            "UNREACHABLE_NODE": lambda m: m["nodes"].append({"id": "z", "op": "const", "value": encode_const(1.0)}),
            "OUTPUT_NOT_A_NODE": lambda m: m.update(output="nope"),
            "WINDOW_PARAM": lambda m: m["nodes"][3].update(n=0),
            "UNDECLARED_INPUT": lambda m: m["nodes"][0].update(name="open"),
            "DECLARED_INPUTS_NOT_EQUAL_USED": lambda m: m["inputs"].append("volume"),
            "CONST_NOT_BINARY64_HEX": lambda m: m["nodes"].__setitem__(1, {"id": "b", "op": "const", "value": "1.0"}),
            "FIT_REF_HASH": lambda m: m.update(fit_refs=[{"generation": 1, "ref_hash": "zz"}]),
            "DUPLICATE_FIT_GENERATION": lambda m: m.update(fit_refs=[{"generation": 1, "ref_hash": "a" * 64}] * 2),
            "BAD_IDENTIFIER_TOKEN": lambda m: m.update(instrument="XAU/USD"),
            "NODE_FIELD_SET": lambda m: m["nodes"][2].update(n=3),
        }
        for want, f in cases.items():
            self.assertEqual(self.mutate(f), want, want)
    def test_nonfinite_const_refused(self):
        m = momentum_manifest(); m["nodes"][1] = {"id": "b", "op": "const", "value": "7ff0000000000000"}
        M = Manifest.from_dict(m)    # schema allows the bit pattern; evaluation must refuse it
        self.assertEqual(code(evaluate, M, {"close": [1.0, 2.0]}), "NON_FINITE_CONST")

class Hashing(unittest.TestCase):
    def test_declaration_order_invariance(self):
        base = Manifest.from_dict(momentum_manifest()); h = manifest_hash(base)
        rng = random.Random(1)
        for _ in range(20):
            m = momentum_manifest(); rng.shuffle(m["nodes"]); rng.shuffle(m["declared_opcodes"]); rng.shuffle(m["declared_capabilities"])
            self.assertEqual(manifest_hash(Manifest.from_dict(m)), h)
    def test_args_order_is_semantic(self):
        a = momentum_manifest(); b = momentum_manifest(); b["nodes"][2]["args"] = ["b", "a"]
        self.assertNotEqual(manifest_hash(Manifest.from_dict(a)), manifest_hash(Manifest.from_dict(b)))
    def test_each_field_is_hash_covered(self):
        h0 = manifest_hash(Manifest.from_dict(momentum_manifest()))
        muts = [lambda m: m.update(feature_version="2"), lambda m: m.update(feature_id="other"),
                lambda m: m.update(timeframe="H1"), lambda m: m.update(instrument="EURUSD"),
                lambda m: m["nodes"][3].update(n=4), lambda m: m["nodes"][3].update(op="rolling_sum"),
                lambda m: m.update(fit_refs=[{"generation": 1, "ref_hash": "a" * 64}])]
        for f in muts:
            m = momentum_manifest(); f(m)
            if m["nodes"][3]["op"] == "rolling_sum":
                m["declared_opcodes"] = ["input", "lag", "rolling_sum", "sub"]
            self.assertNotEqual(manifest_hash(Manifest.from_dict(m)), h0)
    def test_graph_hash_ignores_const_value_program_hash_does_not(self):
        def with_const(v):
            m = momentum_manifest()
            m["nodes"].append({"id": "k", "op": "const", "value": encode_const(v)})
            m["nodes"].append({"id": "e", "op": "mul", "args": ["d", "k"]}); m["output"] = "e"
            m["declared_opcodes"] = ["const", "input", "lag", "mul", "rolling_mean", "sub"]
            m["declared_capabilities"] = ["ARITH_BINARY64", "CONST_BINARY64", "INPUT_SERIES", "WINDOW_LAG", "WINDOW_ROLLING"]
            return Manifest.from_dict(m)
        a, b = with_const(2.0), with_const(3.0)
        self.assertEqual(graph_hash(a), graph_hash(b)); self.assertNotEqual(program_hash(a), program_hash(b))
        self.assertNotEqual(manifest_hash(a), manifest_hash(b))
    def test_program_hash_ignores_identity_metadata(self):
        a = Manifest.from_dict(momentum_manifest()); b = Manifest.from_dict(momentum_manifest(feature_id="alias", version="9"))
        self.assertEqual(program_hash(a), program_hash(b)); self.assertNotEqual(manifest_hash(a), manifest_hash(b))
    def test_unvalidated_manifest_not_encodable(self):
        self.assertEqual(code(encode_manifest, momentum_manifest()), "UNVALIDATED_MANIFEST")

class Capability(unittest.TestCase):
    def test_declared_must_equal_extracted(self):
        m = momentum_manifest(); m["declared_opcodes"].append("sqrt")
        self.assertEqual(code(check_declared, Manifest.from_dict(m)), "OPCODE_DECLARATION_MISMATCH")
        m = momentum_manifest(); m["declared_capabilities"].remove("WINDOW_LAG")
        self.assertEqual(code(check_declared, Manifest.from_dict(m)), "CAPABILITY_DECLARATION_MISMATCH")
    def test_provider_missing_capability_refused(self):
        self.assertEqual(code(check_declared, Manifest.from_dict(momentum_manifest()), frozenset({"INPUT_SERIES"})), "CAPABILITY_NOT_PROVIDED")
    def test_extraction(self):
        M = Manifest.from_dict(momentum_manifest())
        self.assertEqual(extract_opcodes(M), ["input", "lag", "rolling_mean", "sub"])

class Evaluator(unittest.TestCase):
    CLOSE = [1.0, 2.0, 4.0, 7.0, 11.0]
    def test_hand_derived_values(self):
        # diff = [-,1,2,3,4]; 3-bar mean over diff -> first defined at t=3: (1+2+3)/3=2.0, t=4: (2+3+4)/3=3.0
        self.assertEqual(evaluate(Manifest.from_dict(momentum_manifest()), {"close": self.CLOSE}), [None, None, None, 2.0, 3.0])
    def test_causal_no_lookahead(self):
        M = Manifest.from_dict(momentum_manifest())
        full = evaluate(M, {"close": self.CLOSE})
        for cut in range(len(self.CLOSE) + 1):
            self.assertEqual(evaluate(M, {"close": self.CLOSE[:cut]}), full[:cut])
    def test_future_perturbation_does_not_change_past(self):
        M = Manifest.from_dict(momentum_manifest()); a = evaluate(M, {"close": self.CLOSE})
        b = evaluate(M, {"close": self.CLOSE[:3] + [999.0, -999.0]})
        self.assertEqual(a[:3], b[:3])
    def test_undefined_semantics(self):
        m = momentum_manifest()
        m["nodes"] = [{"id": "a", "op": "input", "name": "close"}, {"id": "z", "op": "const", "value": encode_const(0.0)},
                      {"id": "q", "op": "div", "args": ["a", "z"]}, {"id": "l", "op": "log", "args": ["a"]},
                      {"id": "s", "op": "sqrt", "args": ["a"]}, {"id": "o", "op": "add", "args": ["q", "l"]},
                      {"id": "p", "op": "add", "args": ["o", "s"]}]
        m["output"] = "p"; m["declared_opcodes"] = ["add", "const", "div", "input", "log", "sqrt"]
        m["declared_capabilities"] = ["ARITH_BINARY64", "CONST_BINARY64", "ELEMENTARY_BINARY64", "INPUT_SERIES"]
        self.assertEqual(evaluate(Manifest.from_dict(m), {"close": [4.0, -1.0]}), [None, None])
    def test_overflow_is_refusal_not_value(self):
        m = momentum_manifest()
        m["nodes"] = [{"id": "a", "op": "input", "name": "close"}, {"id": "m", "op": "mul", "args": ["a", "a"]}]
        m["output"] = "m"; m["declared_opcodes"] = ["input", "mul"]; m["declared_capabilities"] = ["ARITH_BINARY64", "INPUT_SERIES"]
        self.assertEqual(code(evaluate, Manifest.from_dict(m), {"close": [1e200]}), "NON_FINITE_RESULT")
    def test_input_boundary_strict(self):
        M = Manifest.from_dict(momentum_manifest())
        self.assertEqual(code(evaluate, M, {"close": [1.0, float("nan")]}), "INPUT_NOT_FINITE_BINARY64")
        self.assertEqual(code(evaluate, M, {"close": [1, 2]}), "INPUT_NOT_FINITE_BINARY64")
        self.assertEqual(code(evaluate, M, {"close": [1.0], "open": [1.0]}), "INPUT_SET_MISMATCH")
        self.assertEqual(code(evaluate, M, {}), "INPUT_SET_MISMATCH")
    def test_const_roundtrip_bit_exact(self):
        for x in (0.1, -0.0, 5e-324, 1.7976931348623157e308):
            self.assertEqual(struct.pack(">d", decode_const(encode_const(x))), struct.pack(">d", x))
    def test_incremental_equals_batch_bit_exact(self):
        M = Manifest.from_dict(momentum_manifest()); rng = random.Random(3)
        series = [None if i % 7 == 3 else rng.uniform(-5, 5) for i in range(60)]
        batch = evaluate(M, {"close": series}); inc = IncrementalEvaluator(M)
        got = [inc.push({"close": x}) for x in series]
        self.assertEqual([None if x is None else struct.pack(">d", x) for x in batch],
                         [None if x is None else struct.pack(">d", x) for x in got])
    def test_no_model_name_dispatch_in_evaluator_source(self):
        import ast, inspect
        import stage_a.composer.expression.evaluator as ev
        tree = ast.parse(inspect.getsource(ev))
        banned = {"feature_id", "feature_version", "instrument", "timeframe"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Subscript,)) and isinstance(node.slice, ast.Constant) and node.slice.value in banned:
                self.fail("evaluator reads %s" % node.slice.value)
            if isinstance(node, ast.Attribute) and node.attr in banned and not (isinstance(node.value, ast.Name) and node.value.id == "m" and False):
                self.fail("evaluator touches %s" % node.attr)

class FitGen(unittest.TestCase):
    def test_boundary(self):
        ok = [{"generation": 2, "ref_hash": "b" * 64}]
        check_fit_refs(ok, {1: "a" * 64, 2: "b" * 64})
        self.assertEqual(code(check_fit_refs, [{"generation": 1, "ref_hash": "a" * 64}], {1: "a" * 64, 2: "b" * 64}), "FIT_GENERATION_STALE")
        self.assertEqual(code(check_fit_refs, [{"generation": 3, "ref_hash": "c" * 64}], {1: "a" * 64}), "FIT_GENERATION_UNKNOWN")
        self.assertEqual(code(check_fit_refs, [{"generation": 2, "ref_hash": "x" * 64}], {2: "b" * 64}), "FIT_REF_HASH_MISMATCH")

class Artifact(unittest.TestCase):
    def test_artifact_bytes_are_manifest_bytes(self):
        M = Manifest.from_dict(momentum_manifest()); a = build_artifact(M)
        self.assertEqual(a.manifest_bytes, encode_manifest(M)); self.assertEqual(a.manifest_hash, manifest_hash(M))

if __name__ == "__main__":
    unittest.main()
