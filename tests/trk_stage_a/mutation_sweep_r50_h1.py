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
     (A, "if aug.gateway_rebind.request_id == ret.fw_request_id: raise", "if False: raise"), (A, "if old is not None and old != out: raise", "if False: raise"),
     (A, "check_ml_input_origin(fw_derived_predictive, aug)", "pass"), (A, "gateway=self._g))", "gateway=None))")]
bad = 0
for i, (f, a, b) in enumerate(M):
    p = ROOT / f; o = p.read_text()
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    p.write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: p.write_text(o)
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
