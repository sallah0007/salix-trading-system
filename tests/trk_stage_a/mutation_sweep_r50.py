"""R50 scoped mutation sweep: every mutant of the new race/validation/detach code must make the r48+r50 lifecycle tests fail. Usage: python tests/trk_stage_a/mutation_sweep_r50.py"""
import pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; TD = ROOT / "tracker_component"
T = ["tests/trk_stage_a/test_r48_replica_lifecycle.py", "tests/trk_stage_a/test_r50_commit_races.py"]
M = [("claims.py", "if head.seq == self._p.seq and head.hash == self._p.hash:", "if True:"),
     ("claims.py", "if head.seq == self._p.seq and head.hash == self._p.hash:", "if head.seq == self._p.seq:"),
     ("claims.py", 'raise Refusal("FENCE_RACE_EXHAUSTED", "projection never matched HEAD")', "return head"),
     ("claims.py", "return self._verify_order(order_id, None, self._basis().seq)", "self._p.sync(self._j); return self._verify_order(order_id, None, self._j.head().seq)"),
     ("claims.py", "build(self._basis())", "self._p.sync(self._j); build(self._j.head())"),
     ("claims.py", "head = self._basis()\n            cid = self._p.subject_claim", "self._p.sync(self._j); head = self._j.head()\n            cid = self._p.subject_claim"),
     ("lifecycle.py", "if oid in self._p.revoked or self._order_terminal(oid) or not self._order_grant_revoked(oid, raw[\"issued_by\"]):\n                    return None, None", "if False:\n                    return None, None"),
     ("lifecycle.py", "if c[\"state\"] != \"BOUND\" or self._order_terminal(oid) or not", "if self._order_terminal(oid) or not"),
     ("lifecycle.py", "if c[\"state\"] != \"BOUND\" or self._order_terminal(oid) or not self._order_grant_revoked(oid, self._p.orders[oid][\"issued_by\"]):\n                        return None, None", "if c[\"state\"] != \"BOUND\":\n                        return None, None"),
     ("lifecycle.py", "if self._p.lineage_parent.get(new_creation_id) == old_creation_id:\n                return None, None", "if False:\n                return None, None"),
     ("lifecycle.py", 'if not isinstance(build_id, str) or not build_id:\n            raise Refusal("BUILD_ID_REQUIRED")', "pass"),
     ("lifecycle.py", 'if prev.get("deadline_ref") != deadline_ref:\n                raise Refusal("BUILD_ID_CONFLICT", build_id)', "pass"),
     ("lifecycle.py", "body[\"deadline_ref\"] = copy.deepcopy(deadline_ref)", "body[\"deadline_ref\"] = deadline_ref"),
     ("lifecycle.py", "deadline_ref = copy.deepcopy(deadline_ref)  ", "deadline_ref = deadline_ref  "),
     ("lifecycle.py", "return copy.deepcopy(self._p.attempts[build_id])\n            try", "return dict(self._p.attempts[build_id])\n            try"),
     ("lifecycle.py", "self._p.apply(rec); return copy.deepcopy(self._p.attempts[build_id])", "self._p.apply(rec); return dict(self._p.attempts[build_id])"),
     ("lifecycle.py", "return None if a is None else copy.deepcopy(a)", "return None if a is None else dict(a)"),
     ("lifecycle.py", "head = self._basis()\n            kind, body = self._admit_build(binding, head, deadline_ref)", "head = self._j.head()\n            kind, body = self._admit_build(binding, head, deadline_ref)")]
bad = 0
for i, (f, a, b) in enumerate(M):
    p = TD / f; o = p.read_text()
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    p.write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", *T], cwd=ROOT, capture_output=True, text=True, env=dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: p.write_text(o)
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
