import subprocess, sys
F = "stage_a/ml/shadow_ledger.py"
M = [("raise Refusal(trigger_id, code=\"SHADOW_EVENT_ID_CONFLICT\" if cur[0] != prediction_event_id else \"SHADOW_TERMINAL_IMMUTABLE\")", "return \"RECORDED\"", "terminal reopened"),
     ("if logical_key in self._sealed: raise Refusal(logical_key, code=\"SHADOW_RETROACTIVE_BACKFILL_PROHIBITED\")\n        prov =", "prov =", "seal ignored on record"),
     ("if logical_key in self._sealed and (logical_key, trigger_id) not in self._expected:", "if False:", "seal ignored on expect"),
     ("self._expected.setdefault((logical_key, trigger_id), None)", "self._expected[(logical_key, trigger_id)] = None", "expect resets a disposition (equivalent only before disposition; killed by idempotence)"),
     ("return None if c[\"EXPECTED\"] == 0 else (c[\"PUBLISHED\"], c[\"EXPECTED\"])", "return None if c[\"EXPECTED\"] == 0 else (c[\"PUBLISHED\"], c[\"EXPECTED\"] - c[\"MISSING_OR_IN_PROGRESS\"])", "missing leaves denominator"),
     ("return None if c[\"EXPECTED\"] == 0 else (c[\"PUBLISHED\"], c[\"EXPECTED\"])", "return (0, 0) if c[\"EXPECTED\"] == 0 else (c[\"PUBLISHED\"], c[\"EXPECTED\"])", "empty -> (0,0)"),
     ("if (logical_key, trigger_id) not in self._expected: raise", "if False: raise", "unexpected trigger accepted"),
     ("if prov is not None and outcome == \"PUBLISHED\": raise", "if False: raise", "published after provisional"),
     ("and outcome != \"LIFECYCLE_FENCED\": raise", "and False: raise", "fence cannot supersede different provisional id"),
     ("if prev is not None and prev[:2] != slot: raise", "if False: raise", "id reused across triggers"),
     ("if outcome not in OUTCOMES:", "if False:", "outcome unchecked"),
     ("if self._expected[(logical_key, trigger_id)] is not None: raise Refusal(trigger_id, code=\"SHADOW_TERMINAL_ALREADY_RECORDED\")", "pass", "provisional after terminal"),
     ("if k != logical_key: continue", "pass", "counters cross keys")]
s = []
for a, b, n in M:
    src = open(F).read(); assert src.count(a) == 1, n; open(F, "w").write(src.replace(a, b))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "tests/trk_stage_a/test_r45_shadow_ledger.py", "-q", "-x"], capture_output=True)
    finally: open(F, "w").write(src)
    print(("SURVIVED " if r.returncode == 0 else "killed   ") + n); r.returncode == 0 and s.append(n)
print("survivors:", s)
