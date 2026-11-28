"""R54 row audit WIRING generator: for every row of tools/r43_clause_reconciliation.ROWS, derives from the CURRENT source tree (not from the row prose) which cited modules have a non-test importer in stage_a/tracker_component (ASSEMBLY_REACHABLE) and which are TEST_ONLY (exercised generic connection, no production caller), and whether every cited test file stem exists. Hand verdicts in VERDICT are the Coder's R54 readings; rows without one say so. Generator equality proves transcription only; the verdict lines are the audit. Run: python tools/r54_row_audit.py > docs/closeout/TRK-STAGE-A-R54-ROW-AUDIT.md"""
import re, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import r43_clause_reconciliation as R
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = [p for d in ("stage_a", "tracker_component") for p in (ROOT / d).glob("**/*.py")]; TEXT = {p: p.read_text() for p in SRC}; TESTS = {p.stem for p in (ROOT / "tests").glob("**/*.py")}
# claims that are DOCUMENTARY/SUPPLIED-PARAMETER rather than import-wired (verified by reading the body, R54)
PARAM = {"tracker/status_emitter": "reached only through the `status_emitter=` PARAMETER of Composition.accept_and_publish (caller-supplied object; mapping supplied)", "coordination/lifecycle_framework": "reached only through the `lifecycle=` PARAMETER of Composition.accept_and_publish (object supplied by the caller; policy unbound => HELD)", "tracker/construction_binding": "reached through claims authorizes() callsite, qualified resolver always False"}
VERDICT = {
 "D10": "R54 CORRECTION: the status owning emitter is wired (called through the `status_emitter=` parameter of Composition.accept_and_publish, not imported; test_r50_composition_emitter). The ShadowLedger publication caller `ml/shadow_publication` is NOT called by Composition or any production module (grep: no importer); it is a standalone caller class exercised by tests only. The earlier R54 text saying it is called from Composition.accept_and_publish is WITHDRAWN. Lifecycle apply is a supplied-parameter call.",
 "B23": "R54: ml/consumer_path, ml/augmented_desk and ml/shadow_publication have NO production importer: they are exercised generic connections (tests), not wired into Composition. Composition.deliver_ml uses ml/receiver.build_row only. Reverse-H1/six-join/augmented association are therefore documentary+exercised, not integrated. Remaining: a governed caller (ML function) that invokes them.",
 "TR-14": "R54: same as B23 for ML shadow/augmented: exercised generic only; association stays HELD; no Composition-level caller for the publisher.",
 "TR-12": "R54: context/event_context_store has no production importer (only e05_sources references it by name); event/context correction records are exercised generic code, not wired into delivery. Remaining: the Context function caller that records and the Gateway/Health consumer that reads them.",
 "B11": "R54: lifecycle_framework is reached through a caller-supplied parameter; edge matrix unadopted (R54_DECISION_PACK s4).",
 "D1": "R54: construction_binding is consulted at the claims callsite; qualified resolver is always False.",
 "D3": "R54: candidate_code_tables has no production importer by design (candidate tables for tests/proposal); not an engine input.",
 "B07": "R54: composer/expression operators exercised by R45-R47 parity tests; invoked by the intake/verification path, normative bytes held.",
 "B21": "R54: FW+ML delivery on the real assembly is exercised (test_r53_real_assembly_base, test_r54_shared_rebuild): Composition.deliver/deliver_ml -> Gateway window path -> DurableFinalResolutionStore; E05 final-resolution rebuild from those records is exercised after cold restart. Composition.outcome_desk (R54) binds the H3 desk to the Composition Gateway; exercised after cold restart. Counterpart FW/ML processes and a production CBID source are NOT integrated.",
 "B18": "R54: planes enforced on restart (test_r54_shared_rebuild plane test) and E05 rebuild exercised on the shared assembly's own durable records; data/control/recording plane NAMES beyond the four source-named planes are not invented.",
}
def wiring(code):
    out = []
    for pth in sorted(set(re.findall(r"\b((?:[a-z_0-9]+/)+[a-z_0-9]+)(?:\.py)?\b", code))):
        mod = pth.split("/")[-1]; fs = [p for p in SRC if p.stem == mod and pth.split("/")[-2] in p.parts]
        if not fs: continue
        users = sorted({q.stem for q in SRC if q.stem != mod and re.search(r"(import|from)\b.*\b" + mod + r"\b", TEXT[q])})
        out.append("%s: %s" % (pth, ("importers=" + ",".join(users[:4]) + ("+%d" % (len(users) - 4) if len(users) > 4 else "")) if users else ("PARAMETER:" + PARAM[pth] if pth in PARAM else "TEST_ONLY")))
    return "; ".join(out) or "n/a (no module cited)"
print("# R54 row audit (WIRING derived from the current tree; verdicts = Coder reading; NOT a gate)\n")
print("Equality of this table with the generator proves transcription only. WIRING is recomputed from importers in stage_a/ + tracker_component/. A module with TEST_ONLY wiring is an exercised generic connection, not an integrated caller. Rows with no verdict were not re-read in R54 and carry their R43-R54 clause-table reading.\n")
print("| Row | Status | Source | WIRING (computed) | Tests exist | R54 verdict |\n|---|---|---|---|---|---|")
for r in R.ROWS:
    rid, source, st, code, tst = r[:5]; miss = [t for t in re.split(r";\s*", tst) if t.strip() and t.strip() != "-" and t.strip() not in TESTS]
    print("| %s | %s | %s | %s | %s | %s |" % (rid, st, source.replace("|", "/"), wiring(code).replace("|", "/"), "YES" if not miss else "MISSING:" + ",".join(miss), VERDICT.get(rid, "not re-read in R54")))
