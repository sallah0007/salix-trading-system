# TRK-STAGE-A-TRACKER-R14 - Coder return: Codex-reproduced causal-time defect in the News Hub resolver

CODER FINDING != SALIX DECISION. Local resolver defect only; no claim about live trading. Code event; clears no gate/hold/acceptance (A07/A02 unchanged). Authority: CLAUDE.md section 2A, this repository only; Drive read-only. Independent review still required. The Tracker is NOT complete; the full assignment continues. No private governing-source text is copied here: sources are cited by ID and section and paraphrased.

## Finding (Codex, accepted; I reproduced it)
R13 `resolve_context('REQUIRED', daily, [ev], 100)` returned USABLE for an event whose PUBLICLY_AVAILABLE_AT = SALIX_RECEIVED_AT = AVAILABLE_ASOF = 200 > cutoff 100, because `event_consumable` checked only REVISION_AVAILABLE_AT and ACTUAL_AVAILABLE_ASOF. Also `resolve_context` never called `check_daily_record` (it indexed the daily record directly and accepted an incomplete or malformed one) and compared unvalidated timestamps. I withdraw my R13 statement that the resolver applied the document's causal rules in full.

## Source clauses relied on (opened this turn: News Hub V2 Drive 1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw; frozen raw DOCX 15mPi14mG5MAOerZTnhbWfWXwcOIpzWsA) - by section, paraphrased
- News Hub V2 9.0 causal / anti-look-ahead rules: ACTUAL needs both stamps and ACTUAL_AVAILABLE_ASOF <= cutoff; a revised value needs its revision-availability evidence <= cutoff; PUBLICLY_AVAILABLE_AT and SALIX_RECEIVED_AT are distinct and a publicly-earlier fact is not backfilled into an earlier SALIX state; a single generic timestamp is insufficient. 9.0 conditional list and legacy body: consensus/previous carry their own as-of stamps and values are absent before them.
- News Hub V2 9.2A semantics: no join before ISSUED_AT; a missing daily record is UNKNOWN, never a quiet-day inference; late information creates a correcting record.
- Frozen DOCX section 7A (resolver determinism/ambiguity control): with several causally valid non-equivalent candidates and no governed deterministic rule, return MULTIPLE_CANDIDATES / REQUIRE_EXPLICIT_SELECTION.

## Correction (stage_a/context/news_hub_v2.py)
1. `event_consumable` withholds unless EVERY stamp is a verified integer <= cutoff: REVISION_AVAILABLE_AT, PUBLICLY_AVAILABLE_AT, SALIX_RECEIVED_AT, AVAILABLE_ASOF (and ACTUAL_AVAILABLE_ASOF if ACTUAL present); it validates the record itself. Fail-closed DERIVATIONS, not source formulas, labelled in code: AVAILABLE_ASOF < max(PUBLIC, RECEIPT) is withheld; consensus/previous present without their own stamp is withheld.
2. `check_event_record`/`check_daily_record`: bool/str/float/None stamps, non-mapping records and a bad cutoff refuse (EVENT_TIMESTAMP_MALFORMED, DAILY_TIMESTAMP_MALFORMED, CUTOFF_MALFORMED, ...).
3. `resolve_context` now calls `check_daily_record`; a daily record missing required fields is refused. Derived fail-closed rule: NO_EVENT_RECORDED + a consumable event => refuse (DAILY_PRESENCE_CONTRADICTS_EVENTS); a future event does not contradict.
4. Revision-tie assumption inspected: "highest REVISION_SEQ wins" is NOT in News Hub V2 and is not a governed rule; only the MULTIPLE_CANDIDATES fallback is source-backed (frozen 7A, read directly). Default is now MULTIPLE_CANDIDATES for distinct payloads; selection only when the caller supplies a governed rule identity implemented here (`HIGHEST_REVISION_SEQ`), disclosed in `selection_rule`. Same-payload duplicates collapse. Source conformance of that rule is NOT claimed.
Preserved: News Hub `<=` cutoff wording for this resolver only (equality consumable, tested); the Gateway strict fence rule is untouched.

## Evidence (INDEPENDENTLY_DERIVED; reproducible by Manager)
Codex inputs reproduced and covered by `tests/trk_stage_a/test_r14_event_causality.py` (each stamp, boundary equality, malformed types for every stamp, daily-record validation for every required field, rule/tie behaviour). Suite 769 passed locally. Sweeps: r14 26 mutants and r13 37 mutants, all killed (survivors found were killed by added tests; 3 r13 mutants re-pointed because source lines moved).

## Named gaps (no source decision invented; responsible: Manager / News Hub owner)
Governed revision-selection rule ref/version; GOVERNED_DAY/SCOPE-to-cutoff binding; SCHEDULE_VINTAGE availability evidence; daily-record class vs consumer requirement; SUPERSEDES_REF format; general AVAILABLE_ASOF derivation formula; COVERAGE_BASIS key structure (unchanged). The resolver is not wired to a real News Hub ingestion path.
