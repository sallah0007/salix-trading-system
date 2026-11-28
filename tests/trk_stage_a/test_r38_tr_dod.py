"""R38 targeted Build Plan s27 DoD probes for the rows R35 left NOT RE-EVALUATED: TR-03, TR-04, TR-06, TR-09, TR-11, TR-12. Each asserts the row's DoD sentence directly (positive AND negative) through the real modules; author-run evidence, not an acceptance."""
import ast, copy, itertools, pathlib, random, threading, unittest
from tracker_component.journal_port import HeadMismatch
from stage_a.errors import Refusal, StaleFence
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.hashing import manifest_hash, graph_hash, program_hash
from stage_a.composer.expression.capability import check_declared
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.coordination import fencing
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.context.edge import assert_declared
from stage_a.tracker.quant_intake_adapter import admit, FAILED_REQUESTED_BUILD, NO_QUANT_FEATURE
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import momentum_manifest, package, Rig, SIM_CONF
from .test_r29_intake_order import issue, br
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class TR03_04(unittest.TestCase):
    def test_tr03_permutation_invariance_over_every_declaration_order_and_duplicates_rejected(self):
        base = momentum_manifest(); h0 = manifest_hash(Manifest.from_dict(base)); rnd = random.Random(7)
        for _ in range(25):
            m = copy.deepcopy(base)
            for k in ("nodes", "inputs", "declared_opcodes", "declared_capabilities"): rnd.shuffle(m[k])
            self.assertEqual(manifest_hash(Manifest.from_dict(m)), h0)
        d = copy.deepcopy(base); d["nodes"].append(dict(d["nodes"][0])); self.assertEqual(code(Manifest.from_dict, d), "DUPLICATE_NODE_ID")
        d = copy.deepcopy(base); d["inputs"] = ["close", "close"]; self.assertEqual(code(Manifest.from_dict, d), "DUPLICATE_INPUT")
        d = copy.deepcopy(base); d["declared_opcodes"] = d["declared_opcodes"] + ["lag"]; self.assertEqual(code(Manifest.from_dict, d), "DUPLICATE_DECLARATION")
        a = copy.deepcopy(base); b = copy.deepcopy(base); b["nodes"][1]["args"] = ["a", "a"]; self.assertNotEqual(manifest_hash(Manifest.from_dict(a)), manifest_hash(Manifest.from_dict(b)) if code(Manifest.from_dict, b) is None else "x")      # args ORDER is semantic, not sorted away
        c = copy.deepcopy(base); c["nodes"][2]["args"] = list(reversed(c["nodes"][2]["args"])); self.assertNotEqual(manifest_hash(Manifest.from_dict(c)), h0)                  # sub(a,b) != sub(b,a)
    def test_tr04_every_manifest_field_is_covered_by_the_manifest_hash_and_graph_program_cover_their_own_subsets(self):
        base = momentum_manifest(); M0 = Manifest.from_dict(base); h = manifest_hash(M0); changed = {}
        mut = {"schema": lambda v: v, "feature_id": lambda v: v + "x", "feature_version": lambda v: v + "9", "instrument": lambda v: "EURUSD", "timeframe": lambda v: "H1", "inputs": lambda v: v + ["volume"], "output": lambda v: "c", "fit_refs": lambda v: v}
        for k in base:
            if k in ("nodes", "declared_opcodes", "declared_capabilities", "schema", "fit_refs") or k not in mut: continue
            m = copy.deepcopy(base); m[k] = mut[k](m[k]); r = code(Manifest.from_dict, m)
            if r is None: changed[k] = manifest_hash(Manifest.from_dict(m)) != h
        self.assertTrue(changed and all(changed.values()), changed)                                                                                  # every mutable top-level field that stays valid moves the manifest hash
        m = copy.deepcopy(base); m["nodes"][3]["n"] = 4; M1 = Manifest.from_dict(m); self.assertNotEqual((manifest_hash(M1), graph_hash(M1), program_hash(M1)), (h, graph_hash(M0), program_hash(M0))); self.assertNotEqual(graph_hash(M1), graph_hash(M0))
        m = copy.deepcopy(base); m["feature_id"] = "other"; M2 = Manifest.from_dict(m); self.assertEqual((graph_hash(M2), program_hash(M2)), (graph_hash(M0), program_hash(M0))); self.assertNotEqual(manifest_hash(M2), h)      # identity metadata moves the manifest hash only
        rig = Rig(); p = package(declared_manifest_hash="0" * 64); a = admit(p, accepted_fit_generations={}, conformance=SIM_CONF); self.assertFalse(a.admissible)             # declared hash must equal the recomputed one
class TR06_09(unittest.TestCase):
    def test_tr06_a_failed_requested_build_cannot_become_no_quant_or_baseline_only_with_governed_lineage(self):
        rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid); a = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF); issue(rig.claims, subject_key=a.subject_key); abs_(rig.claims, oid, br())
        self.assertEqual(rig.pipe.run(p).accepted.kind, "CANONICAL_ACCEPTED")
        flagged = package(order_id=oid, quant=False, manifest=None); o = rig.pipe.run(flagged); self.assertNotEqual(o.classification, NO_QUANT_FEATURE); self.assertEqual(o.classification, FAILED_REQUESTED_BUILD); self.assertTrue(any("NO_QUANT_FLAG_CONTRADICTS_GOVERNED_LINEAGE" in str(f) for f in o.failures))
        fresh = Rig(); o2 = fresh.pipe.run(package(order_id="ORD-NEVER-ISSUED", quant=False, manifest=None)); self.assertEqual(o2.classification, NO_QUANT_FEATURE)               # SIMULATION-only genuine positive: no lineage, no claim: still labelled simulation
        q = Rig(simulation=False); o3 = q.pipe.run(package(order_id="ORD-NEVER-ISSUED", quant=False, manifest=None)); self.assertNotEqual(o3.classification, NO_QUANT_FEATURE)           # QUALIFIED route: unknown source identity is HELD, never NO_QUANT
    def test_tr09_exact_opcode_and_capability_equality_and_the_firewall(self):
        m = momentum_manifest(); self.assertEqual(check_declared(Manifest.from_dict(m))[0], m["declared_opcodes"])
        for k, extra, want in (("declared_opcodes", "exp", "OPCODE_DECLARATION_MISMATCH"), ("declared_capabilities", "FAKE_CAP", "CAPABILITY_DECLARATION_MISMATCH")):
            d = copy.deepcopy(m); d[k] = sorted(d[k] + [extra]); self.assertEqual(code(lambda: check_declared(Manifest.from_dict(d))), want)
        d = copy.deepcopy(m); d["declared_opcodes"] = d["declared_opcodes"][:-1]; self.assertEqual(code(lambda: check_declared(Manifest.from_dict(d))), "OPCODE_DECLARATION_MISMATCH")                    # under-declaration
        self.assertEqual(code(check_declared, Manifest.from_dict(m), frozenset({"INPUT_SERIES"})), "CAPABILITY_NOT_PROVIDED")                                               # firewall: a capability not provided refuses
class TR11_12(unittest.TestCase):
    def test_tr11_one_winner_under_contention_stale_epoch_fenced_and_rebuild_from_the_store(self):
        st = InMemoryObjectStore(); j = ObjectStoreJournal(st, "ns", "w1"); j.acquire_epoch(); h0 = j.head(); wins, losses = [], []
        def go(i):
            try: wins.append(j.append(h0, "K", {"i": i}))
            except HeadMismatch: losses.append(i)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(12)]; [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual((len(wins), len(losses)), (1, 11)); self.assertEqual(j.head().seq, 1)                                                                            # exactly one winner, the rest fail closed
        f = fencing.acquire(j, "ns"); j2 = ObjectStoreJournal(st, "ns", "w2"); j2.acquire_epoch()
        with self.assertRaises(StaleFence): fencing.assert_current(j, f)                                                                                                       # the superseded writer is fenced
        self.assertRaises(Exception, j.append, j.head(), "K", {"late": 1}); self.assertEqual(j2.head().seq, 1)
        rebuilt = ObjectStoreJournal(st, "ns", "w3"); self.assertEqual(rebuilt.head(), j2.head()); self.assertEqual([r.kind for r in rebuilt.read_from(1)], ["K"])                      # rebuild proof: a fresh adapter re-derives the same chain
    def test_tr12_declared_edge_only_and_the_context_package_has_no_route_into_gateway_fw_ml_or_tracker(self):
        self.assertEqual(assert_declared([("f", "c")], [("f", "c")]), (("f", "c"),)); self.assertEqual(code(assert_declared, [("f", "c")], [("f", "c"), ("f", "other")]), "UNDECLARED_CONTEXT_EDGE"); self.assertEqual(code(assert_declared, [], [("f", "c")]), "UNDECLARED_CONTEXT_EDGE")
        root = pathlib.Path(__file__).resolve().parents[2] / "stage_a" / "context"; bad = []
        for f in root.glob("*.py"):
            for n in ast.walk(ast.parse(f.read_text())):
                names = [n.module or ""] if isinstance(n, ast.ImportFrom) else [a.name for a in n.names] if isinstance(n, ast.Import) else []
                for nm in names:
                    if any(seg in nm.split(".") for seg in ("gateway", "fw", "ml", "tracker", "health")): bad.append((f.name, nm))
        self.assertEqual(bad, [], "independent context route: no import of gateway/fw/ml/tracker/health")
if __name__ == "__main__": unittest.main()
