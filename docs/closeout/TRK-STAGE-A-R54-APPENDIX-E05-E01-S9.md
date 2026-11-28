# R54 appendix — E05 / E01 / S9 source reconciliation (Coder findings; not Manager decisions)

Sources re-read this pass (Drive, read-only): Build Plan 1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo (285,568 chars as rendered; E-05 table block, E01-H1, E09-H1, E05-L1 sections), Master Health V3 1paXK6vPORaZ4QtQo3Vv3f49h7w2oHVt1-McSC2g6Bkk (B0, sections D, F, G), Contract 1neiQsQ9AG-QKdyMgOqJxXE026D0uY___yhfGaTlIJ8Y (H1 conditionals, H2, coverage vocabulary). DERIVATION_CLASS = INDEPENDENTLY_DERIVED for the comparisons below (names and keys compared by script over the fetched text); METHOD = parse the source blocks, compare to code constants; REPRODUCIBLE_BY_MANAGER = YES. Line numbers differ between renderings, so sections are cited by heading, not line.

## E05 (eleven logical tables)
- 11/11 table names present in both `stage_a/storage/e05_index.py` (executable sqlite reference adapter) and `stage_a/ops/read_model.py` (DDL text generator).
- e05_index.py keys/indexes match the source block for every table checked (manifest, fit, pending_row, transition incl. UNIQUE(namespace_id,epoch,sequence), current_status PK(subject_id, materialization_version), consumer_binding, non_delivery, health, event_context, scheduler, replay). The sqlite adapter is a reference adapter, not Postgres proof, and not a missing logical schema.
- read_model.py deviates from the base block by ADDITIONS only (instrument_id/timeframe in the current_status PK and on fit/pending; data_vintage_mode/supersession_ref). These are source-backed: E09-H1 (status/currentness and fit-generation namespaces carry INSTRUMENT_ID and TIMEFRAME unless the ID is schema-defined globally unique over them) and E05-L1 (row/status projections carry DATA_VINTAGE_MODE and supersession lineage).
- **NEWLY DISCOVERED ABSENCE (repaired):** e05_index.py's `stagea_fit_generation_index` lacked instrument_id/timeframe although `fit_generation_ref` is an opaque Ref with no shown global uniqueness. Added both as indexed columns; negative test `test_fit_generation_projection_requires_instrument_and_timeframe` fails on the old definition and passes on the new (proven by reverting the table). current_status keeps PK(subject_id, materialization_version) as in the source block: subject_id already carries the scope, which E09-H1's exception allows; that equivalence is a reviewable claim, not a proof.
- e05_index.py's docstring cites Build Plan "lines 2126-2166"; the Manager's current fetch places the block at 2512-2552. Citation by line is unstable across renderings.

## E01 (object-store CAS journal)
Source selects object-store CAS journal, canonical authority not Postgres, one mutable HEAD per namespace, conditional write on exact prior version, stale epoch rejects, full scan/rebuild; six methods. Provider linearizability/conditional-write/rebuild/stale-fence/unknown-commit qualification stays separate from software-design closure; no cross-HEAD atomicity is inferred (E01-H1 states cross-HEAD atomicity is ELIMINATED for status/currentness). The earlier E-03 audit and the R54 shared-assembly rebuild proof cover the software side; nothing here claims provider qualification.

## S9 Master Health V3 B0
- All 35 B0 field spellings (SUBJECT_IDENTITY with AUTHORITY_STATE + INSTRUMENT_ID counted as three) appear in `stage_a/health` (name presence only; behaviour is covered by the existing envelope tests).
- Enforced and tested: PRODUCER_REPORTED_LOCAL_STATE only (`ML_LOCAL_STATE` refused, SECOND_LOCAL_STATE_FIELD); EVIDENCE_REFS refused as a competing outward field (COMPETING_EVIDENCE_FIELD); EXPECTATION_UNKNOWN distinct from NOT_EXPECTED; silence after validity expiry never HEALTHY.
- **Absence named, not repaired:** there is no deterministic mapper from the ML profile's plural EVIDENCE_REFS to one canonical EVIDENCE_REF. The source requires the mapping but defines no bundle identity/hash rule; building one would invent a byte/identity layout. Today the plural is refused at the outward boundary (fail-closed). Needs a source-owned bundle-identity rule.
- D17 phase: NEWS_CONTEXT_HEALTH_PROFILE_HOME is required before first FW/ML execution and does not by itself block candidate successor promotion. Recommendation for the D17/D18 proposal: a versioned News/Context domain profile referenced by the common Health registry, with the exact owning source, fields and admission stated; no numeric values or default critical set; no promotion claimed. Recovery classes are a versioned reason registry; flapping thresholds/membership remain separately governed policy.

## Gates
None changed. A merge, passing test or this appendix clears no gate; full Tracker NOT complete.

# Preservation inventory (state at origin/main 7157c4fb5c96)
Remote branches (81), tags (0); nothing deleted or cleaned up:
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
