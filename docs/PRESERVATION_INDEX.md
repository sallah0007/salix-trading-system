# SALIX Trading Tracker — Saved Code and Preservation Index

## Current preservation checkpoint — 29 November 2026, Sydney

Latest integrated code: main `c0988a4da74d92f44ad63f42681b12b61b462051`, through [PR #167](https://github.com/sallah0007/salix-trading-system/pull/167). Full Tracker completion/review and Owner sign-off remain pending. Claude follow-ups are paused for the weekly allowance reset; the existing scope and unfinished checklist are retained.

### Verified remote copies

GitHub API returned 158 remote heads on two complete pages (100 + 58). The following full remote SHAs match the latest five branch tips checked in Claude's workspace:

| Remote branch | Exact saved SHA |
| --- | --- |
| `r53-inventory-checklist` | `3246d032d518643efea179109df1b6d3c29eeaf3` |
| `r53-row-l2-maintenance` | `f46dcb5fd6cca37095fd562795e34e276edd9e2b` |
| `r53-row-route-l2` | `152cfb7ae61034280bd8de2a490218071b8fb894` |
| `r53-row-route-lifecycle` | `86505166a632881bb5f3576ee2cc90186fb1188e` |
| `r53-view-freeze-and-row-bridge` | `4ee4124cc76b8bfd3aa8d746e96ffef0929d333e` |

### Workspace evidence and limits

The Manager read the actual post-PR167 command outputs in Trading Bot 7: `git status --short` produced no entries, stash count 0, untracked count 0. The final native ancestry loop compared every local branch tip against all SHAs returned by `git ls-remote --heads origin`; it printed no unreachable branch. Five earlier apparent misses were stale remote-tracking refs: the direct local/remote SHA comparisons were SAME. The remote head count and five full remote SHAs above were separately fetched by the Manager through GitHub.

This establishes recoverability of the observed repository working tree and local branch histories at that checkpoint. It does not certify arbitrary ignored/scratch files, future edits, test semantics, provider qualification or completion. Private governing-source exports remain governed-source material; this index does not authorize copying them into the repository. No branches, stashes or history were deleted.

### Resume and review

Use [the persistent checklist](closeout/TRK-STAGE-A-CHECKLIST.md) first. Remaining work includes the ML view-path remainder, dependency BEFORE/AFTER checks, per-clause review, all 100 A07 comparisons, remaining Build Plan reads, and one current combined closeout. PR167 engineering claims remain author-run/CI evidence pending the Manager's independent review; preservation is not acceptance. The combined closeout's old §28.11 narrative is not proof of review of every later change.

The older checkpoint below and the R08–R24 record are retained as dated history.

## Historical verified GitHub checkpoint — 28 November 2026, Sydney

This is a preservation check, not implementation certification or acceptance. Code reviewed for this checkpoint is `b8017d408c671e96a28fbb1eb25477cfef70d6ee`, through merged PR #83. Documentation-only heading/navigation updates follow that code checkpoint.

| Check | Observed result |
| --- | --- |
| Current integrated branch | `main`; recent PR #82 lifecycle repairs and PR #83 status emitter/caller are merged |
| Latest two PR file preservation | All 11 changed file paths have the same Git blob SHA on the PR heads and the checked main tree |
| Remote branch inventory | 73 heads returned on one complete page of up to 100; older Tracker branches and the preservation anchor are present |
| Earlier local-only commits | All 170 unique SHAs in [the R46 preservation list](PRESERVATION_R46_LOCAL_ONLY_SHAS.tsv) exactly match the 170 direct parents of remote anchor `5ece0b4fc7b0979dc98fc8ada67161500e390269`; no missing or extra SHA |
| Main history continuity | GitHub comparison from R45 code `3cbefb40ff70d7b877732898c91515358eb16479` to the checkpoint is ahead by 13 commits |
| Current runtime source and tests | The checked main Git tree is complete (not truncated); 472 file blobs were inventoried. This is an inventory, not a review of every file |
| Active workspace limits | GitHub alone cannot detect Claude's newer uncommitted, untracked, stashed or unpushed work; a fresh workspace check remains separate |

### Where to start

- [Repository overview](../README.md): component purpose and directory map.
- [Combined closeout](closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md): use the section explicitly labelled CURRENT, then reconcile later commits. At this checkpoint that section is R49; PR #82/#83 are newer code events and are not silently treated as covered by the R49 narrative.
- [Working requirement register](closeout/TRK-STAGE-A-R43-CLAUSE-RECONCILIATION.md): retained filename; evidence and reread limits are stated per row.
- [Original SHA preservation list](PRESERVATION_R46_LOCAL_ONLY_SHAS.tsv): earlier local-only work now reachable through the remote anchor.

Do not merge the preservation anchor into main, delete branches as cleanup, or use branch names as acceptance evidence. The existing provider-harness PR #16 remains open and explicitly marked DO NOT MERGE; this documentation check changes none of its status.

## Historical preservation record — R08 through R24

The following original record is retained for provenance. Its old 'latest', 'next', 'unresolved' and branch-status statements are dated snapshots, not current selections. Later source decisions and code evidence must be read in the combined closeout and GitHub history. No earlier accepted scope is changed.


PRESERVATION IS NOT ACCEPTANCE. A merge or this index clears no gate, hold or stage (CLAUDE.md §2A). Drive is the canonical record.
Historical baseline snapshot: 2026-11-27 after PR #30. The numbered sections below retain earlier observations; they do not describe the latest repository state.

## 1. Merged into main (code/test/evidence; author-only, no independent review)
| PR | Branch (kept on remote) | Tip | Content |
|---|---|---|---|
| #24–#26 | `stage-a/tracker/annex-conformance`, `.../boundaries` | a3cf798, 33672f6 | Annex V1.2 schema layer, boundaries, simulated Gateway/FW/ML, contract objects, A07 package |
| #27 | `stage-a/tracker/consolidated-r03` | 069bdf7 | V0.38 conformance, News Hub/Decision Context validators, 100-qualifier reconciliation |
| #28 | `stage-a/tracker/review-r04` | de427f3 | R04: encoder hardening, Health B0, Q9 slice, §28 coverage, 106 boundary mutants |
| #29 | `stage-a/tracker/consolidated-r05` | 329c2f8 | R05 tests (D14/D15/store controls) and return |
| #30 | `stage-a/tracker/consolidated-r06` | e3dec9d | R06: FinalResolutionStore request-id reservation fix, forced-interleaving controls, §27 coverage map |
| #31 | `stage-a/tracker/preservation-r07` | a1c26c4 | this index + reproducible R05/R06 mutation sweep |
| next | `stage-a/tracker/completion-r08` | see git | R08: E-06 principals, routing names, Health invariants, FW crosswalk, return `coder_returns/TRK-STAGE-A-TRACKER-R08.md` |

## 2. Published on remote, NOT merged into main (candidate/historical; not merged by this checkpoint)
- `stage-a/tracker/full-component` (695199c) and `tracker-component-construction-layer` (2de875e): earlier component drafts by this Coder. Every file path they contain exists on main (checked with `git diff --name-status`); content was NOT diffed line by line, so "superseded" is not claimed.
- Pre-existing branches from earlier sessions, not touched here: `type1/*` (8), `docs/*` (2), `e01-conformance-harness`, `e01/conformance-harness`, `pr6-universal-transition-history`.

## 3. Unresolved (no code can close these; see coder_returns)
D1–D18 and A07-1..4 open items, 100 qualifier dispositions, Composer §27 field gap (27 of 35 absent from BuildPackage), provider/restart qualification, REQUEST_AFTER_CUTOFF trigger, R7 effectiveness. Detail: `coder_returns/TRK-STAGE-A-TRACKER-R08.md` (latest completion package), `-R06.md`, `-R05.md`, `-R04.md`; `docs/a07/`.

## 4. Where things are
| Need | Path |
|---|---|
| Latest return, requirement status, D1–D18 classification | `coder_returns/TRK-STAGE-A-TRACKER-R08.md` (R06: Codex PR#29 closure) |
| Decisions D1–D16 table, 100-qualifier CSV | `docs/a07/A07_CONSOLIDATED_DECISIONS_AND_SOURCE_RECONCILIATION_R03.md`, `docs/a07/V232_26S_QUALIFIER_RECONCILIATION_R02.csv` |
| Requirement/§28 and §27 coverage | `tests/trk_stage_a/test_boundaries.py` (§28), `tests/trk_stage_a/test_composer_s27_coverage.py` (§27) |
| FinalResolutionStore | `stage_a/gateway/v038.py`; tests `tests/trk_stage_a/test_v038_conformance.py`, `test_r05_consolidated.py` |

## 5. Reproduce (Python 3.13, no network)
```
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests -q
python3 -B -m unittest discover -s tests          # does not collect pytest-style tests
python3 -B tests/trk_stage_a/mutation_sweep.py
python3 -B tests/trk_stage_a/mutation_sweep_boundaries.py
python3 -B tests/trk_stage_a/mutation_sweep_r05_r06.py   # R05/R06 manual mutants, now scripted
python3 -B tests/trk_stage_a/mutation_sweep_r08.py       # R08 mutants (14)
python3 -B tests/trk_stage_a/mutation_sweep_r09.py       # R09 mutants (17)
python3 -B tests/trk_stage_a/mutation_sweep_r10.py       # R10 mutants (19)
```
Each sweep restores the mutated file in a `finally` block; run on a clean tree.

## 6. Intentional exclusions (never committed)
Private governing-source exports and Drive text copies (Governance, Connected Contract, Composer, Matrix, Build Plan, MLCore etc.; session scratch under `/home/claude/*`), Governance/Drive-reconstruction scripts (`v09x`–`v103` build/reconstruct scripts: Manager-document work, not repo code), `tracker_component_DRAFT_R01.zip` (earlier draft archive; its files are superseded by branches above, not diffed), `.pytest_cache/`, `__pycache__/`. No credentials were found or staged. Cite sources by ID and range only.

## 7. R09 additions
Code: `stage_a/binding/`, `stage_a/coordination/provider_contract.py`; edits to `stage_a/fw/descriptor_crosswalk.py`, `stage_a/health/envelope.py`, `stage_a/security/principals.py`. Proposals (not authority): `docs/proposals/*.md`. Return: `coder_returns/TRK-STAGE-A-TRACKER-R09.md`.

## 8. R10 additions
`stage_a/composer/request_record.py`; replica role lookup in `stage_a/security/principals.py`; CI `.github/workflows/type1-tests.yml` + `requirements-ci.txt`; corrected `docs/proposals/FW_descriptor_bindings.md`; return `coder_returns/TRK-STAGE-A-TRACKER-R10.md` (supersedes R09 statements on R7 status and FW direction).

## 9. R11 additions
- Code: `composer/expression/{evaluator,opcodes,schema}.py`, `tracker/{quant_intake_adapter,quant_certification}.py`, `tracker/verification/independent_traversal.py`, `tracker/materialization/stateful_materializer.py`, `gateway/v038.py` (BOTH).
- Tests: `test_r11_arithmetic.py`, `test_r11_intake_request.py`, `test_r11_both.py`; sweeps `mutation_sweep_r11.py` (16), `mutation_sweep_r11b.py` (14).
- Docs: `docs/proposals/{E03_responsibility_map,STATUS_EVENT_OWNERSHIP,A02_trace_and_inputs}.md`, `coder_returns/TRK-STAGE-A-TRACKER-R11.md`.

## 10. R12 additions
Code: `gateway/v038.py` (BOTH, consumer-local request keys), `gateway/contracts.py`, `tracker/status_projection.py`, `composer/expression/{ceilings,sqe_opset}.py`, `tracker/quant_intake_adapter.py`, `health/blast_radius.py`, `ml/receiver.py`. Tests `test_r12_*.py`, `test_r11_both.py`; sweeps `mutation_sweep_r11b.py` (17), `mutation_sweep_r12.py` (39). Return `coder_returns/TRK-STAGE-A-TRACKER-R12.md`.

## 11. R13 additions
Code: `tracker/{build_output_check,lifecycle_status_event}.py`, `context/news_hub_v2.py` (R13 section), `fw/return_lineage.py`, `ml/receiver.py`, `health/blast_radius.py`, `tracker/quant_intake_adapter.py`. Tests `test_r13_*.py`; sweep `mutation_sweep_r13.py` (38). Return `coder_returns/TRK-STAGE-A-TRACKER-R13.md`.

## 12. R14 additions
`context/news_hub_v2.py` (causal gate, validated daily record, revision rule), `tests/trk_stage_a/test_r14_event_causality.py`, `mutation_sweep_r14.py` (26 mutants), r13 sweep updated (37). Return `coder_returns/TRK-STAGE-A-TRACKER-R14.md`.

## 13. R15 additions
`docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md` (row-by-row evidence or exact gap; working draft), `tests/trk_stage_a/integration_reach.py` + `test_r15_integration_ledger.py` (import-graph reachability, journal->status-fact gap), news_hub_v2 typed verdict + `consumer_events`, `test_r14_event_causality.py` (+5), `mutation_sweep_r14.py` (31).

## 14. R16 additions
`ml/receiver.py` (transitive ancestry, AugmentedCheck/require_verified, typed AugmentedInput), `tracker/build_output_check.py` (ConformanceEvidence, check_conformance), intake dimension BUILD_CONFORMANCE (policy hash changed), `TrackerPipeline(conformance_source=...)`, `context/decision_context.as_of_visible` hardening. Tests `test_r16_ml_ancestry.py`, `test_r16_conformance_wiring.py`, `test_r12_ml_augmented.py` (rewritten); `mutation_sweep_r16.py` (26). Closeout file renamed to `docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md` (updated in place).

## 15. R17 additions
`composer/request_record.py` (ORDER outcome-access declaration), `tracker/build_output_check.check_conformance` (bound to the order), `tracker/quant_intake_adapter.Admission.unverified` + `pipeline.Outcome.limits` (capability class-structure and s28 labelled unverified), `tracker/feature_lineage.py` (REFERENCE_ONLY). E-01 harness integrated under `tests/provider_conformance/` (test/evidence tooling; PROVIDER_ACCEPTED = NO; one boundary test adapted). Tests `test_r17_feature_lineage.py`, `test_r17_closeout_completeness.py`, `FunctionInvocation` in `test_r15_integration_ledger.py`, `test_r16_conformance_wiring.py` (rewritten); sweeps `mutation_sweep_r17.py` (21), `mutation_sweep_r16.py` (26, anchors updated). Closeout rewritten with TR-01..15, 57 E-03 paths, D1-D18/D12', A07-1..4, ML qualifiers, baseline duties.

## 16. R18 additions
`health/blast_radius.upstream_incomplete` + `fw/lanes.closure_features` (consumer-specific incompleteness; GRAPH_KEY_MISMATCH at the Health closure seam), `ml/receiver.AugmentedInput.support_ref`, `tracker/quant_intake_adapter.{DutyEvidence,unresolved_mandatory,MANDATORY_UNVERIFIED_DUTIES}` and `TrackerPipeline(duty_source=...)` (mandatory duties held before claim/certify/accept), `tracker/version_relationship.py` (REFERENCE_ONLY). Tests `test_r12_blast_radius.py`, `test_r18_mandatory_hold.py`, `test_r18_version_relationship.py`, `BaselineConnectionLimits` in `test_r15_integration_ledger.py`; sweeps `mutation_sweep_r18.py` (39), r12 (36), r16 (26), r17 (21), r13 (37). Closeout gains sections 0A and 4B (core baseline obligations B01-B24) and corrected A07-2 / probe / hash attribution.

## 17. R19/R20 additions
R19 (PR43): `stage_a/tracker/terminal_identity.py`, `ml/receiver.{union_closure,check_standalone,require_standalone_qualified}`, `health/blast_radius.upstream_lineage_defect` (closure probes mandatory), `tracker_component/claims.ClaimService.lineage`, `quant_intake_adapter` s28 duty labels. R20: `stage_a/storage/authority_class.py` (SimulationStore; authority class of store/journal/pipeline/claims; publication, read model and status projection refuse non-QUALIFIED), `pipeline` `CLASSIFICATION_UNRESOLVED_HELD` for qualified no-quant, scoped/deterministic/fact-carrying `terminal_identity`, `docs/proposals/TRK_ENGINEERING_APPENDIX_PROPOSED.md` (PROPOSED design, not a schema), tests `test_r20_*`, `mutation_sweep_r20.py` (38 mutants; supersedes the Health entries of `mutation_sweep_r18.py`). Preservation is not acceptance.

## 18. R21 additions
`stage_a/core/tracker_core.py` (proposed internal ports + one composition path), `gateway/outcome_binding.py`, structural `storage/authority_class.py` (`SimulationStore`), subject-bound `tracker/terminal_identity`, `tracker/version_relationship.classify_not_computed`, `context/news_hub_v2` strict half-open fence, tests `test_r21_*`, `mutation_sweep_r21.py` (31 mutants), appendix and closeout corrections. Preservation is not acceptance.

## 19. R22 additions
Corrected `stage_a/core/tracker_core.py` (held-unless-bound eligibility, stored-fact snapshot members, atomic admission, reconstructability, health validity), `storage/authority_class` exact-type whitelist + `approve_test_adapter`, `ml/receiver.build_row` gateway requirement, `tracker/terminal_identity` era/scope bounds, `tracker/construction_binding.py` (D1, not installed), `docs/a07/A07_R06_V03_RECONCILIATION_PROPOSED_R04.md`, tests `test_r22_*`, `mutation_sweep_r22.py` (33 mutants). Preservation is not acceptance.

## 20. R23 additions
Core corrections in `stage_a/core/tracker_core.py`, typed terminal validity in `tracker/terminal_identity`, D1 held-when-asserted in `tracker/construction_binding.py`, closeout sections 0E/0F/4C, tests `test_r24_core`, `mutation_sweep_r23.py` (22 single + 2 combined). Preservation is not acceptance.

## 21. R24 (candidate; no gate cleared)
Core plane/mode identity, fail-closed safety result type, candidate semantics, composed re-verification (`tracker/reverification`), B02 time-family logic (`core/time_family`), accepted-manifest read-back (`tracker/accepted_manifest`); the combined closeout was rewritten once around the current scope and R17-R23 change summaries moved verbatim to `docs/closeout/TRK-STAGE-A-TRACKER-PROVENANCE-R17-R23.md`. Tests `test_r24_core`, `test_r24_composed`, `test_r24_accepted_readback`; `mutation_sweep_r24.py`. Preservation is not acceptance.
