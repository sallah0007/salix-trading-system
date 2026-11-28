"""R46: lazy demand evaluation honours the exact indices read by lag/rolling (warm-up reads nothing), preserves TAKEN failures, and the
independent reference agrees (root reproductions 1; plus a seeded differential over random typed DAGs). A pass clears no gate."""
import random, unittest
from stage_a.errors import Refusal
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.evaluator import encode_const, evaluate
from stage_a.tracker.verification import independent_traversal as it
from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
from .test_r11_arithmetic import man, A
from .test_verifier_independence import good_world, run, real, failing_checks
from stage_a.tracker.verification.verification_result import PASS

C = lambda i, x: {"id": i, "op": "const", "value": encode_const(x)}
ALLCAPS = ["ARITH_BINARY64", "COMPARE_BINARY64", "CONST_BINARY64", "INPUT_SERIES", "SELECT_BOUNDED", "WINDOW_LAG", "WINDOW_ROLLING", "ELEMENTARY_BINARY64"]
def mk(nodes):
    ops = sorted({n["op"] for n in nodes}); from stage_a.composer.expression.opcodes import OPCODES
    caps = sorted({OPCODES[o].capability for o in ops}); return man(nodes, ops, caps, nodes[-1]["id"])
def both(m, xs):
    M = Manifest.from_dict(m); s = {"close": xs}
    try: e = evaluate(M, s)
    except Refusal as x: e = ("FAIL", x.code)
    try: r = it.reference_evaluate(parse(enc_bytes(M.data)), s)
    except it.RefEvalError: r = ("FAIL", None)
    return e, r
def agree(e, r): return (e[0] == "FAIL" and r[0] == "FAIL") if isinstance(e, tuple) or isinstance(r, tuple) and False else (isinstance(e, tuple) and isinstance(r, tuple)) or e == r

ROOT = lambda: mk([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": "gt", "args": ["o", "z"]}, {"id": "d", "op": "div", "args": ["o", "a"]},
                   {"id": "l", "op": "lag", "args": ["d"], "n": 1}, {"id": "s", "op": "select", "args": ["c", "l", "z"]}])
RM = lambda: mk([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": "gt", "args": ["o", "z"]}, {"id": "d", "op": "div", "args": ["o", "a"]},
                 {"id": "r", "op": "rolling_mean", "args": ["d"], "n": 2}, {"id": "s", "op": "select", "args": ["c", "r", "z"]}])
RM_PURE = lambda: mk([A, C("o", 1.0), {"id": "d", "op": "div", "args": ["o", "a"]}, {"id": "r", "op": "rolling_mean", "args": ["d"], "n": 2}])

class RootCases(unittest.TestCase):
    def test_lag_warmup_does_not_demand_index_it_does_not_read(self):
        self.assertEqual(both(ROOT(), [-1.0, 0.0]), ([None, -1.0], [None, -1.0]))
        self.assertEqual(both(ROOT(), [2.0, 4.0]), ([None, 0.5], [None, 0.5]))
        self.assertEqual(both(ROOT(), [0.0]), ([None], [None]))
    def test_rolling_warmup_does_not_demand_unread_index(self):
        self.assertEqual(both(RM(), [0.0]), ([None], [None]))
        self.assertEqual(both(RM(), [2.0, 4.0]), ([None, 0.375], [None, 0.375]))
    def test_select_free_program_keeps_eager_semantics_in_both_evaluators(self):
        # documented: without select every node is evaluated at every index (a failure anywhere fires) - identical in composer and reference
        e, r = both(RM_PURE(), [0.0]); self.assertEqual(e, ("FAIL", "DOMAIN_DIV_ZERO")); self.assertEqual(r[0], "FAIL")
    def test_taken_failure_through_lag_and_window_still_fires_in_both(self):
        e, r = both(ROOT(), [0.0, 1.0]); self.assertEqual(e, ("FAIL", "DOMAIN_DIV_ZERO")); self.assertEqual(r[0], "FAIL")
        e, r = both(RM(), [0.0, 1.0]); self.assertEqual(e, ("FAIL", "DOMAIN_DIV_ZERO")); self.assertEqual(r[0], "FAIL")
    def test_nested_select_lag_reduction(self):
        m = mk([A, C("z", 0.0), C("o", 1.0), {"id": "d", "op": "div", "args": ["o", "a"]}, {"id": "r", "op": "rolling_sum", "args": ["d"], "n": 2},
                {"id": "c", "op": "gt", "args": ["a", "z"]}, {"id": "s1", "op": "select", "args": ["c", "r", "z"]},
                {"id": "l", "op": "lag", "args": ["s1"], "n": 1}, {"id": "c2", "op": "ge", "args": ["a", "o"]}, {"id": "s2", "op": "select", "args": ["c2", "l", "s1"]}])
        for xs in ([1.0, 2.0, 4.0], [0.0, 2.0, 4.0], [2.0, 0.0, 4.0], [2.0, 4.0, 0.0], [-1.0, 0.0, 1.0]):
            e, r = both(m, xs); self.assertTrue(agree(e, r), (xs, e, r))
    def test_materializer_verifier_categories(self):
        for mkr in (ROOT, RM):
            store, M, rec, declared = good_world(mkr())
            res = run(real, store, rec, declared); self.assertEqual(res.status, PASS, failing_checks(res))

class Differential(unittest.TestCase):
    def test_seeded_random_typed_dags_agree(self):
        rnd = random.Random(46); n_fail = n_ok = 0
        for _ in range(600):
            nodes = [A, C("z", 0.0), C("o", 1.0)]; f, b = ["a", "z", "o"], []
            for i in range(rnd.randint(2, 7)):
                k = rnd.choice(["div", "add", "sub", "mul", "lag", "rs", "rm", "cmp", "sel", "neg"]); nid = "n%d" % i
                if k in ("div", "add", "sub", "mul"): nodes.append({"id": nid, "op": k, "args": [rnd.choice(f), rnd.choice(f)]}); f.append(nid)
                elif k == "neg": nodes.append({"id": nid, "op": "neg", "args": [rnd.choice(f)]}); f.append(nid)
                elif k == "lag": nodes.append({"id": nid, "op": "lag", "args": [rnd.choice(f)], "n": rnd.randint(1, 3)}); f.append(nid)
                elif k in ("rs", "rm"): nodes.append({"id": nid, "op": "rolling_sum" if k == "rs" else "rolling_mean", "args": [rnd.choice(f)], "n": rnd.randint(1, 3)}); f.append(nid)
                elif k == "cmp": nodes.append({"id": nid, "op": rnd.choice(["lt", "le", "gt", "ge", "eq_canonical"]), "args": [rnd.choice(f), rnd.choice(f)]}); b.append(nid)
                elif b: nodes.append({"id": nid, "op": "select", "args": [rnd.choice(b), rnd.choice(f), rnd.choice(f)]}); f.append(nid)
            # output = last float node; keep only nodes reachable (schema refuses unreachable): rebuild from output
            out = f[-1]; by = {n["id"]: n for n in nodes}; keep, st = set(), [out]
            while st:
                x = st.pop()
                if x in keep: continue
                keep.add(x); st.extend(by[x].get("args", []))
            if "a" not in keep: continue
            nodes = [n for n in nodes if n["id"] in keep]
            nodes.append(nodes.pop(next(i for i, n in enumerate(nodes) if n["id"] == out)))
            try: m = mk(nodes); Manifest.from_dict(m)
            except Refusal: continue
            xs = [rnd.choice([0.0, 1.0, -1.0, 2.0, 4.0, 0.5, None]) for _ in range(rnd.randint(1, 6))]
            e, r = both(m, xs)
            self.assertTrue(agree(e, r), (nodes, xs, e, r))
            n_fail += isinstance(e, tuple); n_ok += not isinstance(e, tuple)
        self.assertGreater(n_fail, 20); self.assertGreater(n_ok, 20)      # the corpus exercises both outcomes (else the check is vacuous)
if __name__ == "__main__": unittest.main()
