"""R48 mutation sweep for tracker_component/lifecycle.py: every mutant must make tests/trk_stage_a/test_r48_replica_lifecycle.py fail. Usage: python tests/trk_stage_a/mutation_sweep_r48.py"""
import pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; F = ROOT / "tracker_component" / "lifecycle.py"; T = "tests/trk_stage_a/test_r48_replica_lifecycle.py"
M = [("if not self._order_terminal(order_id) and self._order_grant_revoked", "if self._order_grant_revoked"),
     ("== ISSUER:\n            return True", "== ISSUER and False:\n            return True"),
     ('if c["state"] != "BOUND":\n                raise Refusal("CLAIM_NOT_BOUND", c["state"])\n            prev', 'if False:\n                raise Refusal("CLAIM_NOT_BOUND", c["state"])\n            prev'),
     ('raise Refusal("ATTEMPT_ALREADY_LIVE")', "pass"),
     ('if mine and correction_parent != mine[-1]["build_id"]', "if False"),
     ('raise Refusal("BUILD_ID_CONFLICT", build_id)', "pass"),
     ('raise Refusal("FINAL_DISPOSITION_EXISTS")               # a new', 'pass  # a new'),
     ('raise Refusal("REPORT_ID_REBOUND_TO_DIFFERENT_BYTES")', "pass"),
     ('raise Refusal("REPORT_HASH_REUSED")', "pass"),
     ('raise Refusal("PACKAGE_HASH_CHANGED")', "pass"),
     ('raise Refusal("SUCCESSOR_NEEDS_REVIEW_DECISION")', "pass"),
     ('raise Refusal("OLD_LINEAGE_NOT_TERMINAL", old_creation_id)', "pass"),
     ('raise Refusal("REPLACEMENT_NEEDS_NEW_ORDER", order_id)', "pass"),
     ('if st == "CONSUMED":', 'if False:'),
     ('if new_creation_id in self._p.request_claim or', 'if'),
     ('raise Refusal("GRANT_ROLE_CONFLICT", grant_id)', "pass"),
     ("if gate == DUPLICATE_OR_NEAR:\n            raise Refusal(\"DUPLICATE_OR_NEAR_REUSE_CANONICAL_IDENTITY\")", "if False:\n            pass"),
     ('raise Refusal("REVIEW_GENERATION_MISMATCH")', "pass"),
     ('self._need_grant(origin_grant)\n            a = self._p.attempts.get(build_id)\n            if a is None or a["state"] != "ADMITTED":\n                raise Refusal("ATTEMPT_NOT_ADMITTED", build_id)\n            self._verify_order(a["order_id"], None, head.seq)\n            if self._final', 'a = self._p.attempts.get(build_id)\n            if a is None or a["state"] != "ADMITTED":\n                raise Refusal("ATTEMPT_NOT_ADMITTED", build_id)\n            self._verify_order(a["order_id"], None, head.seq)\n            if self._final')]
orig = F.read_text(); bad = 0
try:
    for i, (a, b) in enumerate(M):
        if orig.count(a) < 1: print("MUTANT %d PATTERN NOT FOUND" % i); bad += 1; continue
        F.write_text(orig.replace(a, b, 1))
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True)
        k = r.returncode != 0; print("mutant %2d %s" % (i, "KILLED" if k else "SURVIVED")); bad += (not k)
finally:
    F.write_text(orig)
print("survivors/missing:", bad); sys.exit(1 if bad else 0)
