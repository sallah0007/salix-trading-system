# A07 R47: per-qualifier reconciliation from the four ORIGINAL oracle JSON members

Status: AUTHOR-RUN reading, evidence class = Coder reading (reported/independently-reviewed/simulated/qualified/accepted are NOT merged here). Awards nothing; all 41 units / 100 qualifiers remain UR; 65 no-current-refs, 35 cited-not-awarded and the four programme obligations stay unresolved. No governing text copied (IDs, ranges, hashes, own-word paraphrase only). No Drive writeback.

## Inputs (INDEPENDENTLY_DERIVED, REPRODUCIBLE_BY_MANAGER = YES)
Transport `A07_EXACT_ORACLE_MEMBERS_TRANSPORT.txt`: xz 174316 B sha256 c6532543...8d7d recomputed equal; base64 -> lzma -> ZIP; all four member sizes+sha256 recomputed equal to the header: V235_CROSSWALK_CANDIDATE (282d0fd2...), V230_TYPED_339 (1287086d...), V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339 (cc0c27be...), V232_FINITE_41_UNIT_QUALIFIER_RESIDUAL (bfee4c8a...). Method: `tools/a07_r47_member_reconcile.py <dir> <csv>` (refuses on any hash mismatch or any acceptance field != false). Output `V232_26S_R47_MEMBER_RECONCILIATION.csv` (100 rows). Source integrity is not equivalence or adoption.
Mechanical facts (counted): 41 units, 100 qualifiers; 92 carry a prior Manager working map, 8 carry none; every V232 unit says runtime NOT RUN. Prior-map line refs vs V235's own cited current ranges: 73 all inside, 4 some, 4 none, 19 no line ref.

## A. The 12 loss-listed qualifiers (NL0087 #1-3, NL0180 #1-5, NL0184 #1-4; counted 3+5+4 = 12 from the residual member)
**HISTORY NOTE (R50; the R47 sentence that stood here is superseded by section D).** What the V232 manifest lists is a set of four undeclared **V231** semantic-loss FLAGS (NL0087, NL0178, NL0180, NL0184). That flag names the V231 text only. The actual V232/V235 canonical oracle texts were supplied and read (section D) and restore the flagged content as PROPOSED, NOT RUN claims; they do not show that the CURRENT text still loses meaning, and "the oracle text itself is not stable" is NOT a finding. The per-qualifier readings below are readings of CURRENT current-range coverage only. Distinguish three evidence layers: (1) V231 loss flag = a manifest statement about V231; (2) V232/V235 actual text = read, hash-verified, proposed; (3) CURRENT-range coverage = the per-qualifier reading in this section. None awards anything; all 100 stay UR.
| Qualifier | V232 prior map / V235 wording (own words) | Reading (no award) |
|---|---|---|
| NL0087#1 abstention coverage visible | current ranges show selection policy and coverage | CARRIED_IN_CURRENT_RANGES; oracle for the unit not stable |
| NL0087#2 performance-when-predicting and suppressed-case profile | V235 itself states cited ranges do NOT establish it; V230 verdict GAP | HISTORY_ONLY_GAP. Not inferred away (MLCore459 raise duty) |
| NL0087#3 no tuning on confirmatory outer test | selection/exposure rules already apply | CARRIED_IN_CURRENT_RANGES |
| NL0180#1 lifecycle state kept in separate append-only ledger | current replacement is explicit | REPLACED_EXPLICITLY (replacement, not equivalence) |
| NL0180#2 named states, REVOKED != SUPERSEDED | preserved | CARRIED_IN_CURRENT_RANGES |
| NL0180#3 seven services, load vs serve | no-revoked-serving and recovery validation present; seven-service load scope not proven | PARTIAL; D26 open |
| NL0180#4 fail closed, no backward walk, alerts | first two present; no alert duty in that clause | PARTIAL; alert owner D24 open |
| NL0180#5 forensic exception | read-only audit exception explicit | CARRIED_IN_CURRENT_RANGES |
| NL0184#1 pointer alone insufficient | separate integrity authority plus snapshot/fence | CARRIED_IN_CURRENT_RANGES |
| NL0184#2 every consumer validates cached generation per use | not proven for all eight consumers | NOT_ESTABLISHED; D26 |
| NL0184#3 stale cache invalidation, N/N+1 visibility | broad outcome kept; non-publishing cache invalidation open | PARTIAL; D26 |
| NL0184#4 original-event history, revoked forensic only | explicit | CARRIED_IN_CURRENT_RANGES |
Per-qualifier, NOT by unit inheritance: of 12, 6 carried/replaced in current ranges, 4 partial, 2 not established/history-only gap. Even the carried ones sit on an oracle the V232 manifest says lost meaning, so none is awarded.
**NL0178 (separate; text read in section D).** Not in the 41-unit qualifier residual, so no per-qualifier DISPOSITION record exists (a bounded data shape, not absence of its canonical oracle). The canonical oracle text IS supplied and read in section D: all four components are present as proposed claims. Unit-level facts read: V235 SUPERSEDED-BY with six current ranges (overlay 10-29, 297-311, 335-340, 431-442, 456-457, 341-344); V235 says only the old freeze-blocked status instance is superseded while the adversarial runtime/artifact/isolation re-test and Manager reconciliation are retained and an old freeze approval is not a runtime certificate; V230 verdict JUSTIFIED_SUPERSESSION; V232 lists an undeclared semantic loss with changed oracle hash. The V231 loss flag names V231 only; whether any meaning is lost in the current V232/V235 text is answered by section D (not lost; proposed, NOT RUN).

## B. The 21 disagreement qualifiers (R43 list), read against V235's actual comparison wording
Question per qualifier: does V235's own comparison wording state the qualifier element (if yes the earlier R42 "not current" reading missed it; if no, only the container is incorporated and a strengthener would be silently restored)? A line-range check (prior-map lines inside V235's ranges) is shown as a second, independent signal.
| Qualifier | V235 wording states it? | Ranges signal | Reading |
|---|---|---|---|
| 0030#2 resolved-through identity to caller | no (two gates, original-event generation only) | none inside | CONTAINER_ONLY |
| 0056#1 raw retention vs selective use | yes | all inside | CARRIED_BY_V235_WORDING (R42 reading withdrawn as to wording) |
| 0073#3 diversity by target/model class | no (dependence, traceability only) | all inside | CONTAINER_ONLY |
| 0076#4 no arbitrary denominator shrink | stated, and V235 itself calls the method a source-equivalence question | no line ref | SELF_ADMITTED_RESIDUAL |
| 0078#2 preregistered conservative reconstruction | partial (observed vs reconstructed kept; preregistered/conservative not) | inside, BUT the lines relied on (487-489) lie after MLCore459 = history unless incorporated | PARTIAL; strengthener history-only (R49 correction) |
| 0078#3 exclude without trustworthy boundary | no wording; the lines that state it (489-490) lie after MLCore459, so they are HISTORY unless the master explicitly incorporates them; V235 range membership does not promote them; current 247/248 give explicit causally governed missing/stale/imputed states, no future imputation and a reproducible as-of meaning, but not the exclusion rule | inside (history) | HISTORY_STRENGTHENER_UNRESOLVED (R49 correction of my earlier CARRIED_BY_SOURCE label) |
| 0079#2 composed interval, not raw lookback/scalar max | partial (composed intervals named; rejection of scalar max not) | all inside | PARTIAL |
| 0080#3 held-back pass scoped, not universal | yes | no line ref | CARRIED_BY_V235_WORDING |
| 0096#1 ML can kill an idea / no-model | yes, anchored at MLCore265 which is in V235's ranges | all inside | CARRIED_BY_V235_WORDING_AND_RANGE |
| 0099#3 source/target range difference | no; this is a mapping-role question, not a clause | all inside | NOT_A_CLAUSE_MAPPING_ROLE_ONLY |
| 0113#1 portability section self-contained | partial (both evidence kinds yes; self-containment not) | all inside | PARTIAL |
| 0113#2 no separate design document needed | no | no line ref | CONTAINER_ONLY |
| 0126#3 core defect needs Owner-governed reopen | wording yes; V235 ranges do not contain the line the prior map used | none inside | WORDING_CARRIES_ANCHOR_MISMATCH |
| 0162#3 compatibility-contract exception | no | none inside | CONTAINER_ONLY |
| 0186#3 no consumer observes partial shadow record | partial (record must not expose partial mandatory fields; reader side not stated) | all inside | PARTIAL |
| 0220#2 revoked-lineage minimum fields | partial (ancestry, reason/scope; minimum field name not) | no line ref | PARTIAL |
| 0221#2 original reason + remediation finding | partial (reason/scope remediation review) | no line ref | PARTIAL |
| 0223#2 object MUST be annotated | V235 says annotations are useful, not sole mechanism: weaker than historical MUST | all inside | WORDING_DIVERGES_FROM_HISTORICAL_MUST |
| 0224#1 mark consistently with 0223 | same wording as 0223 (unit inheritance, not a clause) | no line ref | INHERITED_FROM_0223_NOT_INDEPENDENT |
| 0249#1 trigger identity incl. forecast timestamp + instrument | no | all inside | CONTAINER_ONLY |
| 0258#2 own resolved-through version | no | all inside | CONTAINER_ONLY |
Tally (counted from the 21 rows above): CARRIED_BY_V235_WORDING 3, HISTORY_STRENGTHENER_UNRESOLVED 1 (0078#3; earlier label CARRIED_BY_SOURCE withdrawn), WORDING_CARRIES_ANCHOR_MISMATCH 1, PARTIAL 6, CONTAINER_ONLY 6, SELF_ADMITTED_RESIDUAL 1, WORDING_DIVERGES_FROM_HISTORICAL_MUST 1, INHERITED_NOT_INDEPENDENT 1, NOT_A_CLAUSE 1 = 21.
Mechanical addition (R49): 4 qualifiers have every prior-map line after MLCore459 (NL0030#2, NL0078#2, NL0078#3, NL0162#3); for these a range-membership or line citation proves nothing current unless the controlling master explicitly incorporates the lines. The MLCore459 boundary is the Manager's reading, not re-derived from section headings.
Finding: the disagreement is real for the 6 container-only and 6 partial rows (12 of 21), plus the self-admitted residual, the divergence and the anchor mismatch. The earlier R42 "not current" reading is withdrawn as to V235 wording only for 0056#1, 0080#3 and 0096#1; withdrawing it is not adoption. The ML source owner must still confirm each; this reading is not that confirmation.

## D. R49 correction: the four exact V232 oracle texts WERE supplied (my earlier "hash-only / not supplied" statement is WITHDRAWN)
Source: `manager_comparisons[id].positive_negative_test.canonical_text` in V235 (not the legacy_V231 field). I recomputed sha256 of each UTF-8 text: it equals BOTH `canonical_sha256` and the V232 manifest `V232_oracle_plain_sha256` for NL0087 (1421 B), NL0178 (1069 B), NL0180 (1116 B), NL0184 (999 B). Each text states `NOT RUN`/proposed. DERIVATION_CLASS = INDEPENDENTLY_DERIVED (hashes recomputed; texts read).
What the texts say (own words), as versioned semantic content, not hash changes:
- NL0087: confirmatory-abstention tuning refused and coverage/abstention retained (qualifiers #1, #3 stated); #2 (performance when predicting, suppressed-case profile) is kept as a SEPARATE proposed D22 test and is expressly not claimed as incorporated. So the V231 "dropped clause" is present again in the V232 text, as a proposal.
- NL0178: the old freeze-blocked status is not revived; three prospective obligations (re-test of revised runtime/artifact contracts bound to exact identities, adversarial multi-instrument isolation challenge, independent Manager reconciliation) are stated with positive and negative cases; historical freeze approval is not a result. All four components of the unit are present.
- NL0180: states, revoked vs superseded, seven services, load vs serve, forensic exception and no backward fallback are tested (#1, #2, #3 as test content, #5); the alert duty (#4's alerts) and exact service/load mapping stay UNRESOLVED under D24/D26.
- NL0184: every enumerated consumer, every read/use identity check, stale-cache invalidation and N vs N+1 labelling are tested (#2, #3); publication fences are retained but explicitly NOT claimed to prove non-publishing cache duties (D26); #1 and #4 are carried only through the retained fences/labelling.
Consequence: the V231 undeclared-loss flag names V231 only; the V232/V235 canonical text restores the lost content as PROPOSED claims. It does not show that the current text still loses meaning, and it does not accept anything (NOT RUN; D22/D24/D26 unresolved; all 100 UR). The "12 loss-listed" readings in section A therefore stand as readings of CURRENT current-range coverage, and the oracle-text question is closed as supplied; the remaining adjudication is the ML source owner's.

## C. What stays open (named, not hidden)
All 100 UR; 65 no-current-refs; 35 cited-not-awarded; four programme obligations; Smallest exact input: the ML source owner's per-qualifier confirmation of sections A/B against the D22/D24/D26 decisions (the oracle texts themselves are supplied, section D).
