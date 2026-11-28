> **HISTORY NOTE (R54):** This pack is retained, not deleted. Its B11 (lifecycle edges) is WITHDRAWN (it conflated the intake workflow with the twelve source lifecycle states); its D13 omitted the observation object; its D3 RPN proposal conflicts with the implemented lazy `select`; its shadow row is stale. The current proposals are in `R54_DECISION_PACK.md`. Nothing here is adopted.

# R44 DECISION PACK (ONE pack: D8, D3, D13, B11, D6, B04/B08, shadow row). PROPOSALS ONLY.
STATUS: reviewable Coder proposals under the §2A authoring delegation. NONE is adopted, effective, normative or a gate; existing candidate code labels are RETAINED until a reviewed adoption. "Spec function" = the responsible function, not an appointed person. Sources cited by S-id/range only (S2 BuildPlan, S4 Registry, S5 Parent/Annex, S6 Contract V0.38, S7 Composer V9).
Each item: (a) what exists, (b) PROPOSAL, (c) compatibility consequence in this repository, (d) the exact decision needed, (e) what stays blocked meanwhile.

## D8 / TR-06: route selector
(a) `composer/request_classification.route_from_adapter` maps adapter classes QUANT_FEATURE -> COMPOSER_BUILT_QUANT_FEATURE, NO_QUANT_FEATURE -> NO_QUANT_FEATURE; FAILED_REQUESTED_BUILD refuses (TR-06); DIRECT_TRACKER_FEATURE has NO producer. Existing source-backed inputs: `quant_feature_requested` and `manifest is not None` (adapter.admit), request_record `REQUEST_CLASS` (GOVERNED_INTAKE_REQUEST | STREAM_B_EXPLORATION_REQUEST), `TARGET_CONSUMER`, requested REQUIRED/OPTIONAL/absent dependency semantics (S4 p320).
(b) PROPOSED table (first match wins; every other combination refuses `ROUTE_COMBINATION_UNSUPPORTED`):
| quant_feature_requested | admitted manifest | selector for a Tracker-native feature | route |
|---|---|---|---|
| no | none | - | NO_QUANT_FEATURE (unchanged) |
| no | present | - | refuse (unchanged: MANIFEST_SUPPLIED_FOR_NO_QUANT_REQUEST) |
| yes | present, admitted | - | COMPOSER_BUILT_QUANT_FEATURE (unchanged) |
| yes | build failed | - | refuse FAILED_BUILD_NOT_ROUTABLE; NEVER the baseline (unchanged) |
| yes | none | request names an existing governed feature id+version already in the registry and no build is requested | DIRECT_TRACKER_FEATURE (NEW; the single new discriminator = "request references an existing registry feature and carries no builder/manifest") |
(c) Consequence: only the last row is new; it needs the registry lookup port (exists: registry_gate). Failed-build != baseline is preserved because a failed build row never reaches the last row (manifest absent AND build not requested are both required).
(d) Decision: confirm or replace the DIRECT_TRACKER_FEATURE selector ("existing registry reference, no builder/manifest"). (e) Blocked: any code path returning DIRECT_TRACKER_FEATURE stays unbuilt (fail-closed UNKNOWN_CLASSIFICATION).

## D3: numeric ENUM / REF_TYPE / opcode tables and program grammar
(a) Formats ARE supplied (S2 s6.2/6.3, S5 SQE_OPSET_V1_1, Annex I); numeric assignments and the program grammar are not. `schema/candidate_code_tables` holds author-proposed numbering (labelled candidate).
(b) PROPOSAL: adopt the candidate numbering by REVIEW, not by default, using a single rule: codes are assigned in the declaration order of the Annex lists, starting at 1, 0 = reserved/UNKNOWN (refused). Grammar proposal: postfix (RPN) program = sequence of (opcode, operand-count-implied-by-opcode) with the operand stack validated for exact arity and a single result; no jumps/loops (matches "no future-reading operator").
(c) Consequence: hashes computed today change if any code changes; every candidate hash is already labelled candidate, so adoption = one regeneration + test fixture update. (d) Decision: approve the order rule + RPN grammar or supply the governed tables. (e) Blocked: normative bytes, D13 hashes, TR-01/03/04 normative claims.

## D13: per-object wire layouts (FINAL_RESOLUTION, PACKAGE, Event, Context)
(a) Durable record encoding is a CANDIDATE (`durable_final_store` codec); EventContext store runs on a SUPPLIED encoding interface (R43). (b) PROPOSAL: one deterministic envelope for all four: `domain_tag | version(u16) | field_count(u16) | (field_id(u16), type_tag(u8), length(u32), bytes)*` fields sorted by field_id, no optional-by-omission (explicit NONE tag), integers big-endian, text UTF-8 NFC, hash = sha256(domain_tag || canonical bytes). Field ids follow the existing dataclass field order. (c) Consequence: replaces JSON candidate encodings behind the existing encode/decode interface (no caller change); hashes change once. (d) Decision: approve the envelope or supply layouts. (e) Blocked: the E05 event-context source stays HELD without the interface; PACKAGE normative hash.

## B11: lifecycle transition edge matrix and subject->MV mapping
(a) 12 states + intake path exist (S4 p223-233; framework takes a supplied policy). (b) PROPOSAL edges: strictly the listed forward order, one step at a time: NEW_CANDIDATE>SAFE_INTAKE>EXPERIMENTAL_UNCLASSIFIED>ADMISSIBILITY>FEATURE_IDENTIFICATION>CLASSIFICATION>CERTIFICATION_ELIGIBILITY>MATERIALIZATION>CONTINUOUS_RECORDING_VERIFICATION>HEALTH_AI_CHALLENGE; from ANY non-terminal state -> REJECTED | RETIRED | DISCARDED (terminal identity still returned, S4 F118); no re-entry from terminal; no skipping. Subject->MV mapping proposal: one MV (materialization version) per (feature_id, feature_version) subject, 1:1, recorded at CERTIFICATION_ELIGIBILITY. (c) Consequence: `LifecyclePolicy` instance only (no code change); PUBLISHABLE=>CURRENT and SIM->QUALIFIED mappings are NOT proposed (not invented). (d) Decision: approve edges and 1:1 MV mapping. (e) Blocked: B11/B13 mapping use; any edge not listed refuses.

## D6: Composer s27 field types
(a) `docs/proposals/D6_composer_s27_mapping.md` already proposes all 27 attributes with Tracker-side validation. (b) PROPOSAL: adopt its types as written (text/enum/(id,sha256) refs/tuples); enum numbering follows D3. (c) Consequence: validation is shape/membership only until D3/D13. (d) Decision: Composer source owner function confirms the 27 types. (e) Blocked: enforcement beyond shape; TR-05 normative.

## B04 / B08: discriminator battery and similarity detector
(b) PROPOSAL B04: closed field-set typing = the REQUIRED_IDENTITY_FIELDS tuple in `quant_intake_adapter` plus exact-type checks; discriminator battery = one positive and one negative fixture per field (missing, wrong type, extra field, duplicate). B08: similarity detector HELD; proposal = exact-equality on canonical formula hash first (duplicate), semantic similarity (correlation of outputs on a fixed fixture window) only as an advisory flag that can never promote. (c) Consequence: B08 detector would add an advisory column only. (d) Decision: approve the battery content owner and whether advisory similarity is wanted. (e) Blocked: any claim that similarity is detected.

## Shadow row (MLCore p323/p324 only)
(a) The shadow-row contract is bound only at MLCore p323/p324 and stays unbound. (b) PROPOSAL: model it as a read-only ML-side row type carrying (row_id, generation_ref, dataset_manifest_id, reverse-H1 binding id, reason) and refuse any Tracker write of it. (c) Consequence: none on existing code; `ml/consumer_path` already refuses to qualify. (d) Decision: ML source owner function confirms field set. (e) Blocked: shadow-row writer.

## What this pack does NOT do
It adopts nothing, assigns no principal, provider, calendar, threshold or ceiling, and does not change any candidate label. A merge of this file clears no gate.
