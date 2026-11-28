# R52 Build Plan reread — batch 5 (capture lines 3885–4260 read in full: §18–§27 start; test families Q/G/F/M/OB)

DERIVATION_CLASS = INDEPENDENTLY_DERIVED (reading, test bodies read where marked BODY, mutants run where marked MUT). EXACT_INPUTS = /tmp `buildplan.txt` 3885–4260, repo main a73fa79 + this PR. METHOD = per family: named test, whether its body was read, whether it can fail. REPRODUCIBLE_BY_MANAGER = YES. A test NAME that states a family is NOT treated as closure; "name only" is marked.

## §18–§19, §24–§26 (duties)
- §18 replay pins manifest/program/fit/origin/input/binding/Health/applicability/research/operator/impl identities; historical replay never substitutes latest; corrected assessment separate from as-known. Code: `replay.py`, `currentness.py` (AS_KNOWN vs EVENTUAL), tests `test_boundaries.test_catching_up_where_current_required_and_vintage_mismatch`, Q23 below. Limit: pin list not enumerated field by field (open).
- §18A oracle provenance: golden/oracle bytes must not come from the implementation under test. Code: `schema/independent.py` is a separate implementation compared to the producer; hand-pinned vectors in `test_schema_annex.test_primitives_golden`. Limit: provenance statement per vector not recorded (open).
- §19 harness capabilities (positive oracle, negative control, mutation injection, race, cold rebuild, restart, stale cache, wrong instrument/version/schema, hash corruption, program/operator mutation, revocation race, unknown commit, split brain/stale epoch, late dependency, Health staleness, baseline contamination, confluence leakage, FW→ML bypass, profile-name dispatch): present in the suite as separate tests and `tests/trk_stage_a/mutation_sweep_*.py` scripts (not part of CI pytest); a per-capability list is not enumerated here (open).
- §24.1 capability split (materializer cannot write acceptance/status/binding; separate write roles; no combined principal) : `security/principals.py` (`check_no_prohibited_merge`), `test_r10_replica_roles`. Actual principals unbound (held).
- §25 audit evidence per authority transition: `observability.py`, `ops/jsonlog.py`; logs are non-authoritative by design.
- §26 build sequence A–H is a plan order, not a code clause; "no later phase may silently repair missing fields" = fail-closed default.

## Test families
| Family | Closest test (file::name) | Read | Can fail / limit |
|---|---|---|---|
| Q1 permutation invariance, Q2 duplicate keyed | `test_r38_tr_dod::test_tr03_permutation_invariance_over_every_declaration_order_and_duplicates_rejected` | name only | not re-mutated here |
| Q3 opcode extraction, Q4 under/over-declared, Q5 emulation | `test_r38_tr_dod::test_tr09_exact_opcode_and_capability_equality_and_the_firewall`; `test_pipeline::test_capability_declaration_mismatch`; `test_r12_ceilings::test_opcode_set_must_equal_program_and_have_no_duplicates`; `test_expression::test_provider_missing_capability_refused` | name only | emulation (a program emulating an unavailable capability class) has no test whose name says so: UNCONFIRMED |
| Q6 golden vectors bit-exact two evaluators | `test_r11_arithmetic::test_independent_table_equals_composer_table`; `test_verifier_independence::test_independent_encoder_agrees_with_composer_bytes` | name only | two independent evaluators exist; vector provenance not recorded |
| Q7 materializer arithmetic mutant caught, Q8 verifier mutant caught by oracle | `test_r11_arithmetic::test_materializer_claiming_values_where_reference_refuses_fails`; `test_pipeline::test_materializer_encoding_defect_caught`; hash-composition mutants (batch 3, PR #132) | partly MUT | Q8 (verifier-only defect) has no test by name: UNCONFIRMED |
| Q9 new fit generation | `test_boundaries::test_q9_new_fit_generation_changes_row_and_delivered_identity_but_not_manifest_hash` | name only | |
| Q10 stale fit blocks | `test_pipeline::test_stale_and_unknown_fit_generation`; `test_r54_ancestry::test_stale_fit_ref_fails_fit_ancestry_even_with_good_closure` | name only | |
| Q11/Q12 baseline unaffected, verifier failure leaves unrelated consumers | `test_r42_consumer_path::test_unknown_ancestry_is_denied_and_the_unrelated_baseline_is_delivered_to_both...`; `test_r36_composed_window_path::test_same_path_required_unknown_ancestry_fails_closed_unrelated_baseline_delivers...`; `test_boundaries::test_ob2_...` | BODY (ob2) | covers ancestry/HALTED lane, not literally "verifier failure" (Q12): partial |
| Q13 confluence only when explicitly requested | `test_boundaries::test_lanes_and_closure` | name only | UNCONFIRMED |
| Q14 hidden quant ancestor rejected, M3 removed-present-day dependency | `test_r54_ancestry`, `test_r34_consumption_claim` | name only | |
| Q15 no model-name dispatch | `test_expression::test_no_model_name_dispatch_in_evaluator_source` | name only | static source check; evaluator only |
| Q16 correlated replay storm | `test_boundaries::test_replay_storm_does_not_starve_unrelated_head`, `test_priority_classes_live_heads_never_behind_replay_storm` | name only | |
| Q17 Health evidence-only | `test_boundaries::test_health_is_evidence_only_and_objects_validate` | name only | |
| Q18/Q19/Q20 no direct Composer/Health→FW/ML path | `test_boundaries::test_direct_paths_do_not_exist_q18_q19_q20` | BODY + MUT | DEFECT FOUND AND FIXED (below). Static import graph only; the positive "quant output reaches FW/ML only through Tracker→Gateway" has no behavioural test of its own |
| Q21/Q22/Q23 speculation depth, chain state machine, query modes | `test_boundaries::test_speculation_depth_rules`, `test_halted_terminal_and_correction_monotone`, `test_catching_up_where_current_required_and_vintage_mismatch`; `currentness.py` modes | name only | |
| G1+OB1, G2, G3+G9, G4+G5, G6, G7, G8 | `test_boundaries::test_g1_...` through `test_g8_...` | BODY for G4/G5/G6/G7/G8 | G5 asserts the stored outcome object is returned after a later arrival (identity in memory); the durable-store version is in `durable_final_store` tests (not re-read) |
| OB2 | `test_boundaries::test_ob2_failed_quant_lane_does_not_block_unrelated_binding` | BODY | HALTED bad lane vs CURRENT good lane; a real verifier failure is not the trigger |
| F1–F6, M1–M4 | `test_boundaries::test_fw_*`, `test_lanes_and_closure`, `test_ml_row_negatives_and_explicit_exclusion`, `test_ml_generation_checks_and_augmented` and the R50/R54 ML tests | name only | |

## DEFECT (found by mutation, fixed in this PR): Q18/Q19/Q20 could be bypassed
The import scanner recorded only `ImportFrom.module`; `from .. import composer` has no module, so FW receiver importing Composer passed the test. Mutant: append `from .. import composer` to `stage_a/fw/receiver.py` => test PASSED (survived). Fix: the scanner now includes alias names (`..composer`), and a dynamic import (`importlib.import_module`, `__import__`) is recorded as `<dynamic-import>` and fails the check (fail closed; a static graph cannot follow it). New self-test `test_q18_import_scanner_sees_alias_form_relative_imports_and_dynamic_imports`; both bypass mutants now fail the Q18 test. Limits that remain: `getattr`-style indirection and `exec` are not scanned; the check is structural only.

## Lenses
MATHEMATICAL=NA; DATA_SCIENCE=YES (Q11/Q14/M-family leakage mapped, not re-attacked); SOFTWARE_ARCHITECTURE=YES; ADVERSARIAL=YES (import-bypass found); TRADING_MICROSTRUCTURE=YES (G1/G2/G7 fence/visibility mapped); GOVERNANCE=YES; FALSIFICATION=YES for Q18-20 only.

## Still unread in the capture
Lines 140–2230 (heading-scanned only), 2440–2960, 3232–3335, 4260–5234 (the rest of the §27 traceability matrix and the closing status text).
