"""R45 mutation sweep for select/compare. Each mutant must be killed by tests/trk_stage_a/test_r45_select_compare.py (run: python -m tests.trk_stage_a.mutation_sweep_r45)."""
import subprocess, sys
EV, SC, CE, IT = ("stage_a/composer/expression/evaluator.py", "stage_a/composer/expression/schema.py", "stage_a/composer/expression/ceilings.py",
                  "stage_a/tracker/verification/independent_traversal.py")
M = [
 (EV, 'return canon(get(node["args"][1] if c is True else node["args"][2], t))', 'a_ = get(node["args"][1], t); b_ = get(node["args"][2], t); return canon(a_ if c is True else b_)', "select eager"),
 (EV, 'return canon(get(node["args"][1] if c is True else node["args"][2], t))', 'return canon(get(node["args"][2] if c is True else node["args"][1], t))', "select branches swapped"),
 (EV, '"lt": a[0] < a[1]', '"lt": a[0] <= a[1]', "lt -> le"),
 (EV, '"ge": a[0] >= a[1]', '"ge": a[0] > a[1]', "ge -> gt"),
 (EV, '''        if c is None:
            return None
        return canon(get''', '''        if c is None:
            c = False
        return canon(get''', "missing cond treated false"),
 (SC, '_req(memo[output] == "F64", "OUTPUT_NOT_F64", output)', 'pass', "bool output allowed"),
 (SC, '_req(memo[a] == w, "TYPE_MISMATCH"', '_req(True, "TYPE_MISMATCH"', "type mismatch ignored"),
 (CE, 'if branches > ceilings["MAX_BRANCH_COUNT"]', 'if False', "branch ceiling off"),
 (IT, 'if c is None: res.append(None)', 'if c is None: res.append(0.0)', "reference missing cond"),
 (IT, 'v = row[1] if c is True else row[2]', 'v = row[2] if c is True else row[1]', "reference branches swapped"),
 (IT, "if not lazy: raise\n            return _FAIL", "raise", "reference eager failure"),
]
def main():
    surv = []
    for f, a, b, name in M:
        src = open(f).read(); assert src.count(a) == 1, name
        open(f, "w").write(src.replace(a, b))
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", "tests/trk_stage_a/test_r45_select_compare.py", "-q", "-x"], capture_output=True)
        finally:
            open(f, "w").write(src)
        if r.returncode == 0: surv.append(name)
        print(("SURVIVED " if r.returncode == 0 else "killed   ") + name)
    print("survivors:", surv); return 1 if surv else 0
if __name__ == "__main__": sys.exit(main())
