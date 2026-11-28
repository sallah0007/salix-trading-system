"""R44 mutants (snapshot_carrier, final-resolution E05 source on the separated path, plane identity). One at a time, file restored; NOT APPLICABLE or SURVIVED fails the run. Do not edit sources while it runs."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
SC="stage_a/tracker/snapshot_carrier.py"; ES="stage_a/storage/e05_sources.py"; TC="stage_a/core/tracker_core.py"; RS="stage_a/tracker/registry_semantics.py"
M = [
 (SC, 'if not callable(watermark_source): raise Refusal("watermark_source", code=WATERMARK_HELD)', 'pass'),
 (SC, 'if type(w) is not int or w < 0: raise Refusal(tf, code="SNAPSHOT_WATERMARK_SOURCE_RETURNED_NON_WATERMARK")', 'pass'),
 (SC, 'if type(w) is not int or w < 0:', 'if type(w) is not int:'),
 (SC, 'set(held_inputs) == set(HELD_INPUTS) and all(isinstance(v, str) and v for v in held_inputs.values())', 'True'),
 (SC, 'and all(isinstance(v, str) and v for v in held_inputs.values())', ''),
 (SC, 'if out["state"] != "RESOLVED": return', 'if False: return'),
 (SC, 'if timeframe not in ents: raise Refusal(timeframe, code="SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS")', 'pass'),
 (SC, 'canonical_bar_or_event_identity=ents[timeframe]["parent_id"]', 'canonical_bar_or_event_identity="x"'),
 (SC, 'timeframe_watermarks=tuple(sorted((tf, e["watermark"]) for tf, e in ents.items()))', 'timeframe_watermarks=tuple(sorted((tf, 0) for tf, e in ents.items()))'),
 (ES, 'if D._ident_key(ident) != k: raise Refusal(k, code="E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")', 'pass'),
 (ES, 'else: raise Refusal(k, code="E05_SOURCE_OUTCOME_TYPE_UNMAPPED")', 'else: continue'),
 (TC, 'if plane is not None and plane not in self.PLANES: raise Refusal(str(plane), code="UNKNOWN_PLANE")', 'pass'),
 (TC, 'if b.get("plane") != self._plane: raise IntegrityFailure(', 'if False: raise IntegrityFailure('),
]
# NAMED EQUIVALENTS (defence in depth; the same refusal is raised one layer down): (1) `len(vint) != 1`: Core returns UNRESOLVED_HELD for a non-single-vintage seal first; (2) `len(v) != 1` over recorded facts: snapshot_binding refuses the same SNAPSHOT_FIELD_DISAGREES_WITH_RECORDED_OBSERVATION_FACTS; (3) empty parents_by_tf: Core raises the same SNAPSHOT_STREAMS_INVALID.
T = [f"tests/trk_stage_a/{f}" for f in ("test_r44_snapshot_carrier.py", "test_r44_e05_rebuild_separated.py", "test_r44_d14_boundary.py", "test_r38_relationship_snapshot.py", "test_r42_e05_owning_sources.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=300, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:70]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70], flush=True); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
