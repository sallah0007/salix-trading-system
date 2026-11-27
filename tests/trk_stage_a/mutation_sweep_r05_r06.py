"""Reproducible controls for the R05/R06 manually-run mutants (previously shell-only). Each mutant must make the named tests FAIL.
Run: python3 -B tests/trk_stage_a/mutation_sweep_r05_r06.py   (exit 0 = all killed). Restores every file in a finally block."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
T = ["tests/trk_stage_a/test_r05_consolidated.py", "tests/trk_stage_a/test_v038_conformance.py", "tests/trk_stage_a/test_composer_s27_coverage.py"]
M = [  # (file rel to repo root, old, new)
 ("stage_a/gateway/v038.py", "if available_asof >= fence:", "if available_asof > fence:"),                      # R05 D14 equality
 ("stage_a/gateway/v038.py", "if out is None:", "if False:"),                                                    # R05 None guard
 ("stage_a/gateway/v038.py", "            self._req_ids[request_id] = identity            # reserve BEFORE evaluating: nested calls cannot rebind it\n", ""),  # R06 reservation removed (request bound only after evaluate)
 ("stage_a/gateway/v038.py", "                if reserved_here:", "                if False:"),                                        # R06 release-on-failure disabled
 ("stage_a/gateway/v038.py", "            if bound is not None and bound != identity:", "            if False:"),                                        # request-id rebind check removed
 ("stage_a/tracker/quant_intake_adapter.py", "    creation_request_id: Optional[str] = None", "    creation_request_id: Optional[str] = None\n    claim_id: Optional[str] = None"),  # s27 map must be revisited
]
def run():
    return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *T], cwd=ROOT, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
def main():
    assert run() == 0, "baseline must pass"
    bad = []
    for rel, old, new in M:
        p = ROOT / rel; src = p.read_text()
        if src.count(old) != 1:
            print("NOT APPLICABLE (count=%d): %s :: %s" % (src.count(old), rel, old.strip()[:60])); bad.append(rel); continue
        try:
            p.write_text(src.replace(old, new)); killed = run() != 0
        finally:
            p.write_text(src)
        print(("killed  " if killed else "SURVIVED"), rel, "::", old.strip()[:70])
        if not killed: bad.append(rel)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad)))
    assert run() == 0
    return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
