"""R54 E-03 module-map audit: every path of the Build Plan E-03 FINAL REPOSITORY MODULE MAP (57 paths, re-read from the live Build Plan in the R54 resume) is checked against the CURRENT tree. For a path that exists the first docstring line is shown; for an absent path the responsibility's actual home is a HAND mapping whose every named symbol is VERIFIED to exist by this generator (the run fails if one does not), plus its class (EQ behaviour exists elsewhere; LATER counterpart-owned; MISSING genuinely absent). Filename equality is NOT closure. Run: python tools/r54_e03_audit.py > docs/closeout/TRK-STAGE-A-R54-E03-AUDIT.md"""
import ast, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
PATHS = """authority.py identifiers.py errors.py clocks.py currentness.py replay.py observability.py
composer/request_classification.py composer/governed_order_adapter.py composer/build_executor.py composer/refit_executor.py composer/build_output.py composer/expression/manifest.py composer/expression/schema.py composer/expression/canonical_encoding.py composer/expression/hashing.py composer/expression/opcodes.py composer/expression/capability.py composer/expression/evaluator.py composer/expression/fit_generation.py composer/expression/artifacts.py
tracker/quant_intake_adapter.py tracker/quant_certification.py tracker/publication.py tracker/materialization/stateful_materializer.py tracker/verification/stateful_verifier.py tracker/verification/verification_result.py
context/event_identity.py context/coverage.py context/applicability.py context/resolver.py context/causal_gate.py
gateway/dependency_resolution.py gateway/binding.py gateway/non_delivery.py gateway/settlement.py gateway/health_snapshot.py
fw/request_adapter.py fw/input_binding.py fw/return_lineage.py
ml/dataset_binding.py ml/standalone_ancestry.py ml/fw_augmented_rebind.py ml/generation_lineage.py
health/b0_adapter.py health/quant_evidence.py health/blast_radius.py health/expectation.py
coordination/interface.py coordination/transition_record.py coordination/object_store_journal.py coordination/fencing.py coordination/recovery.py coordination/scheduler.py
storage/object_store.py storage/postgres_read_model.py storage/keys.py""".split()
assert len(PATHS) == 57
# absent path -> (class, [(file, symbol)...], note). Symbols are verified to exist.
M = {
 "composer/governed_order_adapter.py": ("LATER", [("tracker/authority_bridge.py", "")], "Composer-side order adapter; the Tracker is sole order issuer"),
 "composer/build_executor.py": ("LATER", [], "Composer build execution is counterpart work; Tracker consumes BuildPackage in quant_intake_adapter"),
 "composer/refit_executor.py": ("LATER", [], "Composer refit execution; fit generations are consumed via expression/fit_generation + check_fit_refs"),
 "composer/build_output.py": ("EQ", [("tracker/build_output_check.py", "check_build_output"), ("tracker/build_output_check.py", "section27_status")], "Tracker-side check/report of a SUPPLIED package (producer LATER); s27 33 groups / s28 compared in TRK-STAGE-A-R54-S27-S28-COMPARISON.md"),
 "context/event_identity.py": ("EQ-partial", [("context/decision_context.py", "check_envelope"), ("context/decision_context.py", "domain_for_event")], "event identity key derivation not source-defined beyond the envelope"),
 "context/coverage.py": ("EQ", [("context/news_hub_v2.py", "check_dimensions")], "coverage dimensions"),
 "context/applicability.py": ("EQ-partial", [("context/news_hub_v2.py", "check_dimensions")], "applicability relation to the consumer requirement class is a named source gap"),
 "context/resolver.py": ("EQ", [("context/news_hub_v2.py", "resolve_context"), ("context/news_hub_v2.py", "event_consumable")], "market Event/Context resolver (News Hub V2 9.0/9.2A/9.3); NOT consulted by Composition.deliver"),
 "context/causal_gate.py": ("EQ", [("context/decision_context.py", "as_of_visible"), ("context/news_hub_v2.py", "actual_available_asof")], "as-of visibility"),
 "gateway/dependency_resolution.py": ("EQ-SIMULATED", [("gateway/contracts.py", "DependencyEntry"), ("gateway/contracts.py", "SimulatedGateway")], "resolution is SIMULATED, not a real Gateway"),
 "gateway/non_delivery.py": ("EQ", [("gateway/v038.py", "NonDeliveryResolutionV038"), ("gateway/v038.py", "FinalResolutionStore")], "structured omissions; one final per identity"),
 "gateway/settlement.py": ("EQ", [("gateway/v038.py", "check_settlement"), ("gateway/v038.py", "classify_late")], "delay value D16 unsupplied"),
 "gateway/health_snapshot.py": ("EQ-SIMULATED", [("gateway/contracts.py", "HealthSnapshot")], "Core gateway_health composes it in Composition"),
 "fw/request_adapter.py": ("EQ-partial", [("fw/receiver.py", "receive_verified"), ("fw/outcome_desk.py", "OutcomeSeriesDesk")], "request/return generic; FW payload fields unbound"),
 "fw/input_binding.py": ("EQ-partial", [("fw/descriptor_crosswalk.py", "require_real_binding"), ("fw/descriptor_binding.py", "")], "ten-field bindings undeclared (documentary)"),
 "ml/dataset_binding.py": ("EQ-partial", [("ml/receiver.py", "build_row"), ("ml/consumer_path.py", "MLConsumerPath")], "dataset manifest registry/authority are ML-owned ports (tests only)"),
 "ml/standalone_ancestry.py": ("EQ-partial", [("ml/receiver.py", "check_generation")], "standalone ancestry; closure record consumption absent"),
 "ml/fw_augmented_rebind.py": ("EQ-partial", [("ml/receiver.py", "check_fw_augmented"), ("ml/augmented_desk.py", "AugmentedDesk")], "association HELD until reverse-H1 mapping"),
 "ml/generation_lineage.py": ("EQ-partial", [("ml/generation_lifecycle.py", ""), ("ml/receiver.py", "check_generation")], "writer/finalizer facade is ML-owned"),
 "health/b0_adapter.py": ("EQ", [("health/adapters.py", "")], "B0 evidence adapters; B0_HELD_SLOTS named, none invented"),
 "health/quant_evidence.py": ("EQ", [("health/evidence.py", ""), ("health/adapters.py", "")], "quant evidence observations"),
}
def exists_sym(f, s):
    p = ROOT / "stage_a" / f
    if not p.exists(): return False
    return (not s) or re.search(r"(def|class)\s+" + s + r"\b|^" + s + r"\s*=", p.read_text(), re.M) is not None
def first_doc(p):
    try: return (ast.get_docstring(ast.parse(p.read_text())) or "(no docstring)").split("\n")[0][:140]
    except SyntaxError: return "PARSE ERROR"
print("# R54 E-03 module-map audit (57 paths; NOT a gate; nothing adopted)\n")
print("DERIVATION_CLASS = INDEPENDENTLY_DERIVED. EXACT_INPUTS = Build Plan 1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo, section 'E-03 FINAL REPOSITORY MODULE MAP' (re-read live; the tree lists 57 .py paths) and the current tree. METHOD = compare each path with `stage_a/<path>`; absent paths are mapped by hand to the symbols that implement the responsibility, and this generator FAILS if a named symbol is missing. Filename equality is not closure: 'exists' rows show the module's own first docstring line only; whether the content discharges the E-03 responsibility is the Coder reading in the last column of the manual audit (TRK-STAGE-A-R54-MANUAL-AUDIT.md).\n")
ex = [p for p in PATHS if (ROOT / "stage_a" / p).exists()]; ab = [p for p in PATHS if p not in ex]
print("Result: %d exist, %d absent (R11 had 32/25). Every absent path has a verified mapping or a LATER/counterpart class.\n" % (len(ex), len(ab)))
print("| E-03 path | State | Where the responsibility lives (verified symbols) / first docstring line | Class |\n|---|---|---|---|")
bad = []
for p in PATHS:
    f = ROOT / "stage_a" / p
    if f.exists(): print("| %s | EXISTS | %s | FILE |" % (p, first_doc(f).replace("|", "/"))); continue
    cls, syms, note = M[p]
    for fl, s in syms:
        if not exists_sym(fl, s): bad.append((p, fl, s))
    print("| %s | ABSENT | %s %s| %s |" % (p, "; ".join("%s%s" % (fl, ("::" + s) if s else "") for fl, s in syms) or "none (counterpart)", "- " + note + " ", cls))
if bad: sys.stderr.write("UNVERIFIED MAPPING: %r\n" % bad); sys.exit(2)
