"""R14 mutants for the News Hub resolver causal clauses. Run: python3 -B tests/trk_stage_a/mutation_sweep_r14.py (60 s per-mutant timeout; hang = killed)"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
NH = "stage_a/context/news_hub_v2.py"
M = [(NH, '    if ev["PUBLICLY_AVAILABLE_AT"] > cutoff:', "    if False:"), (NH, '    if ev["SALIX_RECEIVED_AT"] > cutoff:', "    if False:"),
     (NH, '    if ev["AVAILABLE_ASOF"] > cutoff:', "    if False:"), (NH, '    if ev["AVAILABLE_ASOF"] < max(ev["PUBLICLY_AVAILABLE_AT"], ev["SALIX_RECEIVED_AT"]):', "    if False:"),
     (NH, '    if ev["REVISION_AVAILABLE_AT"] > cutoff:', "    if False:"), (NH, 'ev["ACTUAL_AVAILABLE_ASOF"] > cutoff:', "False:"),
     (NH, '            if ev.get(stamp) is None:', "            if False:"), (NH, "            if ev[stamp] > cutoff:", "            if False:"),
     (NH, "    check_event_record(ev)                                                              # never rely", "    pass                                                              # never rely"),
     (NH, '    _need_ts(rec, TS_FIELDS, "EVENT_TIMESTAMP_MALFORMED")', "    pass"), (NH, '        _need_ts(rec, ACTUAL_TS_FIELDS, "EVENT_TIMESTAMP_MALFORMED")', "        pass"),
     (NH, "    return isinstance(v, int) and not isinstance(v, bool)", "    return isinstance(v, int)"),
     (NH, '        if rec.get(stamp) is not None and not _is_ts(rec[stamp]):', "        if False:"),
     (NH, '    check_daily_record(daily_record)\n', "    pass\n"), (NH, '    if not _is_ts(rec["ISSUED_AT"]):', "    if False:"),
     (NH, '    if not _is_ts(decision_cutoff):\n        raise Refusal("decision cutoff", code="CUTOFF_MALFORMED")\n    if governed_revision_rule', "    if governed_revision_rule"),
     (NH, '    if not _is_ts(cutoff):', "    if False:"), (NH, "        if governed_revision_rule is None:\n            multi.append", "        if False:\n            multi.append"),
     (NH, "governed_revision_rule not in KNOWN_REVISION_RULES:", "False:"), (NH, "top = max(e.get(\"REVISION_SEQ\", 0) for e in avail)", "top = min(e.get(\"REVISION_SEQ\", 0) for e in avail)"),
     (NH, '    if daily_record["EVENT_PRESENCE_STATE"] == "NO_EVENT_RECORDED" and used:', "    if False:"),
     (NH, '    if not isinstance(rec, dict):\n        raise Refusal("event record not a mapping"', '    if False:\n        raise Refusal("event record not a mapping"'),
     (NH, '    if not isinstance(rec, dict):\n        raise Refusal("daily record not a mapping"', '    if False:\n        raise Refusal("daily record not a mapping"'),
     (NH, '        verdict = "NON_AUTHORITATIVE_SELECTION"', '        verdict = "USABLE"'), (NH, '        verdict = "MULTIPLE_CANDIDATES"', '        verdict = "USABLE"'),
     (NH, '    if not isinstance(result, dict) or result.get("verdict") != "USABLE":', "    if False:"), (NH, "            rule_selected = True", "            pass"),
     (NH, '"selection_rule_verified": False,\n            "admission"', '"selection_rule_verified": True,\n            "admission"'),
     (NH, "        if len(distinct) == 1:", "        if False:"), (NH, "    if daily_record is None:", "    if False:"), (NH, "    if not daily_record_joinable(", "    if False and not daily_record_joinable(")]
T = ["tests/trk_stage_a/test_r13_context_resolver.py", "tests/trk_stage_a/test_r14_event_causality.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
