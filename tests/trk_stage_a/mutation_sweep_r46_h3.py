import subprocess, sys
F = "stage_a/gateway/outcome_delivery.py"
M = [("if a <= cur < b: cur = b", "if a <= cur <= b: cur = b", "EQUIVALENT: closed end covers (cur==b reassigns b)"), ("def hits(regions): return any(a < e and s < b for a, b in regions)", "def hits(regions): return any(a <= e and s <= b for a, b in regions)", "touching counts as overlap"),
     ("if hits(sealed_holdout) and \"holdout_unseal_event_ref\" not in record:", "if False:", "sealed ignored"), ("if hits(unopened_regions):", "if False:", "unopened ignored"),
     ("if not _covered(s, e, ivs):", "if False:", "coverage ignored"), ("if not s < e:", "if s > e:", "empty interval allowed"), ("if record[\"available_asof\"] > record[\"delivery_decision_ts\"]:", "if False:", "causality ignored"),
     ("if miss or extra:", "if miss:", "extra fields allowed"), ("if segments_by_name is None:", "if False and segments_by_name is None:", "unsupplied model accepted"),
     ("return OutcomeDecision(not reasons, tuple(reasons))", "return OutcomeDecision(True, tuple(reasons))", "delivers despite reasons")]
s = []
for a, b, n in M:
    src = open(F).read(); assert src.count(a) == 1, n; open(F, "w").write(src.replace(a, b))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "tests/trk_stage_a/test_r46_outcome_delivery.py", "-q", "-x"], capture_output=True)
    finally: open(F, "w").write(src)
    print(("SURVIVED " if r.returncode == 0 else "killed   ") + n); r.returncode == 0 and s.append(n)
print("survivors:", s)
