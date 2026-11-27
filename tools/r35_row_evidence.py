"""R35 mechanical row evidence. PRESENCE/IMPORT evidence only - NOT a clause audit.
For each E03 row of the closeout section 3: does the repo location exist, last commit touching it, count of test files
that import/reference its module name. Output is a markdown table on stdout."""
import re, subprocess, pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
doc = (root / "docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md").read_text()
sec = doc.split("## 3. E-03", 1)[1].split("## 3A.", 1)[0]
tests = {p: p.read_text() for p in (root / "tests").rglob("*.py")}
print("| # | E-03 path | repo path(s) | exists | last commit | test files naming module | closeout STATE |\n|---|---|---|---|---|---|---|")
for line in sec.splitlines():
    m = re.match(r"\| (\d+) \| (\S+) \| (.*?) \| (\S[^|]*?) \|", line)
    if not m: continue
    n, e03, loc, state = m.groups()
    base = pathlib.Path(e03).name
    found = sorted(str(q.relative_to(root)) for q in (root / "stage_a").rglob(base) if "__pycache__" not in str(q))
    if loc.strip().startswith("`...") or loc.strip().startswith("`stage_a"):
        loc = " ".join("`" + f + "`" for f in found) if found else loc
    paths = sorted(set(re.findall(r"`(stage_a/[A-Za-z0-9_/]+(?:\.py)?)", loc))) or [e03 if e03.startswith('stage_a/') else 'stage_a/' + e03]
    ex, cm, tc = [], [], 0
    for p in paths:
        f = root / p
        ok = f.exists() or (root / (p + ".py")).exists() or (root / p).is_dir()
        ex.append("Y" if ok else "N")
        t = p if p.endswith(".py") else p + ".py"
        c = subprocess.run(["git", "log", "-1", "--format=%h", "--", t if (root / t).exists() else p], cwd=root, capture_output=True, text=True).stdout.strip()
        cm.append(c or "-")
        stem = pathlib.Path(p).stem
        tc = max(tc, sum(1 for s in tests.values() if re.search(r"\b" + re.escape(stem) + r"\b", s)))
    print(f"| {n} | {e03} | {', '.join(paths)} | {''.join(ex)} | {','.join(cm)} | {tc} | {state[:40]} |")
