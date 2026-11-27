# A07 — NL-0187 qualifier_comparison: PROPOSED bounded delta (R25-E)

STATUS: PROPOSED, NON-GOVERNING. Not applied to any Drive record (Drive is Coder-read-only; Manager-only writes). No A07 unit, qualifier or programme obligation is closed by this note. No private source text is reproduced; sources are cited by ID, line range and range hash only.

## Source basis (read directly this pass)
- Extract: `A07_Source_Review_Extract_R01.zip` (Drive 1Avpm0dFCr5jH-ax6WhPXSXpV4jQMtY4m), member `V235_CROSSWALK_CANDIDATE.json`, sha256 `282d0fd2d541562ca956b973e9aa9b4888ee302ca06d37cf1948cd382f9ad7fb`; `manager_comparisons[169]`, id `NL-0187` (339 entries in the array).
- Historical source: MLCore (1cf1uR0wJLPVsWitIy9aVLM9CZPk2fyd4bP_3tFyLKrw) line 1409, range hash `aeef1eb9…bf088a`; container row A22.AUDIT-MLCore-08-033; target A22.V212-HIST-MLCore-1409; disposition INCORPORATED-AT.
- Current source: MLCore lines 323–334 (range hash `4026e464…944bc6e`). Lines 331–334 are the Owner scorecard minimum-visibility contract and the pooled/transfer/cross-instrument distinction sentence. Lines 323–330 are shadow-counter/disposition rules.

## Defect (author-reproduced by reading the record)
The record's `qualifier_comparison` for NL-0187 describes one-final-disposition-per-trigger, fencing precedence, retry-vs-event counting and abstention/infrastructure separation. That is the shadow-counter/disposition content of lines 323–330. The historical line 1409 and the canonical `positive_negative_test` (which itself says not to use a shadow-counter oracle) concern DISPLAY VISIBILITY of model research class and pooled/transfer/cross-instrument contribution distinction. The qualifier wording is therefore about a different obligation than the one the unit tests.

## Proposed replacement wording (paraphrase; not source text)
Current Owner-facing review, and as-applicable model/research-class surfaces, must make the model research class visible, and where applicable the pooled/transfer/cross-instrument classification, so that such a contribution is distinguishable from a standalone single-instrument forecast (MLCore 331–334). Whether the historical "every displayed forecast or contribution" scope extends to every display surface/field is NOT established by the current source and remains UR pending an exact current display/payload source. No universal UI field, field name or layout is introduced. No whole-unit equivalence between line 1409 and lines 323–334 is claimed: lines 323–330 (shadow counters/dispositions) are a separate obligation and are not discharged by this unit.

## What this does not do
- Does not edit the source extract or any hash above (original preserved as read).
- Does not close NL-0187, the other 40 units / 100 qualifiers, or any of the four A07 programme obligations; A07/COVERAGE stays OPEN.
- Does not clear A02 Class B HOLD, P12/N2, QC34, A08 or Stage A. A merge of this note is a code/doc event only.

## Disposition for the Manager
Accept, amend or reject the replacement wording and record the result in Drive. If rejected, this file stays as the historical rationale.
