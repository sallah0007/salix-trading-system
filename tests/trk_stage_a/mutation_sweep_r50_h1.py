"""R50 scoped mutation sweep: h1_record.py, outcome_desk.register_h1, augmented_desk.py."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_h1_augmented.py"
H, D, A = "stage_a/gateway/h1_record.py", "stage_a/fw/outcome_desk.py", "stage_a/ml/augmented_desk.py"
M = [(H, "check_h1(d, decision_window)", "pass"),
     (H, 'if self._f.get("MANIFEST_OR_DATASET_BINDING_ID") in (None, ""): raise', "if False: raise"), (H, "check_binding_matches_identity(self.thaw(), identity)", "pass"),
     (H, "def __setattr__(self, k, v): raise Refusal(k, code=\"H1_RECORD_IMMUTABLE\")", "def __setattr__(self, k, v): object.__setattr__(self, k, v)"),
     (H, "if isinstance(x, (list, tuple)): return tuple(_freeze(v) for v in x)", "if isinstance(x, (list, tuple)): return x"),
     (D, 'if not isinstance(h1, TypedH1): raise', "if False: raise"), (D, 'if h1.fields["CONSUMER_ID"] != "FW": raise', "if False: raise"),
     (A, 'if "LINEAGE" not in ret.classes: raise', "if False: raise"), (A, 'if fw is None or fw.kind != "FW": raise', "if False: raise"),
     (A, "if old != ret: raise", "if False: raise"), (A, "if self._lin.get(ret.lineage_ref, ret.return_id) != ret.return_id: raise", "if False: raise"),
     (A, 'if getattr(m, "derived_from", None) != ret.fw_manifest_id: raise', "if False: raise"), (A, "or aug.fw_lineage_ref != ret.lineage_ref: raise", "or False: raise"),
     (A, "if aug.gateway_rebind is self._g.outcome(ret.fw_request_id, \"FW\"): raise", "if False: raise"), (A, "if dataclasses.replace(old, association=\"HELD\", consumer_binding_id=None, manifest_or_dataset_binding_id=None) != out: raise", "if False: raise"),
     (A, "check_ml_input_origin(fw_derived_predictive, aug)", "pass"), (A, "gateway=self._g))", "gateway=None))"),
     # R51
     (A, 'if self._od is None: raise', "if False: raise"), (A, "if not isinstance(self._od.return_for(ret.fw_request_id), OutcomeReturn): raise", "if False: raise"),
     (A, 'if not isinstance(h1, TypedH1): raise Refusal(type(h1).__name__, code="H1_RECORD_NOT_TYPED")', "pass"), (A, 'if f["CONSUMER_ID"] != "ML" or not h1.is_ml: raise', "if False: raise"),
     (A, 'if f["REQUEST_ID"] != cur.rebind_request_id: raise', "if False: raise"), (A, 'or fs.identity_of("ML", cur.rebind_request_id) != identity: raise', "or False: raise"),
     (A, 'getattr(identity, "consumer_id", None) != "ML" or fs.identity_of', 'False or fs.identity_of'), (A, "rec = h1.correlation(identity)", "rec = None"),
     (A, "!= (rec.consumer_binding_id, rec.manifest_or_dataset_binding_id): raise", "!= (cur.consumer_binding_id, cur.manifest_or_dataset_binding_id): raise"),
     (A, "            return old  ", "            return out  ")]
EQUIV = ('False or fs.identity_of',)
bad = 0
for i, (f, a, b) in enumerate(M):
    p = ROOT / f; o = p.read_text()
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    p.write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: p.write_text(o)
    eq = b in EQUIV
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else ("EQUIVALENT (reasoned: final-store identity_of(ML, req) == identity already implies identity.consumer_id == ML)" if eq else "SURVIVED"))); bad += (r.returncode == 0 and not eq)
sys.exit(1 if bad else 0)
