# Tracker Stage A — persistent work checklist (Coder; code state only, governance state lives in Drive)
A fixed finding or merged PR does NOT mark the larger task complete. Holds unchanged: A02 Class B HOLD; A07/COVERAGE OPEN; A07/P12/N2 UNSATISFIED; QC34 ALERT(HOLD); A08 READY_TO_CODE NO; Stage A HOLD; all 100 A07 qualifiers UR/QUALIFIED false; full Tracker NOT complete; no Sallah sign-off. No gate cleared by any merge/CI.
Main at last update: a79158e (#151 invariant stage, #152 row publication, #153 route delivery tests, invariant-identity fix merged). Full suite 2106 passed.

| # | Task | Status | Evidence / branch / resume point |
|---|---|---|---|
| 1 | Supplied-profile row runtime: StateRowBuilder/CommittedRowChain -> independent verifier -> invariant stage -> epoch-fenced RowAcceptor | PARTIAL (merged #139-#146, #150, #151, invariant identity) | profile math/codec/clock/commit-point rule HELD (SIM only) |
| 2 | journaled status/currentness for rows | PARTIAL | RowPublication -> SIM_STATUS_FACT merged; no per-row A1 event (vocabulary gap); status token mapping HELD |
| 3 | E05 rebuild over per-row records | PARTIAL-> tested | #147 sources + new route test: E05 rebuild over row namespace + durable FW/ML final resolutions on the per-row route, drift refused. SIM status side records (SIM_STATUS_FACT) have NO E05 table in the plan list (not invented) |
| 4 | Core/Gateway + BOTH FW/ML for per-row route | PARTIAL | tests merged (test_r53_row_route_delivery, SIM-merged code tables; admitted table = source-owner input). Needs: first-class Composition per-row publish method (currently reuses recover_publication), restart/cold recovery of row route, separated-worker route for rows (#149 is feature-VERSION only), exact source/manifest/version/row/currentness/consumer evidence |
| 5 | Invariant port identity (PR151 review) | FIXED, merged | reported identity only; artifact-hash recomputation needs a bound codec input (HELD) |
| 6 | ML Registry §14 p337-349 thirteen duties + orchestration | PENDING (not started this stretch) | |
| 7 | All-segment stored SOURCEVALUE L2 / triggers / maintenance / snapshot minima / per-TF vintage / quarantine / restoration / planes / restart / read-model, for the per-row route | PENDING | feature-version route exists (test_r53_real_assembly_base) |
| 8 | Before/after Composer 27/28 + seven-field; FW 10-field/H3 distinct CBID manifest binding / request-return; Health/source dependencies | PENDING | |
| 9 | Per-clause E03/TR/B01-24/D1-18/D12'/A07 review | PENDING | tools/r54_*_audit.py regenerated after test additions |
| 10 | All 100 A07 qualifier/current-oracle comparisons (/tmp/r47a) | PENDING; all stay UR, no awards | |
| 11 | Build Plan lines 140-2230 clause-by-clause read | PENDING (2440-2960, 3232-3335 done) | |
| 12 | ONE CURRENT combined closeout (source/callpath/commit/positive+negative/review limit or irreducible input/source-owner ROLE/consequence/recommendation) | PENDING | TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md §28.11 is the last |
| 13 | Refreshed fetch + untracked/stash/local-only inventory (no cleanup) | PENDING | last: 135 tracking refs, 0 stashes, 0 untracked, none unreachable |

Cold restart of the row route: tested (this PR). Next resume point: item 4 remainder (Composition per-row publish method, separated-worker rows), then item 6 (ML Registry §14), then 6-13 in order. Preserve all branches/WIP; no cleanup.
