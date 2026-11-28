# A07 R52: one 100-row PROPOSED disposition record (Coder proposal; awards nothing)

Status: PROPOSAL for the ML source owner and Manager. Evidence class = Coder reading. All 100 qualifiers stay UR; A07/COVERAGE OPEN; A07/P12/N2 UNSATISFIED; no gate, hold or stage changes; no Drive writeback; no governing text copied (identifiers, ranges, hashes, own-word paraphrase only). Independence limitation stands (Claude authors, Codex/Manager review, Sallah signs off; no third actor). Hash parity, range overlap and token similarity are never used as COVERED_BY, and a missing current ref alone is never used as HISTORY_ONLY.

## Inputs (INDEPENDENTLY_DERIVED; REPRODUCIBLE_BY_MANAGER = YES)
Four original members re-verified by sha256 before use: V235_CROSSWALK_CANDIDATE 282d0fd2…, V230_TYPED_339 1287086d…, V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339 cc0c27be…, V232_FINITE_41_UNIT_QUALIFIER_RESIDUAL bfee4c8a…; acceptance fields read false. Joined with `V232_26S_R47_MEMBER_RECONCILIATION.csv`, `V232_26S_R42_PER_QUALIFIER_READING.csv`, `V232_26S_R43_ORACLE_ASSOCIATION.csv`, `A07_R47_MEMBER_RECONCILIATION.md`. Method: `python -I tools/a07_r52_disposition_record.py <member dir> docs/a07 docs/a07/V232_26S_R52_PROPOSED_DISPOSITION_RECORD.csv`. Output has 100 rows, 41 units. Invariants checked by `tests/test_a07_r52_record.py` (with negative controls that fail on tampering).

## The record
`V232_26S_R52_PROPOSED_DISPOSITION_RECORD.csv`: per row, qualifier sha256, own-word historical meaning, R42 class, exact current controlling anchor (MLCore paragraph numbers within the controlling 1-459, or NONE with the reason), oracle evidence (V235 disposition/target/ranges/comparison hash, V232-vs-V230 oracle hash relation, acceptance state, flags), prior-map-versus-V235-range signal, discrepancy, recommended disposition, rationale, exact source delta if needed, Tracker code action, decision-input id, evidence class, award (NONE).

Counts (from the CSV): R42 classes {'P': 32, 'H': 16, 'C': 40, 'O': 3, 'L': 3, 'R': 2, 'N': 4}; 90 rows have a current controlling anchor in 1-459. Recommended-disposition families:
| family | rows |
|---|---|
| COVERED_BY_PROPOSED | 45 |
| PARTIAL | 37 |
| CONTAINER_ONLY | 4 |
| PROPOSED_WORDING_ONLY | 2 |
| PROCESS_OR_BINDING_NOTE | 2 |
| SELF_ADMITTED_RESIDUAL | 1 |
| HISTORY_STRENGTHENER_UNRESOLVED | 1 |
| HISTORY_ONLY_GAP | 1 |
| NOT_A_CLAUSE | 1 |
| WORDING_CARRIES | 1 |
| PARTIAL_LINEAGE_ONLY | 1 |
| REPLACED_EXPLICITLY | 1 |
| NOT_ESTABLISHED | 1 |
| WORDING_DIVERGES_FROM_HISTORICAL_MUST | 1 |
| INHERITED_FROM_0223 | 1 |
These are proposals. The 12 loss-listed rows are readings of CURRENT-range coverage only; the V231 loss flag names V231 text, and the V232/V235 canonical texts restore the content as proposed, NOT RUN claims.

## The 21 disagreements, individually (R47 section B + Manager source answers)
Carried by V235 wording or range: **0056#1** (wording-only: V235 is Manager-proposed, so it is NOT a controlling anchor; R42 withdrawn as to wording), **0080#3** (same: wording-only, no controlling anchor yet), **0096#1** (carried at MLCore 265; repaired row). **0249#1**: the current paragraphs 405-424 carry forecast time + instrument; the defect is in V235's comparison wording (correct that wording; no source delta).
Container only (V235 incorporates the container, not the element): **0030#2**, **0073#3**, **0113#2**, **0258#2** (and 0030#2/0258#2 are the same concept). 0113#2 is a process remark; HISTORY_ONLY with an effect statement is recommended. 0030#2/0258#2: restoration delta recommended (p313/p319 need both freshness and completeness; the caller-facing resolved-through identity is the missing half).
Partial: **0079#2** (rejection of scalar max absent; one-sentence delta recommended), **0113#1** (self-containment, owner-confirmable), **0186#3** (reader side unbound; the immutable prospective record alone does not prove no reader can observe a partial record), **0220#2** and **0221#2** (minimum lineage fields; original reason + finding record; deltas recommended).
Lineage-only after the controlling boundary (MLCore 459: history unless explicitly incorporated; range membership does not promote): **0078#2**, **0078#3**, **0162#3**, plus **0030#2**'s only statement. Four prior-map sets (0030#2, 0078#2, 0078#3, 0162#3) lie wholly after 459. 0078#3's earlier CARRIED_BY_SOURCE label stays withdrawn.
Other: **0076#4** self-admitted residual (V235 calls the method a source-equivalence question; restoration recommended). **0099#3** is a mapping role, not a clause. **0126#3** wording carries but the anchor mismatches: the controlling paragraph (203) says no reopen now and lacks the conditional Owner-governed path; correct the V235 range list and add the path if wanted. **0223#2**: V235 says annotation is useful, not the sole mechanism, which diverges from the historical MUST; a mandatory append-only annotation is NOT inferred from present-day revocation freshness. **0224#1** is inherited from 0223 and not independent.

## Genuine decision inputs (each: question, consequence either way; none is decided here)
- **DI-01** (0078#2, 0078#3, 0162#3): is any paragraph after 459 explicitly incorporated for these strengtheners? Yes: they become controlling and need an explicit reviewed delta. No: they are HISTORY_ONLY with the effect that preregistered conservative reconstruction, exclusion without a trustworthy boundary, and the compatibility-contract exception are not stated rules.
- **DI-02** (0223#2, 0224#1): is per-object append-only annotation mandatory, or is dynamic trust resolution the mechanism? Mandatory: delta required, and 0224#1 follows. Dynamic only: HISTORY_ONLY with the effect that no per-object annotation duty exists.
- **DI-03** (0076#4): restore "no arbitrary multiplicity-denominator shrink without a justified method"? Restore: closes the self-admitted residual. History-only: a method may change the family count without a recorded justification.
- **DI-04** (0073#3): is diversity-by-target/model-class a normative measurement? Yes: delta. No: independence is judged by dependence only.
- **DI-05** (0079#2): state that a raw lookback or scalar maximum is insufficient? Yes: one-sentence delta. No: only the composed-interval wording stands.
- **DI-06** (0220#2, 0221#2): restore the minimum revoked-lineage field set and the original-reason/finding record? Yes: deltas. No: consumers cannot check a revoked lineage mechanically.
- **DI-07** (0030#2, 0258#2): restore caller-visible resolved-through identity / resolver's own resolved-through version? Yes: delta (affects what Tracker can later bind). No: callers rely on epoch/watermark only.
- **DI-08** (0186#3 and the shadow-row field set): state the reader-side partial-record rule and the mandatory shadow-row field set? Needed before any Tracker consumer contract for shadow records can be bound; until then Tracker only has atomic record-level publication as a candidate.
- **DI-09** (0087#2 / D22): performance-when-predicting and suppressed-case profile: restore as a requirement or HISTORY_ONLY with effect? V235 itself says the cited ranges do not establish it.
- **DI-10** (0180#3, 0180#4, 0184#2, 0184#3 / D24, D26): seven-service load-versus-serve scope, alert owner, eight-consumer per-use validation, non-publishing cache invalidation: not proven in current text; each needs the owner's scope statement or a delta.
- **DI-11** (0056#1, 0080#3, 0126#3): V235 comparison wording is not a controlling anchor. Adopt the wording into a controlling paragraph (delta), or correct V235's range list/wording.
- **DI-12** (0113#1, 0113#2): self-containment and no-separate-design-document statements: confirm as structural remarks (no code effect) or restore.

## Tracker code action
None follows from the ML-owned history/current questions (R02 marks all 100 `tracker_owned = NO`). Tracker-adjacent duties already exist as candidate code and tests (held-back lifecycle tests, atomic record-level publication, deterministic event identity): 0034#1, 0034#2, 0186#1, 0186#2, 0186#3, 0200#1, 0200#3, 0249#1, 0262#1. These are not awards; the shadow-row field set and reader contract remain unbound (DI-08).

## What this does not do
No qualifier moves from UR; no oracle is accepted; no R06 reconciliation is performed (Manager custody work; this record only supplies predicate evidence); no waiver is suggested; no gate is cleared. Smallest remaining input: the ML source owner's per-qualifier confirmation of the proposals above, with D22/D24/D26 decided by their owners.
