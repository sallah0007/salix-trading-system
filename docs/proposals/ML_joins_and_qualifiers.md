# ML creator/writer/manifest/lineage joins and the 100 qualifiers (PROPOSED)

STATUS: PROPOSAL. Source: Build Plan mapping/dependency disposition (ML_mapping section) and ML Health Profile V2. Nothing here appoints a writer, admits a manifest or awards acceptance.

## Creator / writer
| Item | Governed state | Proposed binding | Missing admission |
|---|---|---|---|
| ML dataset/manifest creator | operation = ML dataset/manifest construction function; exact operation and writer principal/grant NULL in source | Tracker-side: manifest creation request carries `creation_request_id`, `order_id`, manifest id + sha256 | writer principal and grant appointment (D2-class, no principal in E-06 covers ML construction) |
| Writer principal | not among the ten E-06 principals | none proposed to be invented | Manager/Owner appointment or explicit statement that `context-writer` covers it |

## Six joins (source-listed) with proposed Tracker-side validation
| # | Join | Validation implementable now | Missing |
|---|---|---|---|
| 1 | Consumer Binding.MANIFEST_OR_DATASET_BINDING_ID -> provenance manifest | id equality + sha256 shape | manifest registry |
| 2 | manifest features -> Tracker FEATURE_ID/VERSION + graph hash + closure | membership vs supplied catalog snapshot | catalog snapshot instance |
| 3 | Health refs -> bind-time snapshot | single EVIDENCE_REF mapping (plural alias must map to one); ML_LOCAL_STATE refused | Health service |
| 4 | generation manifest -> components | component id set equality | generation registry |
| 5 | lifecycle ledger -> MANIFEST_ID/HASH + epoch | id/hash/epoch triple shape | ledger instance |
| 6 | research-family/exposure -> ledger version/hash/AVAILABLE_ASOF | AVAILABLE_ASOF strictly before fence | exposure ledger |

Manifest classes (source): OFFICIAL_ML_TRAINING_MANIFEST, ML_SIMULATION_MANIFEST, RESEARCH_MANIFEST; modes ML_STANDALONE, ML_FW_AUGMENTED. SIM manifest never counts as REAL. Section 29B recertification: source present; revoked-generation revival and Gateway restore remain open (not invented).

## The 100 ML qualifiers
Status: all 100 remain RAISE_FOR_SOURCE_OWNER_DISPOSITION (hashes 100/100 reproduced, refs 100/100 resolved earlier; 65 cite no current line). Semantic disposition PROPOSALS are prepared only where a source line supports them; none is awarded, none is accepted. Per-qualifier text is not reproduced here (private governing source). Classification for the source owner (R19 correction): (i) 35 qualifiers cite a current line, but a current-line citation proves NO disposition. Codex lexical triage of those 35: 12 weak, 19 partial, 4 strong lexical hints; even the 4 strong are hints, not confirmation. Nothing is proposed as "confirm as stated"; each needs source-owner reading of the cited line against the qualifier. (ii) 65 cite no current line: propose "cite current line or withdraw" for owner review. NL-0187 (V235): the qualifier_comparison (shadow counters) and the display-visibility treatment are inconsistent; this is preserved as a BOUNDED CANDIDATE CORRECTION and the open question whether the qualifier must appear in EVERY display remains OPEN. No frozen source rewrite and no blanket 100-row acceptance. These counts are carried from earlier derivation, not recounted in this pass: The 35 is arithmetic (100 minus 65) on the carried 65 figure; the 65 itself was derived in an earlier pass and is not recounted here (INSUFFICIENT_EVIDENCE for this pass).
