# A07 per-qualifier authority reconciliation — R40 (candidate; Coder finding, not a SALIX decision)

Reuses, does not duplicate: `V232_26S_QUALIFIER_RECONCILIATION_R02.csv` (100-qualifier inventory, lexical screen), `A07_R06_V03_RECONCILIATION_PROPOSED_R04.md`, `A07_NL0187_QUALIFIER_COMPARISON_PROPOSED_DELTA_R25.md`. Derived data: `V232_26S_REF_AUTHORITY_CLASSIFICATION_R40.csv` (script `tools/a07_ref_authority.py`). No governing text is copied; sources cited by ID/range. Adoption/awards stay held; nothing is written to Drive.

## 1. Evidence (evidence floor)
- DERIVATION_CLASS = INDEPENDENTLY_DERIVED (ref counts, region assignment); region boundaries read by me from current MLCore (Drive 1cf1uR0w…, 4715 lines; markers at lines 1-20 navigation/currentness, 25 V1.16 freeze overlay, 161 retained-V1.12 pointer, 165 V1.12 controlling pre-freeze overlay, 245/361 its conflict clauses, 365 V1.11 overlay, 491 its conflict clause, 503+ retained V1.10/historical).
- METHOD: parse every `MLCore:N` token in the R02 CSV column `controlling_current_line_refs`; assign by line number to a region; separately mark root-designated ranges (203, 208-211, 265, 297-319, 405-424). REPRODUCIBLE_BY_MANAGER = YES (`python tools/a07_ref_authority.py <R02 csv> <out>`).
- **Not reproduced:** the "543 of 1329 historical references" figure. The R02 CSV I hold has 143 ref slots (78 non-empty `MLCore:N` tokens, 65 qualifiers with an empty ref cell). I cannot derive 1329 from it; that count is INSUFFICIENT_EVIDENCE here (possibly a different file or revision). I do not use it.

## 2. Result: field label vs actual authority
Of 78 refs: V1.16 overlay 2, navigation pointer 1, V1.12 controlling overlay 66, V1.11 overlay (superseded by V1.12 where conflict) 7, V1.10-and-earlier historical 2. So 9 of 78 (11.5%) point at historical/superseded regions, 69 at overlay regions that state they control. The heading "controlling_current_line_refs" is therefore wrong for those 9 and, more importantly, **uninformative for 65 qualifiers that have no ref at all** (lexical screen found nothing — INSUFFICIENT_EVIDENCE, not absence).
Disposition classes (column `disposition_class`): 19 current-region ref, lexical not weak; 12 current-region ref, lexical weak; 4 historical-region only; 65 no ref. In every class the equivalence is NOT proven by a lexical screen; each needs the source owner.

Root-designated applicable ranges: 18 qualifiers cite at least one of them. Note these ranges sit in the V1.12 (203-319) and V1.11 (405-424) overlays; V1.11 text is superseded by V1.12 "where it conflicts" (MLCore 245/361). I treat 405-424 as applicable per root's instruction and flag that no conflict check against V1.12 was possible for it without owner confirmation.

## 3. Per-qualifier disposition
Per qualifier, `V232_26S_REF_AUTHORITY_CLASSIFICATION_R40.csv` carries: exact current refs actually in a controlling region, historical-region refs, owner role (ML source owner; Manager records), consequence (A07 coverage stays OPEN for it; no Tracker behaviour changed) and recommendation (owner names exact current clause + oracle repair, or the exact historical-only difference). I have **not** asserted any clause equivalence myself: with lexical overlap this low (see R02 `hist_token_overlap`) that would be a manufactured finding.

## 4. Specific items
- NL0034 / NL0262 oracles: need a lagged authoritative resolver/index **with a complete historical slice** (MLCore 4551-4573: both CURRENT_READ_FRESHNESS = PASS and HISTORICAL_SLICE_COMPLETENESS = PASS are required). The Tracker side now has the generic shape (R40 `E05Index.lookup` re-resolution, `as_known_rows`, `rebuild` with source-head stability); the resolver *instance* and the historical-slice completeness proof are source-owner inputs. Not invented.
- NL0186: consumer-side partial-observation exclusion is Tracker-side (R06R04 §5). Existing generic protection: whole-frame IPC, immutable accepted records read through the verified manifest reader. A consumer-side "no reader observes a partial record" test beyond those is OPEN — recommendation: Tracker work item once the reader contract is named.
- Already repaired, not repeated: NL0076, NL0096/ML265, NL0249/ML405-424. NL0187 uses the R25 delta.
- Historical UR 0030/0258/0266 do not erase MLCore 297-319, 265, 208-211, 203, 405-424 (applied as targets above).

## 5. What this does not do
Does not close A07/COVERAGE, A07/P12/N2, adopt anything, or award anything. Coverage stays OPEN.
