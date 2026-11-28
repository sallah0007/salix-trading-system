"""R38: generates the ONE combined CURRENT requirement table (docs/closeout/TRK-STAGE-A-R38-CURRENT-REQUIREMENT-TABLE.md).
Columns: source clause (Build Plan 1CVUUPJ4... s29A E-03 final package map + s27 TR row; cited by section, no text copied) / current code at HEAD (last commit per module, computed) / callpath (static import reachability from pipeline, TrackerCore, composition: IMPORT evidence only, never semantic coverage) / meaningful test files that exist (curated map; the tool asserts each file exists) + review limits; OR for rows with no code: precise input / owner ROLE / consequence / recommendation.
Run: python tools/r38_current_table.py > docs/closeout/TRK-STAGE-A-R38-CURRENT-REQUIREMENT-TABLE.md  (reproducible by the Manager; commit sha is the git HEAD it ran on)."""
import ast, pathlib, re, subprocess, sys
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
ENT = {"PIPE": closure("stage_a.tracker.pipeline"), "CORE": closure("stage_a.core.tracker_core"), "COMP": closure("stage_a.tracker.composition")}
HEAD = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
def last(p): return subprocess.run(["git", "log", "-1", "--format=%h", "--", str(p.relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "UNCOMMITTED"
TR = {"expression": "TR-01/03/04/09", "composer": "TR-05/06", "tracker": "TR-02/09", "context": "TR-12", "gateway": "TR-06/07/10", "fw": "TR-13", "ml": "TR-14", "health": "TR-08", "coordination": "TR-11", "storage": "TR-15 (E-09 keys)", "root": "TR-10/TR-11 support"}
T = lambda *n: n
TESTS = {"expression": T("test_expression.py", "test_r38_tr_dod.py", "test_r11_arithmetic.py"), "composer": T("test_r29_intake_order.py", "test_r38_tr_dod.py"), "tracker": T("test_pipeline.py", "test_r33_composed.py", "test_r38_composition.py"),
         "verification": T("test_verifier_independence.py", "test_r33_composed.py"), "context": T("test_context_contracts.py", "test_r13_context_resolver.py", "test_r38_tr_dod.py"), "gateway": T("test_boundaries.py", "test_r37_sim_publication_path.py", "test_r38_sim_publication_source.py", "test_r38_projection_class.py"),
         "fw": T("test_r36_outcome_desk.py", "test_r38_composition.py"), "ml": T("test_r37_ml_required_nondelivery.py", "test_r37_dataset_lineage.py"), "health": T("test_health_envelope.py", "test_r34_health_subjects.py", "test_r38_relationship_snapshot.py"), "coordination": T("test_r38_tr_dod.py", "test_r38_lifecycle_framework.py", "test_r38_process_supervisor.py"),
         "storage": T("test_foundations.py", "test_r38_stored_values_scope.py"), "root": T("test_foundations.py", "test_r24_core.py")}
LIMIT = "author-run only; SIMULATION class; passes clear no gate; mutation-swept where a sweep names it"
HELD = {10: ("Composer build executor: Composer-owned producer; no source schema of the produced BuildPackage beyond the Tracker-side check", "Composer owner ROLE", "no real producer: requested builds stay simulated", "keep LATER; Manager decides whether Composer producer enters this segment"),
        11: ("Composer refit executor: Composer-owned; fit generation producer", "Composer owner ROLE", "fit refs only checkable against caller-supplied accepted generations", "keep LATER"),
        48: ("health/expectation.py: expectation-state rule is undefined in every source read (B0 HELD slot EXPECTATION_STATE)", "Health/Master Health source owner ROLE", "no expectation verdict can be produced; silence only via derive_silence", "Manager to point at the expectation-rule clause or confirm it is absent")}
ROOTTR = {"authority": "TR-02 (identity/authority refs)", "identifiers": "TR-15 (instrument-qualified keys)", "errors": "none (support)", "clocks": "TR-10 (fence/as-of clocks)", "currentness": "TR-10", "replay": "TR-11 (rebuild from journal)", "observability": "TR-08 / E-08 (telemetry not authority)"}
def tests_for(path):
    parts = path.removeprefix("stage_a/").split("/"); key = "verification" if "verification" in parts else parts[0] if len(parts) > 1 else "root"
    ts = [t for t in TESTS.get(key, ()) if (ROOT / "tests/trk_stage_a" / t).exists()]; missing = [t for t in TESTS.get(key, ()) if t not in ts]
    assert not missing, ("curated test file missing", path, missing); return ts, (TR.get(parts[0], "") if len(parts) > 1 else ROOTTR.get(parts[0].removesuffix(".py"), "root support"))
rows = [l for l in DOC.read_text().split("## 3. E-03", 1)[1].split("## 3A.", 1)[0].splitlines() if re.match(r"\| \d+ \|", l)]
extra = [("58", "stage_a/tracker/verification/independent_encoding.py"), ("59", "stage_a/tracker/verification/independent_hashing.py"), ("60", "stage_a/tracker/verification/independent_traversal.py"), ("61", "stage_a/storage/byte_primitives.py")]
print("# TRK Stage A: ONE combined CURRENT requirement table (R38)\n")
print("Generated by `tools/r38_current_table.py` at git HEAD `%s`. Older sections of the closeout stay as HISTORY (including the Rescue material). Not a gate, acceptance or appointment. DERIVATION_CLASS: code commit/reachability = INDEPENDENTLY_DERIVED (git + static `ast` import graph); test column = curated names asserted to exist, NOT proof the test covers the clause; semantic coverage is in the closeout rows and the review limits. REPRODUCIBLE_BY_MANAGER = YES.\n" % HEAD)
print("Source clause for every row: Build Plan s29A `E-03 FINAL REPOSITORY MODULE MAP` entry for that path (+ `E-03 MODULE MAP ADDITIONS` for rows 58-61) read in R38 from Drive 1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo (modified 2026-11-11T06:06:17Z), plus the s27 TR row named. The E-03 map gives path + owner only; the per-module responsibility is the TR/DoD sentence, so a row's 'requirement' is that sentence, not a module-internal spec.\n")
print("| # | E-03 path | s27 TR row / clause | current code (last commit) | callpath (import reach: PIPE/CORE/COMP) | tests that exist + limits  OR  input / owner ROLE / consequence / recommendation |\n|---|---|---|---|---|---|")
ALIAS = {32: ("stage_a/context/news_hub_v2.py", "stage_a/context/decision_context.py"), 35: ("stage_a/gateway/v038.py", "stage_a/gateway/durable_final_store.py"), 36: ("stage_a/gateway/v038.py",), 37: ("stage_a/gateway/contracts.py",), 42: ("stage_a/ml/receiver.py",), 43: ("stage_a/ml/receiver.py",)}      # alias rows whose closeout text names symbols, not files (symbols named in closeout s3)
def emit(n, path, loc, state):
    if int(n) in ALIAS: loc = " ".join("`%s`" % a for a in ALIAS[int(n)])
    mods = [modname(ROOT / q) for q in re.findall(r"`(stage_a/[\w/]+\.py)`", loc) if (ROOT / q).exists()] if loc else []
    if not mods:
        suf = path.removeprefix("stage_a/"); mods = [modname(q) for q in sorted((ROOT / "stage_a").rglob(suf.split("/")[-1])) if q.as_posix().endswith(suf)]
    mods = [m for m in mods if m in files]
    if not mods:
        h = HELD.get(int(n), ("no repo module resolved; responsibility not located", "Manager", "row unaudited", "Manager to map path or confirm LATER"))
        print("| %s | `%s` | %s | none | - | **INPUT** %s; **OWNER ROLE** %s; **CONSEQUENCE** %s; **RECOMMEND** %s |" % (n, path, TR.get(path.removeprefix("stage_a/").split("/")[0], "-") if "/" in path.removeprefix("stage_a/") else "-", *h)); return
    ts, tr = tests_for(path); f = lambda k: "Y" if any(m in ENT[k] for m in mods) else "N"; code = ", ".join("`%s`@%s" % (m.removeprefix("stage_a."), last(files[m])) for m in mods)
    alias = "" if (ROOT / path).exists() else " ALIAS (filename absent; responsibility mapped; not counted as coverage by name)"
    print("| %s | `%s` | %s | %s%s | %s/%s/%s | %s; state: %s; %s |" % (n, path, tr, code, alias, f("PIPE"), f("CORE"), f("COMP"), ", ".join(ts), state, LIMIT))
for l in rows:
    c = [x.strip() for x in l.strip("|").split("|")]; emit(c[0], c[1] if c[1].startswith("stage_a/") else "stage_a/" + c[1], c[2], c[3])
for n, p in extra: emit(n, p, "`%s`" % p, "INVOKED")
print("\n## TR-10 observed implementation route (traceability only; the filename `gateway/dependency_resolution.py` is absent and that is NOT semantic absence)\n`gateway.contracts.SimulatedGateway._compute` (half-open fence `available_asof < fence`, equality excluded; technical latest never authority: eligibility is selected among causally valid candidates, MULTIPLE_CANDIDATES refuses) and `SimulatedGateway.resolve_window` (durable immutable per-window outcome) plus `gateway.binding`/`v038` settlement helpers. No governing adoption of that mapping is claimed; the E-03 filename mapping is a Manager decision.")
print("\n## TR-03/04/06/09/11/12 re-evaluation (R38, was NOT RE-EVALUATED in R35): `tests/trk_stage_a/test_r38_tr_dod.py` asserts each DoD sentence directly (positive + negative); author-run; see closeout s17.")
