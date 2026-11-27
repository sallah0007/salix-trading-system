"""R34 mutants for code added in R34 (ML writer/finalizer exact receipts, Health subject coverage, FW association, producer admission, consumption claim/era/revocation). Author-run; a survivor is a finding. Not run by CI."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
WF = "stage_a/ml/writer_finalizer.py"; SC = "stage_a/health/subject_coverage.py"; AS = "stage_a/fw/association.py"; PA = "stage_a/binding/producer_admission.py"; CC = "stage_a/ml/consumption_claim.py"
M = [
 (WF, "e not in {a[4] for a in f} or", "e.authority not in {a[1] for a in f} or"),
 (WF, 'if prior[0][1] != caller: raise', "if False: raise"),
 (WF, 'if prior[0][3] != manifest.manifest_hash: raise', "if False: raise"),
 (WF, "if not prior: self._audit.append", "if True: self._audit.append"),
 (WF, 'or not any(a[0] == "WRITE" and a[2] == manifest_id for a in self._audit)', ""),
 (WF, "or w[0][3] != m.manifest_hash", ""),
 (SC, " or gateway_snapshot.version != version", ""),
 (SC, " or gateway_snapshot.subject != subject", ""),
 (SC, " or not core.snapshot_current_at_use(gateway_snapshot, now)", ""),
 (SC, 'agg = "NOT_HEALTHY" if "NOT_HEALTHY" in sts else ("HEALTHY" if all(s == "HEALTHY" for s in sts) else "UNKNOWN")', 'agg = "HEALTHY" if all(s == "HEALTHY" for s in sts) else "UNKNOWN"  #'),
 (SC, "all(src != NO_SOURCE for _, _, src in local)", "True"),
 (AS, 'if self._store.identity_of(FW, request_id) != identity: raise', "if False: raise"),
 (AS, 'getattr(identity, "consumer_id", None) != FW', "False"),
 (AS, "if old is not None:", "if False:"),
 (AS, 'if return_class == "LINEAGE" and not _s(lineage_ref)', "if False"),
 (AS, 'if payload is not None: raise', "if False: raise"),
 (PA, "diff = [f for f in SEVEN_FIELDS if rec[f] != a[f]]", 'diff = [f for f in SEVEN_FIELDS if f != "content_hash" and rec[f] != a[f]]'),
 (PA, "if a is None:", "if False:"),
 (PA, "    try: check_shape(a)", "    try: pass"),
 (CC, "if c.family_ledger.available_asof > c.claim_ts", "if False"),
 (CC, "if old != c:", "if False:"),
 (CC, "if manifest_feed_era_id != c.feed_era_id", "if False"),
 (CC, "if r is None: unknown.add(mid)", "if r is None: pass"),
 (CC, "if mid in path:", "if False:"),
 (CC, "depth == 1 else DERIVED_FROM_REVOKED", "depth == 1 else CONTRIBUTOR_LATER_REVOKED"),
]
T = ["tests/trk_stage_a/test_r34_ml_writer.py", "tests/trk_stage_a/test_r34_health_subjects.py", "tests/trk_stage_a/test_r34_fw_association.py", "tests/trk_stage_a/test_r34_producer_admission.py", "tests/trk_stage_a/test_r34_consumption_claim.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:70].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
