"""Static import reachability over stage_a (AST, no execution). A module is INTEGRATED only if non-test code reachable from an entry module imports it;
otherwise REFERENCE_ONLY (exercised by tests, but no production call path). This is evidence about call paths, not about correctness."""
import ast, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2] / "stage_a"
def _mods():
    return {".".join(("stage_a",) + f.relative_to(ROOT).with_suffix("").parts): f for f in ROOT.rglob("*.py")}
def import_graph():
    mods = _mods(); g = {m: set() for m in mods}
    for m, f in mods.items():
        pkg = m if f.name == "__init__.py" else m.rsplit(".", 1)[0]
        for n in ast.walk(ast.parse(f.read_text())):
            if isinstance(n, ast.ImportFrom):
                base = n.module or ""
                if n.level:
                    parts = pkg.split(".")[: len(pkg.split(".")) - (n.level - 1)]
                    full = ".".join(parts + ([base] if base else []))
                else:
                    full = base
                for a in n.names:
                    for c in (full + "." + a.name, full):
                        if c in mods:
                            g[m].add(c); break
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.name in mods:
                        g[m].add(a.name)
    return g
def reachable(entries):
    g = import_graph(); seen, st = set(), list(entries)
    while st:
        m = st.pop()
        if m in seen or m not in g:
            continue
        seen.add(m); st.extend(g[m])
    return seen

def called_names(rel_path):
    """Names called (as plain names or attributes) anywhere in a stage_a module: FUNCTION-INVOCATION evidence, which an import alone is not."""
    t = ast.parse((ROOT.parent / rel_path).read_text()); out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            out.add(n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", ""))
    return out
