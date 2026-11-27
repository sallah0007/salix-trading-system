import ast, os, types, unittest
from stage_a.errors import Refusal
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.canonical_encoding import encode_manifest
from stage_a.composer.expression.hashing import manifest_hash, graph_hash, program_hash
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker.materialization.stateful_materializer import StatefulMaterializer
from stage_a.tracker.verification import stateful_verifier as real
from stage_a.tracker.verification.stateful_verifier import verify_materialization, probe_for
from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
from stage_a.tracker.verification import independent_hashing as ih
from stage_a.tracker.verification.verification_result import (make_result, PASS, FAIL, SCOPE_MATERIALIZATION)
from .fixtures import momentum_manifest

def _read(path):
    with open(path) as fh:
        return fh.read()

VDIR = os.path.join(os.path.dirname(real.__file__))
STDLIB_OK = {"json", "hashlib", "math", "struct", "functools", "operator", "dataclasses", "typing"}

class StaticIndependence(unittest.TestCase):
    def test_verifier_imports_nothing_from_producer_side(self):
        seen = 0
        for fn in sorted(os.listdir(VDIR)):
            if not fn.endswith(".py"):
                continue
            tree = ast.parse(_read(os.path.join(VDIR, fn)))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        self.assertIn(a.name.split(".")[0], STDLIB_OK, "%s imports %s" % (fn, a.name)); seen += 1
                elif isinstance(node, ast.ImportFrom):
                    seen += 1
                    if node.level == 0:
                        self.assertIn((node.module or "").split(".")[0], STDLIB_OK, "%s imports %s" % (fn, node.module))
                    elif node.level == 1:
                        self.assertTrue(node.module.startswith("independent_") or node.module in ("verification_result",), "%s -> .%s" % (fn, node.module))
                    elif node.level == 3:
                        self.assertEqual(node.module, "errors", "%s -> %s" % (fn, node.module))
                    else:
                        self.fail("%s: unexpected relative import level %d" % (fn, node.level))
        self.assertGreater(seen, 10)
    def test_verifier_does_not_use_json_dumps_for_encoding(self):
        for fn in os.listdir(VDIR):
            if fn.endswith(".py"):
                for node in ast.walk(ast.parse(_read(os.path.join(VDIR, fn)))):
                    if isinstance(node, ast.Attribute) and node.attr == "dumps":
                        self.fail("%s calls .dumps" % fn)
    def test_producer_side_does_not_import_verifier(self):
        root = os.path.dirname(os.path.dirname(VDIR))   # stage_a/
        for sub in ("composer", os.path.join("tracker", "materialization")):
            for dp, _, fs in os.walk(os.path.join(root, sub)):
                for f in fs:
                    if f.endswith(".py"):
                        src = _read(os.path.join(dp, f))
                        self.assertNotIn("verification", src.replace("verification_hash", ""), os.path.join(dp, f))

class EncodingAgreement(unittest.TestCase):
    def test_independent_encoder_agrees_with_composer_bytes(self):
        for m in (momentum_manifest(), momentum_manifest(feature_id="x-y.z", version="12", window=5)):
            M = Manifest.from_dict(m)
            raw = encode_manifest(M)
            self.assertEqual(enc_bytes(parse(raw)), raw)
            self.assertEqual(ih.manifest_digest(raw), manifest_hash(M))
            p = parse(raw)
            self.assertEqual(ih.graph_digest(p, enc_bytes), graph_hash(M))
            self.assertEqual(ih.program_digest(p, enc_bytes), program_hash(M))
    def test_independent_string_escaping_matches_stdlib_on_hard_cases(self):
        import json
        for s in ['a"b', "a\\b", "tab\t", "nl\n", "\x00\x1f", "\x7f", "é", "日本", "\U0001F600", "mixed  "]:
            self.assertEqual(enc_bytes(s), json.dumps(s, ensure_ascii=True).encode("ascii"), repr(s))
    def test_strict_parse_rejects_duplicates_floats_nan(self):
        for bad in (b'{"a":1,"a":2}', b'{"a":1.5}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(ValueError): parse(bad)

class Result(unittest.TestCase):
    def test_no_truthiness(self):
        r = make_result(PASS, SCOPE_MATERIALIZATION, {"k": "v"}, [("c", True)], [])
        with self.assertRaises(TypeError): bool(r)
        with self.assertRaises(TypeError): if_ = (True if r else False)
    def test_scope_and_status_enforced(self):
        r = make_result(PASS, SCOPE_MATERIALIZATION, {}, [], [])
        self.assertIs(r.require_pass(SCOPE_MATERIALIZATION), r)
        with self.assertRaises(Refusal) as c: r.require_pass("SOME_OTHER_SCOPE")
        self.assertEqual(c.exception.code, "VERIFICATION_SCOPE_MISMATCH")
        f = make_result(FAIL, SCOPE_MATERIALIZATION, {}, [("c", False)], ["c"])
        with self.assertRaises(Refusal) as c: f.require_pass(SCOPE_MATERIALIZATION)
        self.assertEqual(c.exception.code, "VERIFICATION_NOT_PASS")
    def test_result_hash_covers_status_reasons_subject(self):
        a = make_result(PASS, SCOPE_MATERIALIZATION, {"k": "1"}, [("c", True)], [])
        for b in (make_result(FAIL, SCOPE_MATERIALIZATION, {"k": "1"}, [("c", True)], []),
                  make_result(PASS, SCOPE_MATERIALIZATION, {"k": "2"}, [("c", True)], []),
                  make_result(PASS, SCOPE_MATERIALIZATION, {"k": "1"}, [("c", False)], []),
                  make_result(PASS, SCOPE_MATERIALIZATION, {"k": "1"}, [("c", True)], ["x"])):
            self.assertNotEqual(a.result_hash, b.result_hash)

# ---------------------------------------------------------------- verification scenarios
KEY = "XAUUSD/H4/mom3/1"

def good_world(manifest_dict=None):
    store = InMemoryObjectStore()
    M = Manifest.from_dict(manifest_dict or momentum_manifest())
    raw = encode_manifest(M)
    rec = StatefulMaterializer(store).materialize(M, probe_for(raw))
    declared = {"manifest_hash": manifest_hash(M), "graph_hash": graph_hash(M), "program_hash": program_hash(M)}
    return store, M, rec, declared

def run(mod, store, rec, declared, key=KEY):
    return mod.verify_materialization(store_get=lambda k: (lambda g: None if g is None else g[0])(store.get(k)),
                                      record=rec, declared=declared, expect_scope_key=key)

def failing_checks(res):
    return {n for n, ok in res.checks if not ok}

class VerifierBehaviour(unittest.TestCase):
    def test_good_world_passes(self):
        s, M, rec, d = good_world(); r = run(real, s, rec, d)
        self.assertEqual(r.status, PASS, r.reasons)
    def test_each_defect_is_caught_by_its_own_check(self):
        for name, build in SCENARIOS.items():
            s, rec, d, key = build()
            r = run(real, s, rec, d, key)
            self.assertEqual(r.status, FAIL, name)
            self.assertIn(name, failing_checks(r), "%s: %s" % (name, r.reasons))
    def test_missing_artifact_is_insufficient_evidence_not_pass(self):
        s, M, rec, d = good_world(); s._d.clear()
        self.assertEqual(run(real, s, rec, d).status, "INSUFFICIENT_EVIDENCE")
    def test_record_with_extra_or_missing_field_fails(self):
        s, M, rec, d = good_world()
        for bad in (dict(rec, extra=1), {k: v for k, v in rec.items() if k != "program_hash"}):
            self.assertEqual(run(real, s, bad, d).status, FAIL)
    def test_garbage_artifact_fails_closed(self):
        s, M, rec, d = good_world(); k = rec["object_key"]; s._d[k] = (b"not json", 5)
        self.assertEqual(run(real, s, dict(rec, byte_length=8), d).status, FAIL)

def _flip(bits):
    return bits[:-1] + ("0" if bits[-1] != "0" else "1")

def sc_declared_manifest_hash():
    s, M, rec, d = good_world(); return s, rec, dict(d, manifest_hash="0" * 64), KEY
def sc_declared_graph_hash():
    s, M, rec, d = good_world(); return s, rec, dict(d, graph_hash="0" * 64), KEY
def sc_identity_artifact_vs_request():
    # record AND request agree on a different key; only the artifact itself disagrees
    s, M, rec, d = good_world(); return s, dict(rec, feature_key="XAUUSD/H4/other/1"), d, "XAUUSD/H4/other/1"
def sc_equivalence_batch():
    s, M, rec, d = good_world()
    b = list(rec["probe_batch"]); i = next(i for i, x in enumerate(b) if x is not None); b[i] = _flip(b[i])
    return s, dict(rec, probe_batch=b), d, KEY
def sc_equivalence_incremental():
    s, M, rec, d = good_world()
    b = list(rec["probe_incremental"]); i = next(i for i, x in enumerate(b) if x is not None); b[i] = _flip(b[i])
    return s, dict(rec, probe_incremental=b), d, KEY
def sc_object_key():
    s, M, rec, d = good_world(); other = "artifact/" + "e" * 64
    s._d[other] = s._d[rec["object_key"]]; return s, dict(rec, object_key=other), d, KEY
def sc_byte_length():
    s, M, rec, d = good_world(); return s, dict(rec, byte_length=rec["byte_length"] + 1), d, KEY
def sc_opcode_declaration():
    m = momentum_manifest(); m["declared_opcodes"] = ["input", "lag", "sub"]    # omits rolling_mean
    s, M, rec, d = good_world(m); return s, rec, d, KEY

SCENARIOS = {"declared_manifest_hash": sc_declared_manifest_hash, "declared_graph_hash": sc_declared_graph_hash,
             "identity_binding_artifact_vs_request": sc_identity_artifact_vs_request,
             "equivalence_probe_batch": sc_equivalence_batch, "equivalence_probe_incremental": sc_equivalence_incremental,
             "object_key_is_content_address": sc_object_key, "byte_length": sc_byte_length}

def sc_opcode_declaration_unvalidated():
    """The composer schema does not enforce declaration==extraction; the verifier must (own check)."""
    return None

SRC = _read(real.__file__)

def load_mutant(old, new):
    assert SRC.count(old) == 1, old
    mod = types.ModuleType("stage_a.tracker.verification._mutant")
    mod.__package__ = "stage_a.tracker.verification"; mod.__file__ = real.__file__
    exec(compile(SRC.replace(old, new), real.__file__, "exec"), mod.__dict__)
    return mod

MUTANTS = [   # (check name, source text to neuter)
    ("declared_manifest_hash", 'chk("declared_manifest_hash", declared.get("manifest_hash") == manifest_digest(raw))',
     'chk("declared_manifest_hash", True)'),
    ("declared_graph_hash", 'chk("declared_graph_hash", declared.get("graph_hash") == graph_digest(p, enc_bytes))',
     'chk("declared_graph_hash", True)'),
    ("identity_binding_artifact_vs_request", 'chk("identity_binding_artifact_vs_request", key == expect_scope_key, key)',
     'chk("identity_binding_artifact_vs_request", True)'),
    ("equivalence_probe_batch", 'chk("equivalence_" + name, isinstance(got, list) and got == ref)',
     'chk("equivalence_" + name, True)'),
    ("object_key_is_content_address", 'chk("object_key_is_content_address", record["object_key"] == "artifact/" + record["manifest_hash"])',
     'chk("object_key_is_content_address", True)'),
    ("byte_length", 'chk("byte_length", len(raw) == record["byte_length"])', 'chk("byte_length", True)'),
]

class TestsCanFail(unittest.TestCase):
    """Break the verifier on purpose; the matching scenario must then slip through, proving the scenario test has teeth."""
    def test_every_neutered_check_lets_its_defect_through(self):
        for check, old, new in MUTANTS:
            mut = load_mutant(old, new)
            scenario = {"equivalence_probe_batch": sc_equivalence_batch}.get(check) or SCENARIOS[check]
            s, rec, d, key = scenario()
            self.assertEqual(run(real, s, rec, d, key).status, FAIL, "real verifier must fail " + check)
            self.assertEqual(run(mut, s, rec, d, key).status, PASS, "mutant verifier should be blind to " + check)
    def test_unmutated_copy_behaves_identically(self):
        mut = load_mutant('chk("byte_length", len(raw) == record["byte_length"])', 'chk("byte_length", len(raw) == record["byte_length"])')
        s, rec, d, key = sc_byte_length()
        self.assertEqual(run(mut, s, rec, d, key).status, FAIL)

class OpcodeDeclarationCheck(unittest.TestCase):
    def test_verifier_catches_declaration_mismatch_even_when_hashes_are_self_consistent(self):
        # hand-build bytes whose declared_opcodes omit rolling_mean; hashes made consistent so only the declaration check can object
        m = momentum_manifest(); m["declared_opcodes"] = ["input", "lag", "sub"]
        nodes = sorted(m["nodes"], key=lambda n: n["id"]); m = dict(m, nodes=nodes, inputs=sorted(m["inputs"]))
        raw = enc_bytes(m); h = ih.manifest_digest(raw)
        store = InMemoryObjectStore(); store._d["artifact/" + h] = (raw, 1)
        p = parse(raw)
        rec = {"feature_key": KEY, "feature_version": "1", "instrument": "XAUUSD", "timeframe": "H4",
               "object_key": "artifact/" + h, "manifest_hash": h, "graph_hash": ih.graph_digest(p, enc_bytes),
               "program_hash": ih.program_digest(p, enc_bytes), "byte_length": len(raw), "materialization_hash": "x"}
        from stage_a.tracker.verification.independent_traversal import reference_evaluate, bits, make_probe
        ref = [bits(x) for x in reference_evaluate(p, make_probe(p["inputs"]))]
        rec.update(probe_batch=ref, probe_incremental=ref)
        d = {"manifest_hash": h, "graph_hash": rec["graph_hash"], "program_hash": rec["program_hash"]}
        r = run(real, store, rec, d)
        self.assertEqual(r.status, FAIL); self.assertEqual(failing_checks(r), {"opcode_declaration_equals_extracted"})

if __name__ == "__main__":
    unittest.main()
