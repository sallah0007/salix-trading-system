# R45 CHALLENGE TO R44_DECISION_PACK (corrections after source reads). PROPOSALS ONLY. Nothing adopted; no gate moves.
Sources opened in R45 (cited by role/ID, no text copied): Typed Schema Annex V1.2 (Drive 13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA) section I + per-object schemas; Parent V1.2 (Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM) SQE_OPSET_V1_1, capability classes, ceilings, section 27 intake lifecycle; Composer V9 sections 27/28; MLCore shadow-live evidence contract; recovered R06 raw (hash-verified) = V240 candidate.
NOT opened in R45 (report accurately): Contract V0.38 H1/H3 (the Drive ID I used was wrong, "Entity not found"; correct document not yet located); BuildPlan sections 11-14/14A/27/29A + R7 overlays (saved locally, not yet read for these sections); V240 ZIP (connector `download_file_content` refuses >10 MB: connector limit, not a content finding); V235 and V232/V230 oracle files for the qualifier adjudication.
DERIVATION_CLASS = INDEPENDENTLY_DERIVED for the reads above; REPRODUCIBLE_BY_MANAGER = YES (document IDs above).

## D3 (corrects R44): the "assign codes in Annex list order from 1" rule is WITHDRAWN as a default
- Finding (framing): the pack presumed list order is the numbering rule. The sources read supply formats (UINT16 enum width, REF_TYPE) but no numbering rule; list order in a document is not a numbering authority, and a later insertion would silently renumber hashes.
- The opcode SET is larger than the repository table: comparisons, bounded SELECT, FIXED_SUM, FIXED_DOT, vector/matrix are admitted; LOG/EXP/POW/transcendentals are NOT admitted. R45 implemented comparisons + lazy SELECT with a boolean TYPE (no 0/1 encoding invented) and the BRANCH ceiling; FIXED_DOT/vector/matrix remain NAMED-UNIMPLEMENTED (no shape typing in any source read).
- Opcode-set equality (declared == extracted) already enforced; canonical ascending-code ordering of OPCODE_SET_USED stays uncheckable without a code table.
- Alternatives: (A) governed table supplied by the source owner function (preferred; stable, additive-only); (B) author-proposed numbering adopted by review with an append-only rule (new codes only at the end, never renumber); (C) list-order rule (rejected: unstable). RPN grammar: SELECT is lazy, so a pure postfix stack with eager operands CANNOT express it without either a block/jump form or a node-DAG form; the manifest here is a node DAG. RPN proposal therefore needs a branch construct and is NOT recommended until the governed grammar is supplied.
- Backward compatibility: any code change regenerates every candidate hash (all labelled candidate).
- Decision needed: supply table + grammar, or approve (B) explicitly. Blocked: normative bytes, D13 hashes.

## D13 (corrects R44): the invented envelope is WITHDRAWN where the Annex already defines bytes
- Annex section I defines canonical byte rules and per-object hash orders. A parallel envelope (domain_tag/version/field_count/...) would CONTRADICT it for any object the Annex covers. Only objects with no Annex schema need a layout decision, and that list must be taken from the Annex per-object schemas, not from the R44 four-object list. ENUM numeric codes remain unassigned by any source read.
- Decision needed: Manager to confirm which objects lack an Annex schema. Until then the repository's candidate codec stays labelled candidate.

## B11 (corrects R44): conflates two lifecycles
- Parent section 27 defines an INTAKE lifecycle mapping; per-MV currentness (the 12-state lifecycle) is a different machine. The R44 single forward-chain with "any state to REJECTED" merges them. Proposal: keep two edge tables; terminal states have no outgoing edge; no revival path without a new identity. Subject-to-MV mapping stays a Manager decision (not invented).

## D8 / D6
- D8 selector: Composer section 27 request classes/target consumers exist in `request_record`; the selector value still must be supplied. DIRECT_TRACKER_FEATURE stays fail-closed.
- D6: field types are shape/membership only; enum codes follow D3's outcome; no change to the R44 adoption-by-review wording except that "source owner" means the responsible function, not a person.

## B04 / B08
- Unchanged from R44 except: B08 similarity detector remains HELD; exact canonical-hash duplicate detection is the only mechanical rule proposed. No threshold is proposed (none is source-supplied).

## Shadow row (corrects R44): read-only row type was too narrow
- The MLCore contract defines idempotency by PREDICTION_EVENT_ID, three outcomes (PUBLISHED, MODEL_ABSTAINED, LIFECYCLE_FENCED), per-logical-event counters, a coverage rate, visible fencing misses and a ban on retroactive backfill. Implemented in R45 as `stage_a/ml/shadow_ledger.py` (exact (published,total) pair; empty = None; no threshold; no sufficiency verdict).
- Still held: the logical-event key field list, window cadence, any coverage threshold.

## V03 reconciliation / readback proposal (A07) - OPEN
Candidate conflicts with settled staffing (Claude authors, Codex Manager/reviewer, no third person). Exact proposal text NOT yet prepared: it requires the Contract V0.38 and V235 reads listed above. No independence or adoption is claimed. V10 needs whole-domain history (not read).
