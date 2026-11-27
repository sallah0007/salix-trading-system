"""Mutation sweep: each mutant breaks one protection in a COPY of the tree; the Stage A suites must then FAIL.
A mutant that survives means a protection has no test that can fail for it."""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUITES = ["test_foundations.py", "test_expression.py", "test_verifier_independence.py", "test_pipeline.py"]

MUTANTS = [
 ("fencing disabled (epoch check)", "stage_a/coordination/object_store_journal.py",
  'if doc is None or doc["epoch"] != self._epoch:\n            raise StaleFence("writer', 'if doc is None:\n            raise StaleFence("writer'),
 ("compare-and-append disabled (expected head ignored)", "stage_a/coordination/object_store_journal.py",
  'if Head(doc["seq"], doc["hash"]) != expected_head:', 'if False:'),
 ("journal read skips record-hash recomputation", "stage_a/coordination/object_store_journal.py",
  'record_hash(r["seq"], r["prev_hash"], r["kind"], r["body_json"]) != h', 'False'),
 ("AS_KNOWN ignores asof_seq", "stage_a/currentness.py",
  'records = [r for r in records if r.seq <= asof_seq]', 'records = list(records)'),
 ("replay accepts cross-namespace record", "stage_a/replay.py",
  'if body["feature_key"] != "%s/%s" % (namespace, body["feature_version"]):', 'if False:'),
 ("read model serves stale data", "stage_a/storage/postgres_read_model.py",
  'if row is None or row != (h.seq, h.hash):', 'if False:'),
 ("unreachable nodes allowed", "stage_a/composer/expression/schema.py",
  '_req(reach == set(by_id), "UNREACHABLE_NODE"', '_req(True, "UNREACHABLE_NODE"'),
 ("declared inputs need not equal used inputs", "stage_a/composer/expression/schema.py",
  '_req(used_inputs == set(inputs), "DECLARED_INPUTS_NOT_EQUAL_USED")', '_req(True, "DECLARED_INPUTS_NOT_EQUAL_USED")'),
 ("lag reads negative index (look-ahead wraparound)", "stage_a/composer/expression/evaluator.py",
  'return get(src, t - n) if t - n >= 0 else None', 'return get(src, t - n)'),
 ("rolling window start guard removed", "stage_a/composer/expression/evaluator.py",
  'if t - n + 1 < 0:\n            return None', 'if False:\n            return None'),
 ("manifest hash domain changed", "stage_a/composer/expression/hashing.py",
  'MANIFEST_DOMAIN = b"SALIX_EXPR_MANIFEST_V1\\x00"', 'MANIFEST_DOMAIN = b"X\\x00"'),
 ("graph encoding leaks const values", "stage_a/composer/expression/canonical_encoding.py",
  'if k in ("id", "op", "args", "n")', 'if k in ("id", "op", "args", "n", "value")'),
 ("incomplete lookup no longer blocks", "stage_a/tracker/quant_intake_adapter.py",
  'elif gate != PROCEED:', 'elif False:'),
 ("TR-06: schema failure becomes NO_QUANT_FEATURE", "stage_a/tracker/quant_intake_adapter.py",
  'a.classification = FAILED_REQUESTED_BUILD      # TR-06: never silently baseline-only / NONE', 'a.classification = NO_QUANT_FEATURE'),
 ("pipeline ignores verifier verdict", "stage_a/tracker/pipeline.py",
  'if ver.status != "PASS":', 'if False:'),
 ("fence not checked before spending authority", "stage_a/tracker/pipeline.py",
  'if not j.epoch_is_current():          # check the fence BEFORE exercising one-shot authority', 'if False:'),
 ("publication skips verification scope/status", "stage_a/tracker/publication.py",
  '    verification.require_pass(SCOPE_MATERIALIZATION)\n    ns, ver', '    ns, ver'),
 ("publishable may repeat", "stage_a/coordination/transition_record.py",
  'PUBLISHABLE: {WITHDRAWN}', 'PUBLISHABLE: {WITHDRAWN, PUBLISHABLE}'),
 ("resolver ignores claim state/request", "tracker_component/claims.py",
  'if c["state"] != "BOUND" or c["request_id"] != request_id:', 'if False:'),
 ("verification result gains truthiness", "stage_a/tracker/verification/verification_result.py",
  'raise TypeError("VerificationResult has no truthiness; use require_pass(scope)")', 'return True'),
 ("materializer accepts poisoned artifact key", "stage_a/tracker/materialization/stateful_materializer.py",
  'if got is None or got[0] != art.manifest_bytes:', 'if False:'),
 ("replay budget not enforced", "stage_a/coordination/scheduler.py",
  'if total > self.max_total:', 'if False:'),
]

def run_mutant(label, path, old, new):
    tmp = tempfile.mkdtemp(prefix="mut_")
    try:
        for d in ("stage_a", "tracker_component", "tracker_identity"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "tests", "trk_stage_a"), os.path.join(tmp, "tests", "trk_stage_a"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        target = os.path.join(tmp, path)
        with open(target) as fh:
            src = fh.read()
        if src.count(old) != 1:
            return "MUTATION_NOT_APPLICABLE(count=%d)" % src.count(old)
        with open(target, "w") as fh:
            fh.write(src.replace(old, new))
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests/trk_stage_a", "-t", "."] ,
                           cwd=tmp, capture_output=True, text=True, timeout=300)
        return "KILLED" if r.returncode != 0 else "SURVIVED"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main():
    results = []
    for label, path, old, new in MUTANTS:
        if old is None:
            continue
        results.append((label, run_mutant(label, path, old, new)))
        print("%-60s %s" % results[-1])
    bad = [r for r in results if r[1] != "KILLED"]
    print("\n%d mutants, %d killed, %d not killed" % (len(results), len(results) - len(bad), len(bad)))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
