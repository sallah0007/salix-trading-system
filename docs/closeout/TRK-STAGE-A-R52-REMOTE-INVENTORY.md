# R52 exact recoverable GitHub inventory (nothing deleted, no tags created or changed, no cleanup)

Repository sallah0007/salix-trading-system. origin/main = 9b62170692a94b38b772ae2e86ae4b7c06b38c1f at the time of writing. Derivation: `git fetch --prune`, `git branch -r`, GitHub REST `pulls?state=closed` (GraphQL is unavailable from this session). REPRODUCIBLE_BY_MANAGER = YES.

## Merged pull requests this segment (number, merge commit, PR head, title)
| PR | merge commit | head | title |
|---|---|---|---|
| 111 | 9b62170692a9 | c3618f5f2204 | R52: News Hub daily-record required items; source reads; ancestry proposal; AFTER recheck |
| 110 | 6674ded3bafd | a709559dafdd | R52: FW ten-field real-binding declaration review |
| 109 | 012935047cfb | 42d8ceb91487 | R52: A07 100-row proposed disposition record (no awards) |
| 108 | 0bde55132332 | f343acc96443 | R54: E05 fit projection instrument/timeframe; E05/E01/S9 appendix; preservation inventory |
| 107 | 7157c4fb5c96 | 9d57423834ee | R54: H1/H2 COVERAGE_BASIS scope reconciliation |
| 106 | c6ae854a1a3a | fbaae650431a | R54: H1 conditional groups enforced (S6 re-read) |
| 105 | 2cad5d0f3650 | 59c081eb3780 | R54: manual audit of 62 rows, E-03 audit (57 paths), pack s4.1 open question |
| 104 | e5fcd228c26e | 59f3d122b970 | R54: s27/s28 33-group comparison, ancestry/OIA report fixes, fw_association accessor |
| 103 | c6689b3ee8de | 6f767b6f1914 | R54: closeout resume update (docs only) |
| 102 | e3786d4d5858 | 6f21894dd6e9 | R54: shared-assembly E05 rebuild, outcome desk hook, wiring audit, readback |
| 101 | 79506d73638a | c7df177444d1 | R54: closeout 28.5 + stale row pointers (docs/tools only) |
| 100 | b0e8ab421699 | 26ab0c31839f | R54: ONE decision pack (PROPOSED), D10/TR-14 clause re-audit |
| 99 | 3d1d3ac74983 | 448873b3f6fe | R54: observation-to-snapshot adapter over the Core's own receipts |
| 98 | 03b393bf4782 | 067cba077104 | R54: owning-subject correlation and cold recovery of the real assembly |

Code PRs (#106-#108, #110, #111) merged only after every check run on the exact head was completed:success; #109 changed tests/docs/tools and also ran CI; this inventory PR is docs-only (no PR CI triggered; merged by REST with the head SHA).

## Remote branches (81)
- origin/docs/claude-operating-standard-align-canonical8
- origin/docs/restore-owner-relay-communication
- origin/e01-conformance-harness
- origin/e01/conformance-harness
- origin/main
- origin/pr6-universal-transition-history
- origin/preserve/r46-local-only-anchor
- origin/preserve/r50-local-only-anchor
- origin/r50-closeout-28
- origin/r50-composition-emitter
- origin/r50-h1-augmented
- origin/r50-lifecycle-races
- origin/r50-shadow-caller
- origin/r50-status-emitter
- origin/r51-handoff
- origin/r51-mlcore-source
- origin/r51-races
- origin/stage-a/tracker/a07-r47-members
- origin/stage-a/tracker/annex-conformance
- origin/stage-a/tracker/boundaries
- origin/stage-a/tracker/closeout-r10
- origin/stage-a/tracker/closeout-r48
- origin/stage-a/tracker/completion-r08
- origin/stage-a/tracker/completion-r09
- origin/stage-a/tracker/consolidated-r03
- origin/stage-a/tracker/consolidated-r05
- origin/stage-a/tracker/consolidated-r06
- origin/stage-a/tracker/continue-r11
- origin/stage-a/tracker/continue-r12
- origin/stage-a/tracker/continue-r13
- origin/stage-a/tracker/continue-r14
- origin/stage-a/tracker/full-component
- origin/stage-a/tracker/full-pass-r15
- origin/stage-a/tracker/preservation-r07
- origin/stage-a/tracker/r48b
- origin/stage-a/tracker/r49
- origin/stage-a/tracker/r49b
- origin/stage-a/tracker/r49c
- origin/stage-a/tracker/repair-r16
- origin/stage-a/tracker/repair-r17
- origin/stage-a/tracker/repair-r18
- origin/stage-a/tracker/repair-r19
- origin/stage-a/tracker/repair-r20
- origin/stage-a/tracker/repair-r21
- origin/stage-a/tracker/repair-r22
- origin/stage-a/tracker/repair-r23
- origin/stage-a/tracker/repair-r24
- origin/stage-a/tracker/repair-r25
- origin/stage-a/tracker/repair-r26
- origin/stage-a/tracker/repair-r27
- origin/stage-a/tracker/repair-r29
- origin/stage-a/tracker/repair-r30
- origin/stage-a/tracker/repair-r31
- origin/stage-a/tracker/repair-r32
- origin/stage-a/tracker/repair-r33
- origin/stage-a/tracker/repair-r34
- origin/stage-a/tracker/repair-r35
- origin/stage-a/tracker/repair-r36
- origin/stage-a/tracker/repair-r37
- origin/stage-a/tracker/repair-r38
- origin/stage-a/tracker/repair-r39
- origin/stage-a/tracker/repair-r40
- origin/stage-a/tracker/repair-r41
- origin/stage-a/tracker/repair-r42
- origin/stage-a/tracker/repair-r43
- origin/stage-a/tracker/repair-r44
- origin/stage-a/tracker/repair-r45
- origin/stage-a/tracker/repair-r46
- origin/stage-a/tracker/repair-r46b
- origin/stage-a/tracker/repair-r46c
- origin/stage-a/tracker/repair-r47
- origin/stage-a/tracker/review-r04
- origin/tracker-component-construction-layer
- origin/type1/clean-era1-boundary
- origin/type1/cross-instrument-construction-gate
- origin/type1/identity-content-import
- origin/type1/post-admission-identity-gate-hardening
- origin/type1/pre-id-content-identity
- origin/type1/source-class-disposition
- origin/type1/tracker-identity-surface
- origin/type1/validation-scope-hardening

Preservation anchors recorded earlier remain (see the combined closeout section 28 and `docs/PRESERVATION_R46_LOCAL_ONLY_SHAS.tsv`). A merge, a passing test or this inventory is a code/record event, not a governance event.
