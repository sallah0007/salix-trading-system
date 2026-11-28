# A07 R43: oracle-level association of the 100 per-qualifier readings

Status: AUTHOR-RUN reading association. Awards nothing; all 100 UR remain; no Drive writeback; identifiers, ranges and hashes only (no governing text copied).
Sources read in R43 (recovered extract Drive 1Avpm0dFCr5jH-ax6WhPXSXpV4jQMtY4m; ZIP sha256 fd594244... matches the Manager-recorded value, recomputed here): `V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json` (sha256 1287086d...), `V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339.json` (cc0c27be...), `V235_CROSSWALK_CANDIDATE.json` (282d0fd2...). Tool: `tools/a07_r43_oracle_association.py`; output `V232_26S_R43_ORACLE_ASSOCIATION.csv` (100 rows, 41 units).

## What the three files themselves say (read, not inferred)
- V230: `global_source_semantic_acceptance = false`, `global_oracle_acceptance = false`, Tier2 OPEN; counts are review units, not current normative clauses; the exact Reviewer-28 heading count is stated UNRESOLVED (no 28 IDs / predicate supplied).
- V235: `status` = Manager proposed, not adopted; `independent_acceptance = false`; `unadjudicated = 0`; one explicit source-equivalence residual; the old V212 zero-residual result is marked superseded.
- V232: 4 undeclared V231 semantic losses are listed (NL-0087, NL-0178, NL-0180, NL-0184); 71 declared V231 deltas; `new_source_adoptions = 0`; hash basis change disclosed.
The tool refuses to run if any of the three acceptance fields is not false.

## Per-qualifier relations (flags in the CSV)
| Flag | Qualifiers | Meaning (no award) |
|---|---|---|
| V231_UNDECLARED_SEMANTIC_LOSS_LISTED | 12: NL-0087 #1-3, NL-0180 #1-5, NL-0184 #1-4 | the oracle/target transition for these units lost meaning the V232 manifest did not declare; my R42 C/P classes on them (NL-0087#1,#3; NL-0180#1,#2,#5; NL-0184#4 are C) cannot rest on the oracle and are not re-awarded |
| V235_DISPOSITION_RESIDUAL | 3: NL-0087 #1-3 | V235 itself leaves the unit RESIDUAL |
| V235_DISPOSITION_SUPERSEDED-BY | 11: NL-0180 #1-5, NL-0184 #1-4, NL-0225#1, NL-0263#1 | V235 proposes supersession; my C/P readings on NL-0180/0184 describe the current native text and are kept separate from any supersession adoption (historical strengtheners stay explicit) |
| R42_READS_NOT_CURRENT_BUT_V235_SAYS_INCORPORATED_AT | 21: NL-0030#2, 0056#1, 0073#3, 0076#4, 0078#2-3, 0079#2, 0080#3, 0096#1, 0099#3, 0113#1-2, 0126#3, 0162#3, 0186#3, 0220#2, 0221#2, 0223#2, 0224#1, 0249#1, 0258#2 | DISAGREEMENT to be adjudicated by the ML source owner: either V235's current-source range carries the qualifier (my reading missed it) or it carries only the container (a strengthener would be silently restored). The CSV lists V235's current-source RANGES (not text) and a hash of V235's own qualifier-comparison string for the reviewer. Not resolved here, not adopted |
| V232_CONTENT_MODIFIED / ORACLE_TEXT_DIFFERS_FROM_V230 | 19 | the oracle text itself changed after V230; hash parity with V230 is therefore not available for these and is never used as semantics |
| ORACLE_NOT_GLOBALLY_CERTIFIED_PER_CLAIM_MAPPING_REQUIRED | 78 | V230 states shared-group per-claim mapping is still required: an oracle covering a unit is not a mapping of each qualifier |

## Conclusions (Coder findings, not decisions)
1. No qualifier moves from UR. V230/V235 explicitly withhold acceptance and the 12 loss-listed QUALIFIERS (across THREE units: NL0087#1-3, NL0180#1-5, NL0184#1-4; V232 also lists NL0178 at wider transition scope) are not even oracle-stable.
2. The 21 disagreements are the concrete adjudication list for the ML source owner (smallest exact input: confirm whether V235's listed current-source range states the qualifier, per qualifier).
3. NL0034/0262 (missing-tail / stale-index) and NL0186 (atomic consumer read) are engineering duties implemented in R43 (`historical_eligibility`, `lifecycle_eligibility`, `atomic_publication`) and are kept distinct from the unbound shadow-row contract (MLCore p323/p324 only).
4. R06 candidate (Drive 1V5bv2QrbD0U22ExYUbz4FuwHkvXTsCSe): the readable projection is EMPTY because the file is JSON; the raw payload is present (Manager recovered it by raw download; see docs/a07/A07_R44_R06_V240_RECORD.md). Access is resolved, adoption is not.


**R50 NOTE (history label).** The `V231_UNDECLARED_SEMANTIC_LOSS_LISTED` rows above record a V231 loss FLAG from the V232 manifest, not a finding about the CURRENT text. The actual V232/V235 oracle texts were read and hash-verified in `A07_R47_MEMBER_RECONCILIATION.md` section D; see its section A history note. No award; all 100 UR.
