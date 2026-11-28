"""R38 mutants for code added/changed in R38. Each mutant must be KILLED by the R38 tests (+ the R37 tests that share the code); applied one at a time, file restored; NOT APPLICABLE or SURVIVED fails the run. Named equivalents are listed in the closeout."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
GW="stage_a/gateway/contracts.py"; PJ="stage_a/tracker/status_projection.py"; SP="stage_a/tracker/sim_publication_path.py"; SV="stage_a/tracker/stored_values.py"; PS="stage_a/ops/process_supervisor.py"; WC="stage_a/ops/worker_child.py"; ER="stage_a/tracker/evidence_resolver.py"; RL="stage_a/tracker/research_lineage.py"
LF="stage_a/coordination/lifecycle_framework.py"; CO="stage_a/tracker/composition.py"; RS="stage_a/tracker/relationship_store.py"; SB="stage_a/tracker/snapshot_binding.py"
M = [
 (GW, 'if cls == "SIMULATION" or getattr(self.status, "simulation", False) is True:', 'if cls == "SIMULATION":'),
 (GW, 'if cls not in ("QUALIFIED", "SIMULATION") and not self.allow_uncommitted_status:', 'if False:'),
 (GW, 'if not self.allow_simulation_status: return nd("STATUS_SOURCE_SIMULATION_NOT_ALLOWED")', 'pass'),
 (PJ, "return self.carrier_class == SIMULATION", "return False"),
 (PJ, "except Refusal: return None", "except Refusal: return QUALIFIED"),
 (PJ, "try: return self._guard() is True", "try: return True"),
 (PJ, "if self._guard is None: return True", "return True"),
 (SP, 'if vs is None or vs.status not in LIVE_STATES: raise', 'if False: raise'),
 (SP, 'if st.status not in LIVE_STATES: raise Refusal(st.status, code="SIM_PUBLICATION_SOURCE_NOT_LIVE")', 'pass'),
 (SP, 'if (b.get("source_head_seq"), b.get("source_head_hash")) != (cur.seq, cur.hash): raise', 'if False: raise'),
 (SP, 'if latest[b["feature_key"]] is b:', 'if False:'),
 (SP, '"source_head_seq": src.seq, "source_head_hash": src.hash,', '"source_head_seq": 0, "source_head_hash": "0",'),
 (SP, 'src = self._fj.head()  ', 'src = type(self._fj.head())(0, "0")  '),
 (SP, "p = StatusProjection(self._sj, self._decode, simulation=True, source_guard=self.source_current)", "p = StatusProjection(self._sj, self._decode, simulation=True)"),
 (SP, "or st.accepted_hash != b[\"accepted_hash\"]", ""),
 (SV, 'if got != (want, want): raise', 'if False: raise'),
 (SV, 'if authority_class_of(journal) != authority_class_of(store): raise', 'if False: raise'),
 (SV, '"hash": bindings[n]["hash"]} for n in sorted(bindings)})', '"hash": ""} for n in sorted(bindings)})'),
 (SV, 'and rec.get("segment_id") == segment_id(bindings)', ''),
 (SV, 'overall = "FAIL" if "FAIL" in ov else "UNAVAILABLE" if "UNAVAILABLE" in ov else', 'overall = "FAIL" if "FAIL" in ov else'),
 (SV, 'if not keys: return dict(base, overall="UNAVAILABLE"', 'if False: return dict(base, overall="UNAVAILABLE"'),
 (SV, 'if n >= max_items: out.append((sub, work[sub], "SKIPPED_BOUND_EXCEEDED", "")); continue', 'pass'),
 (SV, 'for sub, trig in core.due_for_reverification(list(subjects), now, vers): work[sub] = trig', 'for sub in subjects: work[sub] = "ABSENT"'),
 (PS, " or d[\"pid\"] != p.pid", ""),
 (PS, "if self._procs[w].poll() is not None: self._replace(w)", "pass"),
 (PS, "if res == \"LOST\": self._replace(w)", "pass"),
 (PS, "if self._tries[k] >= self._max: self.dead[k]", "if False: self.dead[k]"),
 (PS, "if self.respawns >= self._maxresp: raise", "if False: raise"),
 (PS, "if res == \"DONE\": self._q.complete(k)", "if True: self._q.complete(k)"),
 (WC, 'if spec is None: _reply(job.job_id, "REFUSED", "KIND_NOT_OWNED_BY_WORKER"); continue', 'pass'),
 (ER, "if pins.get(ref) != h:", "if False:"),
 (ER, "if rec.available_at > watermark:", "if False:"),
 (ER, "revoked=ref in revoked", "revoked=False") if False else (ER, '"revoked": ref in revoked', '"revoked": False'),
 (ER, 'if g in ("ALTERED", "AMBIGUOUS"):', 'if False:'),
 (ER, "if receipt.claim_hash != fresh.claim_hash or receipt.refs != fresh.refs or receipt.store_id != fresh.store_id: raise", "if False: raise"),
 (ER, "authoritative: bool = False", "authoritative: bool = True"),
 (RL, "if type(declared_n) is not int or declared_n != truth: raise", "if False: raise"),
 (RL, 'if atts[attempt_id]["status"] != "COMPLETED": raise', "if False: raise"),
 (RL, "if (family, battery) not in bats: raise", "if False: raise"),
 (RL, "if any(p not in atts for p in parents): raise", "if False: raise"),
 (RL, "if atts[attempt_id] != body: raise", "if False: raise"),
 (LF, "if self._p is None: raise", "if False: raise"),
 (LF, "if have in p.terminal: raise", "if False: raise"),
 (LF, "if have != from_state: raise", "if False: raise"),
 (LF, "if (from_state, to_state) not in p.allowed: raise", "if False: raise"),
 (LF, "if self._ev is None: raise", "if False: raise"),
 (LF, "if not ok: raise", "if False: raise"),
 (LF, "if expected_head is not None and expected_head != head: raise", "if False: raise"),
 (CO, 'if getattr(out, "accepted", None) is None or out.accepted.kind != "CANONICAL_ACCEPTED": r.status', 'if False: r.status'),
 (CO, "binding=binding, require_ancestry=True)", "binding=binding, require_ancestry=False)"),
 (CO, "if self.gateway is None or result.feature_key is None: raise", "if False: raise"),
 (RS, "if not (self._own(rel.predecessor) and self._own(rel.successor)): raise", "if False: raise"),
 (RS, "if not (self._own(predecessor) and self._own(successor)): return RelationshipReference(", "if False: return RelationshipReference("),
 (RS, "r.state == VD.COMPUTED and r.relationship_class is not None", "True"),
 (RS, "return st is not None and st.status in LIVE", "return st is not None"),
 (SB, 'if body.get("mixed_policy") is not None or', "if"),
 (SB, "if set(ents) != set(wm): raise", "if False: raise"),
 (SB, 'if e["watermark"] != wm[tf]: raise', "if False: raise"),
 (SB, 'if e["vintage"] != manifest.data_vintage_mode: raise', "if False: raise"),
 (SB, 'if (body["query_asof"], body["fence"]) != (manifest.query_asof, manifest.snapshot_fence_ts): raise', "if False: raise"),
]
EQUIVALENT = [   # NAMED EQUIVALENTS (behaviour-identical; recorded, not hidden)
 (PS, 'if not r: p.kill(); p.wait(); return "LOST"', 'if not r: return "LOST"', "run_one calls _replace on LOST, which kills and reaps the same child: the kill in _ask is redundant"),
 (ER, "if not claim.evidence_refs: return out(INVALID", "if False: return out(INVALID", "judge_transition_evidence returns the identical INVALID/NO_EVIDENCE_REFERENCED for an empty ref tuple (duplicate guard)"),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r38_projection_class.py", "test_r38_sim_publication_source.py", "test_r38_stored_values_class.py", "test_r38_stored_values_scope.py", "test_r38_process_supervisor.py", "test_r38_evidence_resolver.py", "test_r38_research_lineage.py", "test_r38_lifecycle_framework.py", "test_r38_composition.py", "test_r38_relationship_snapshot.py", "test_r37_sim_publication_path.py", "test_r37_stored_values.py", "test_r12_status_projection.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=180, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
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
