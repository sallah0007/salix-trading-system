"""Mutants for R11 intake request wiring and BOTH enforcement. Run: python3 -B tests/trk_stage_a/mutation_sweep_r11b.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
Q = "stage_a/tracker/quant_intake_adapter.py"; G = "stage_a/gateway/v038.py"
M = [(Q, "    if pkg.request_record is None:\n        fail(", "    if False:\n        fail("),
     (Q, 'if check_request_record(pkg.request_record, "ORDER") == "REVIEW_REQUIRED":', "if False:"),
     (Q, "        except Refusal as e:\n            fail(\"REQUEST_RECORD\", e.code)", "        except Refusal as e:\n            pass"),
     (Q, 'if self.request_record is not None: d["request_record"] = self.request_record', "pass"),
     (Q, '"CONSTRUCTION_AUTHORITY", "REQUEST_RECORD"]', '"CONSTRUCTION_AUTHORITY"]'),
     (G, '        if fw[f] == ml[f]:', "        if False:"),
     (G, '        if rec["PACKAGE_CLASS"] != _LANE_PACKAGE_CLASS[lane]:', "        if False:"),
     (G, '        if rec["TARGET_CONSUMER"] not in (lane, "BOTH"):', "        if False:"),
     (G, '    if fw["REQUEST_ID"] != ml["REQUEST_ID"]:', "    if False:"),
     (G, "    check_h1(ml, consumer_is_ml=True)", "    check_h1(ml, consumer_is_ml=False)"),
     (G, "    check_h1(fw, consumer_is_ml=False)\n", "    pass\n"),
     (G, "if fw_identity.consumer_id == ml_identity.consumer_id or fw_identity == ml_identity:", "if fw_identity == ml_identity:"),
     (G, "        except Refusal as e:\n            out[lane] = (\"REFUSED\", e.code)", "        except Refusal as e:\n            raise"),
     (G, '"%s#%s" % (request_id, lane)', "request_id")]
T = ["tests/trk_stage_a/test_r11_intake_request.py", "tests/trk_stage_a/test_r11_both.py"]
def run(): return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70]); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
