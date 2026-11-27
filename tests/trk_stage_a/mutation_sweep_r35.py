"""R35 mutants for code added in R35 (legacy replay/maintenance hold, final-outcome detach, window resolver + pins, durable final store, Health adapters, dataset manifest registry/ancestry gate, source-input verification). Author-run; a survivor is a finding. Not run by CI."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
TR = "stage_a/coordination/transition_record.py"; RP = "stage_a/replay.py"; RV = "stage_a/tracker/reverification.py"; V = "stage_a/gateway/v038.py"; GW = "stage_a/gateway/contracts.py"; DS = "stage_a/gateway/durable_final_store.py"; HA = "stage_a/health/adapters.py"; DM = "stage_a/ml/dataset_manifest.py"; SI = "stage_a/tracker/source_inputs.py"; CC = "stage_a/ml/consumption_claim.py"
M = [
 (TR, 'if legacy_read and kind == CANONICAL_ACCEPTED and body_generation(kind, body) != "CURRENT"', 'if kind == CANONICAL_ACCEPTED and body_generation(kind, body) != "CURRENT"'),
 (RP, "T.validate_body(r.kind, body, legacy_read=True)", "T.validate_body(r.kind, body)"),
 (RP, 'legacy_binding_absent=T.body_generation(r.kind, body) != "CURRENT"', "legacy_binding_absent=False"),
 (RV, "if st.legacy_binding_absent: raise", "if False: raise"),
 (V, "return copy.deepcopy(self._by_identity[identity])          # never fish", "return self._by_identity[identity]          # never fish"),
 (V, "self._by_identity[identity] = copy.deepcopy(out)", "self._by_identity[identity] = out"),
 (V, "with self._lock: return [(i, copy.deepcopy(o)) for i, o in self._by_identity.items()]", "with self._lock: return [(i, o) for i, o in self._by_identity.items()]"),
 (V, "if old is not None and old != pin: raise", "if False: raise"),
 (GW, "elif canon != out: raise Refusal(request_id, code=\"WINDOW_OUTCOME_STORE_DISAGREES\")", "elif False: raise Refusal(request_id, code=\"WINDOW_OUTCOME_STORE_DISAGREES\")"),
 (GW, "self.final_store.identity_of(getattr(identity, \"consumer_id\", None), request_id) is None: raise", "False: raise"),
 (DS, 'if got is None or got[0] != pb: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 (DS, 'if got is None or got[0] != rec: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 (DS, 'if _ident_key(ident) != k: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 (DS, 'if _pin_key(ident) != k: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 (DS, 'if set(j["f"]) != {f.name for f in dataclasses.fields(cls)}: raise', 'if False: raise'),
 (HA, "return st, \"CALLER_POLICY_UNADMITTED\"", "return st, \"ADMITTED\""),
 (HA, "if st not in STATES or type(st) is not str: raise", "if False: raise"),
 (HA, "admitted: bool = False", "admitted: bool = True"),
 (DM, "if old[1] != m: raise Refusal(m.dataset_manifest_id, code=\"DATASET_MANIFEST_IMMUTABLE\")", "if False: raise Refusal(m.dataset_manifest_id, code=\"DATASET_MANIFEST_IMMUTABLE\")"),
 (DM, "if old is not None and old != mid: raise", "if False: raise"),
 (DM, "if mid not in self._m: return None", "if False: return None"),
 (DM, "(as_of_ts is None or e[1] <= as_of_ts)", "(as_of_ts is None or e[1] < as_of_ts)"),
 (DM, "if self._ledger and ts < self._ledger[-1][1]: raise", "if False: raise"),
 (DM, '"UNKNOWN": "BLOCKED_UNKNOWN", "CLEAN": "CLEAR"', '"UNKNOWN": "CLEAR", "CLEAN": "CLEAR"'),
 (SI, "if st.legacy_binding_absent: raise", "if False: raise"),
 (SI, 'any(v in ("MISSING", "MISMATCH", "UNRESOLVED") for v in out.values())', 'any(v in ("MISSING", "MISMATCH") for v in out.values())'),
 (SI, 'if extra or any', 'if any'),
 (SI, 'if resolver is None: out[n] = "BOUND_UNVERIFIED"', 'if resolver is None: out[n] = "BOUND_VERIFIED"'),
 (CC, "elif r is True:", "elif r:"),
 (CC, "if state.get(mid) == 1: raise Refusal(mid, code=\"LINEAGE_CYCLE\")", "if False: raise Refusal(mid, code=\"LINEAGE_CYCLE\")"),
 (CC, "if mid not in derived_from: unknown.add(mid)", "pass"),
 (CC, "if manifest_id not in derived_from: unknown.add(manifest_id)", "pass"),
 (CC, "elif r is not False: raise", "elif False: raise"),
 (CC, "({CONTRIBUTOR_LATER_REVOKED} if mid in direct else set())", "({CONTRIBUTOR_LATER_REVOKED} if True else set())"),
 (CC, "({DERIVED_FROM_REVOKED} if mid in deep else set())", "(set())"),
 (CC, '"transitive": mid in deep', '"transitive": False'),
 (CC, 'status = "AFFECTED" if affected else ("UNKNOWN" if unknown else "CLEAN")', 'status = "AFFECTED" if affected else "CLEAN"'),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r35_legacy_replay.py", "test_r35_window_resolution.py", "test_r35_durable_final_store.py", "test_r35_health_adapters.py", "test_r35_dataset_manifest.py", "test_r35_source_inputs.py", "test_r34_consumption_claim.py", "test_r34_fw_association.py")]
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
