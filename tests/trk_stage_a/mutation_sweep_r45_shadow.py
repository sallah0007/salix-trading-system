import subprocess, sys
F = "stage_a/ml/shadow_ledger.py"
M = [('return "DUPLICATE_NOOP"', 'self._rows[prediction_event_id] = row; return "DUPLICATE_NOOP"' , "EQUIVALENT: dup overwrite (old == row there, identical write)"),
     ("if old != row:", "if False:", "conflict ignored"),
     ("if logical_key in self._sealed:", "if False:", "seal ignored"),
     ('return None if n == 0 else (c["PUBLISHED"], n)', 'return (0, 0) if n == 0 else (c["PUBLISHED"], n)', "empty -> (0,0)"),
     ('return None if n == 0 else (c["PUBLISHED"], n)', 'return None if n == 0 else (c["PUBLISHED"], n - c["LIFECYCLE_FENCED"])', "fenced hidden from denominator"),
     ("if outcome not in OUTCOMES:", "if False:", "outcome unchecked"),
     ("if k == logical_key:", "if True:", "counters cross keys")]
s = []
for a, b, n in M:
    src = open(F).read(); assert src.count(a) == 1, n; open(F, "w").write(src.replace(a, b))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "tests/trk_stage_a/test_r45_shadow_ledger.py", "-q", "-x"], capture_output=True)
    finally: open(F, "w").write(src)
    print(("SURVIVED " if r.returncode == 0 else "killed   ") + n); r.returncode == 0 and s.append(n)
print("survivors:", s)
