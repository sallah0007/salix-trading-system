"""R54 scoped mutation sweep for tests/trk_stage_a/test_r54_shared_rebuild.py (each mutant must be KILLED by that file alone)."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r54_shared_rebuild.py"
D, E, C, CO = "stage_a/gateway/durable_final_store.py", "stage_a/storage/e05_sources.py", "stage_a/core/tracker_core.py", "stage_a/tracker/composition.py"
M = [(E, "ref_hash=hashlib.sha256(b).hexdigest(), data_vintage_mode=vintage_mode); yield table, r", "ref_hash=hashlib.sha256(b[:-1]).hexdigest(), data_vintage_mode=vintage_mode); yield table, r"),
     (E, "if D._ident_key(ident) != k: raise", "if False: raise"),
     (C, 'if plane is not None and plane not in self.PLANES: raise Refusal(str(plane), code="UNKNOWN_PLANE")', "pass"),
     (E, "l = _listing(); return (len(l), hashlib.sha256(\"|\".join(\"%s:%d\" % (k, e) for k, e, _ in l).encode()).hexdigest())\n    def rows():\n        for k, _, b in _listing():\n            d = json.loads(b)", "l = _listing(); return (0, \"x\")\n    def rows():\n        for k, _, b in _listing():\n            d = json.loads(b)")]
M += [(CO, 'if self.gateway is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")\n        d = getattr(self, "_desk", None)', 'd = getattr(self, "_desk", None)'), (CO, 'd = getattr(self, "_desk", None)', "d = None")]
M += [(CO, 'a = getattr(self, "_fwa", None)', "a = None"), (CO, 'if self.gateway is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")\n        a = getattr(self, "_fwa", None)', 'a = getattr(self, "_fwa", None)')]
bad = 0
for i, (f, a, b) in enumerate(M):
    p = ROOT / f; o = p.read_text()
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    p.write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: p.write_text(o)
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
