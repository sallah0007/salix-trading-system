"""R25 code-derived E03 per-row callpath evidence (stdlib only). Reads docs/closeout closeout table s3 for the 57 rows, resolves repo files from backticked paths, builds the static import graph with ast,
and reports reachability from three entry modules plus test references. METHOD is static import reachability: it shows a module is IMPORTED on a callpath, NOT that the clause is semantically implemented."""
import ast, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]; DOC = ROOT / "docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md"
def modname(p): return ".".join(p.relative_to(ROOT).with_suffix("").parts).removesuffix(".__init__")
files = {modname(p): p for p in list((ROOT / "stage_a").rglob("*.py")) + list((ROOT / "tracker_component").rglob("*.py"))}
def imports(mod):
    p = files[mod]; pkg = mod if p.name == "__init__.py" else mod.rpartition(".")[0]; out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            for a in n.names: out.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level: parts = pkg.split(".")[: len(pkg.split(".")) - (n.level - 1)]; base = ".".join(parts + ([base] if base else []))
            out.add(base)
            for a in n.names: out.add(base + "." + a.name)
    res = set()
    for i in out:
        while i and i not in files: i = i.rpartition(".")[0]
        if i: res.add(i)
    return res
G = {m: imports(m) for m in files}
def closure(entry):
    seen, st = set(), [entry]
    while st:
        m = st.pop()
        if m in seen or m not in G: continue
        seen.add(m); st += list(G[m])
        if "." in m: st.append(m.rpartition(".")[0])
    return seen
ENT = {"PIPE": closure("stage_a.tracker.pipeline"), "CORE": closure("stage_a.core.tracker_core"), "REVERIFY": closure("stage_a.tracker.reverify_scheduler")}
tests = {p: p.read_text() for p in (ROOT / "tests").rglob("*.py")}
rows = [l for l in DOC.read_text().split("## 3. E-03", 1)[1].split("## 4.", 1)[0].splitlines() if re.match(r"\| \d+ \|", l)]
print("| # | E-03 path | repo module(s) resolved | PIPE | CORE | REVERIFY | tests importing | R25 derived reachability |\n|---|---|---|---|---|---|---|---|")
for l in rows:
    c = [x.strip() for x in l.strip("|").split("|")]; n, path, loc = c[0], c[1], c[2]
    mods = [m for m in (modname(ROOT / q) for q in re.findall(r"`(stage_a/[\w/]+\.py|tracker_component/[\w/]+\.py)`", loc) if (ROOT / q).exists()) if m in files]
    if not mods:                    # shorthand rows ("`.../x.py`"): resolve by E-03 path suffix under stage_a (all matches kept; "stage_a/" prefix stripped)
        suf = path.removeprefix("stage_a/"); mods = [modname(q) for q in sorted((ROOT / "stage_a").rglob(suf.split("/")[-1])) if q.as_posix().endswith(suf)]
        mods = [m for m in mods if m in files]
    if not mods: print("| %s | %s | none (no repo module resolved from the row) | - | - | - | - | NOT_BUILT_OR_UNRESOLVED_PATH |" % (n, path)); continue
    f = lambda k: "Y" if any(m in ENT[k] for m in mods) else "N"
    t = sum(1 for s in tests.values() if any(re.search(r"\b" + re.escape(m) + r"\b", s) or re.search(r"from\s+" + re.escape(m.rpartition(".")[0]) + r"\s+import[^\n]*\b" + re.escape(m.rpartition(".")[2]) + r"\b", s) for m in mods))
    d = "IMPORT_REACHABLE_NOT_EXECUTION_EVIDENCE" if "Y" in (f("PIPE"), f("CORE"), f("REVERIFY")) else "REFERENCE_ONLY_NO_IN_REPO_CALLER"
    print("| %s | %s | %s | %s | %s | %s | %d | %s |" % (n, path, ", ".join("`%s`" % m for m in mods), f("PIPE"), f("CORE"), f("REVERIFY"), t, d))
