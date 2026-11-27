"""R36 mutants for code added/changed in R36 (durable commit point, transactional recover, request-reservation retention, source-value finite check, window namespaces/determinism/cross-instrument, ops E-04..E-10, ML dataset authority, producer-binding route, FW outcome desk). Author-run; a survivor is a finding or a named equivalent. Also kills three survivors that the R33/R34 sweeps report on UNCHANGED main f1a597a (reproduced on a pristine worktree) and names one equivalent there: `fw/descriptor_binding` `Descriptor(vals, held, False)` - `held` always contains SEGMENT_REF/KNOWABLE_AT/ADMISSIBILITY_STATE (mapping unbound), so `not held` is always False until a source supplies the mapping."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
DS = "stage_a/gateway/durable_final_store.py"; GW = "stage_a/gateway/contracts.py"; SI = "stage_a/tracker/source_inputs.py"; IT = "stage_a/tracker/verification/independent_traversal.py"; KV = "stage_a/ops/keys_v1.py"; WK = "stage_a/ops/workers.py"; RM = "stage_a/ops/read_model.py"; RH = "stage_a/ops/rehearsal.py"
DA = "stage_a/ml/dataset_authority.py"; QI = "stage_a/tracker/quant_intake_adapter.py"; OD = "stage_a/fw/outcome_desk.py"; CI = "stage_a/gateway/cross_instrument.py"; HS = "stage_a/health/adapters.py"
M = [
 (DS, "            self._by_identity, self._pins, self._facts, self._req_ids = by, pins, facts, reqs\n            self._held.clear()", "            self._held.clear()\n            self._by_identity, self._pins, self._facts, self._req_ids = by, pins, facts, reqs"),   # NAMED EQUIVALENT: both statements run under one lock with no exception possible between them (a plain dict-assignment tuple), so the order is unobservable
 (DS, 'if got is None: raise IntegrityFailure("listed identity record unreadable")', "pass"),
 (DS, 'if reqs.setdefault(key, ident) != ident: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 (DS, "                raise (e.__cause__ or e)               # the identity IS committed", "                self._req_ids.pop((identity.consumer_id, request_id), None); raise (e.__cause__ or e)               # the identity IS committed"),
 (DS, "if isinstance(rid, str) and rid:", "if False:"),
 (SI, 'if not all(_bits_finite(x) for x in v): out[n] = "SERIES_NONFINITE"; continue', "pass"),
 (SI, "(((int(x, 16) >> 52) & 0x7FF) == 0x7FF or int(x, 16) == 1 << 63)", "False"),
 (SI, ">> 52) & 0x7FF) != 0x7FF", ">> 52) & 0x7FF) != 0x7FE"),
 (IT, 'col[nid] = [_fin(x) for x in series[nd["name"]]]', 'col[nid] = [_z(x) for x in series[nd["name"]]]'),
 (KV, 'def head_cas_allowed(current_epoch: int, writer_epoch: int, current_seq: int, new_seq: int) -> bool:\n    """Mutable HEAD may advance only for a writer holding the CURRENT epoch and only by exactly +1 within that epoch; a stale epoch can create no accepted write."""\n    return writer_epoch == current_epoch and new_seq == current_seq + 1', 'def head_cas_allowed(current_epoch: int, writer_epoch: int, current_seq: int, new_seq: int) -> bool:\n    return new_seq == current_seq + 1'),
 (KV, "return \"stage-a/v1/fits/%s/%s/%s/%s/%s.bin\" % (_i(fid), _i(ver), _i(instrument_id), _i(timeframe), _i(gen_or_hash))", "return \"stage-a/v1/fits/%s/%s/%s/%s.bin\" % (_i(fid), _i(ver), _i(timeframe), _i(gen_or_hash))"),
 (WK, "if pr != WORKER_PRINCIPAL[w]: raise Refusal(w, code=\"WORKER_PRINCIPAL_MISMATCH\")", "pass"),
 (WK, 'if exp <= now: raise Refusal(ident, code="BREAK_GLASS_EXPIRED")', "pass"),
 (WK, 'if cap in ("accept", "publish_feature"): raise', "if False: raise"),
 (RM, "if old is not None and old != row and", "if False and"),
 (RM, 'self._built_from_head != accepted_head_hash: raise', 'False: raise'),
 (RH, "if i >= len(ROLLBACK) or action != ROLLBACK[i]: raise", "if False: raise"),
 (DA, 'if gateway.outcome(outcome.request_id, "ML") is not outcome: raise', "if False: raise"),
 (DA, "if reach(dataset_id, set()): raise", "if False: raise"),
 (DA, 'if self._d.is_revoked(claim.manifest_id, claim.claim_ts): raise', "if False: raise"),
 (DA, 'if old != entry: raise Refusal(dataset_id, code="UNION_IMMUTABLE")', "if False: raise Refusal(dataset_id, code=\"UNION_IMMUTABLE\")"),
 (QI, 'if pkg.producer_binding is None: a.failed.append', "if False: a.failed.append"),
 (QI, 'pkg.producer_binding.get("interface_id") != iface', "False"),
 (QI, "if d.status != PA.ADMITTED_AGAINST_SUPPLIED_AUTHORITY: a.failed.append", "if False: a.failed.append"),
 (DS, 'if got is None or not (equal(got[0]) if equal else got[0] == rec): raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 ("stage_a/tracker/reverification.py", 'if (body["feature_key"], body["feature_version"]) != (feature_key.key(), feature_key.feature_version): raise', "if False: raise"),
 ("stage_a/ml/six_joins.py", 'if isinstance(j, dict) and ("ML_LOCAL_STATE" in j or "EVIDENCE_REFS" in j): add', "if False: add"),
 ("stage_a/ml/writer_finalizer.py", " or w[0][3] != m.manifest_hash", ""),
 (OD, "if old[0] != pkg: raise", "if False: raise"),
 (OD, "if not isinstance(issued, Binding): raise", "if False: raise"),
 (OD, "delivered: bool = False", "delivered: bool = True"),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r36_recovery_holds.py", "test_r36_commit_point.py", "test_r36_source_values.py", "test_r36_ops.py", "test_r36_dataset_authority.py", "test_r36_producer_route.py", "test_r36_outcome_desk.py", "test_r35_durable_final_store.py", "test_r36_survivor_kills.py")]
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
