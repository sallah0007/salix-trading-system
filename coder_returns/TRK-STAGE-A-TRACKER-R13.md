# TRK-STAGE-A-TRACKER-R13 - Coder return (full Tracker assignment continues)

CODER FINDING != SALIX DECISION. Code events only; no gate/hold/acceptance cleared; review pending. No principal/provider/host/grant appointed; no SALIX AI, Engine/Stage B or live action. Authority: CLAUDE.md section 2A (this repository only); Drive read-only.

## Source recovery used (current sources first)
Composer V9 (1aMYAmh5i7ogdQ0vIInPKki3lCSV4Nwotx48zllZhfVw) s27/s28/38.2; Decision Context V4 (1dwGRh2EOxzhQGwV6x6TS4K5FFTu3_TJaES4R4BpW-PQ) A0/A1/H; News Hub V2 (1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw) 1-6, 9.0, 9.2A, 9.3; current Build Plan (1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo) 11-14A. I withdraw the R12 statement that section 27/28 and the status-event/context schemas were missing: they are recovered.

## Rows actioned (code / call path / evidence)
1. Section 27 build-output contract: `tracker/build_output_check.py`; call path `quant_intake_adapter.admit` -> dimension BUILD_OUTPUT_CONTRACT (new BuildPackage.build_output, bound into the package hash). Enforced: immutable-evidence rule (never carries Gateway/registry identities), ORDER_ID and CREATION_REQUEST_ID equal the governed order/request (sole Tracker order authority), learned-derived (derived from the verified manifest's fit_refs, not from the package) requires UPSTREAM_MODEL_ID, UPSTREAM_GENERATION_ID and generation authority class, FORBIDDEN outcome access, dangling inputs, recomputation mismatch / governed-reason rule. No prose-only field name invented; conditional fields stay conditional. Section 28 report already carries the 23 groups (`tracker_component/report.py`).
2. Status event: `tracker/lifecycle_status_event.py` maps a committed lifecycle record to A1; exact residual mismatch listed in STATUS_EVENT_OWNERSHIP.md R13. Combined with R12 `StatusProjection` (consumer authority only from committed journal).
3. Market context resolver: `context/news_hub_v2.py` (`check_event_record`, `check_daily_record`, `resolve_context`): NO_EVENT_RECORDED needs COMPLETE basis, PARTIAL non-exhaustive, OPTIONAL needs policy ref, NOT_REQUESTED != UNAVAILABLE, ACTUAL_AVAILABLE_ASOF = max(public, receipt), no join before ISSUED_AT, revision selection with explicit MULTIPLE_CANDIDATES. Gateway strict < fence untouched.
4. FW return / ML lineage: `fw/return_lineage.py`; `AugmentedInput` now requires FW generation identity and research exposure (Build Plan 13.2); no real counterpart integration claimed.
5. Blast radius: `health/blast_radius.consumer_use` (undetermined + required -> refuse; proven independent allowed; undetermined non-required: named gap).
6. D13-D18 and A02 traces: docs/proposals/A02_trace_and_inputs.md R13 table.
Evidence: DERIVATION_CLASS INDEPENDENTLY_DERIVED; suite 750 passed (locally; reused earlier green evidence for unchanged scope); targeted sweep r13: 38 mutants, 1 survivor killed by an added intake test (verified), others killed. REPRODUCIBLE_BY_MANAGER = YES.

## Exact remaining (source-owner, blocks)
COVERAGE_BASIS key names; News Hub ingestion IO glue (News Hub component); FW return payload fields; status-origin principal and record-kind mapping; package hash bytes (D13); reason->status list (D15); settlement duration (D16); Health profile registry (D17/D18); numeric opcode/program grammar/CASE/state-count/class-compat; provider/host/grants. Reference-only helpers are labelled as such: none of the Gateway/FW/ML/Health connections is REAL.
