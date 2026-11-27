# Consolidated decisions, source reconciliation and dependency table (Coder return, 27 Nov 2026, R03)

CODER FINDING != SALIX DECISION. Nothing here clears, closes or advances A07, A02, QC34, P12/N2, any hold or any stage. Drive was read only.
Merge/PR status is a code event. Keep Trading separate from SALIX AI.

## 0. What was read this pass, and how (evidence floor)
| Source | Drive ID | How read | Class |
|---|---|---|---|
| Connected Contract V0.38 (head carries "CURRENT CONNECTED CONTRACT V0.38"; R10 text is a NOT-ADOPTED candidate appended at its end, lines 3959-3966) | file text export, 3,966 lines | downloaded; **sha256 of the downloaded export** 18d620db5c3df5606a05d4a5ae5e2692cecc76d81e81be0d667a7dab0b277c27, 326,563 B | INDEPENDENTLY_DERIVED hash of the *export*; not a hash of Drive's native bytes |
| News Hub Event/Context V2 | 1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw | read through the connector in full | directly read; bytes not retained, receipt-only |
| Decision Context V4 | 1dwGRh2EOxzhQGwV6x6TS4K5FFTu3_TJaES4R4BpW-PQ | read through the connector in full | directly read; bytes not retained, receipt-only |
| Governance (primary) | export, 398,157 B | downloaded; sha256 a9edd1b68fb88b45a4cee15d983cd78f878cbcdf756083448807a9736291cc07; **only the standing/status and A07/QC lines were read**, not the whole file | partial read |
| Build Plan, Matrix V5 | 1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo; 1RRZD4i_81Q4L6koxqyNs4INELOuI8aKVupznM-aBmTc | head/snippets and pinned-ID extraction only | partial read |
| MLCore etc. (V232 extract) | earlier pass | reproduced locator hashes | INDEPENDENTLY_DERIVED |
Not located by search: a document literally titled "Connected Contract V0.38" (the head of the file above is it). Master Health, Composer V9 and the A02 SPEC were **not** re-read this pass.

## 1. What the real sources changed in the code (no invention)
* Connected Contract V0.38 defines a delivery-failure model my earlier simulation did not match. New `stage_a/gateway/v038.py` encodes: the 3-value NON_DELIVERY_STATUS (NOT_READY_REQUIRED_DEPENDENCY, REJECTED_FAIL_CLOSED, REQUEST_AFTER_CUTOFF); structured OMISSIONS with EXPECTED_DEPENDENCY_KEY; RESOLUTION_VISIBILITY_WATERMARK; one final outcome per (consumer, manifest, scope, window) identity with REQUEST_ID many-to-one and no re-evaluation; SETTLEMENT_DELAY (fail closed on unknown/short bound); the GENUINE_LATE / SETTLEMENT_BREACH / RESOLVER_FAULT classification; and a presence check of the H1 CONSUMER_BINDING field list.
* **D12 is answered by the source** (V0.38 "Settlement delay", "Forensic classification"): my earlier LATE_VISIBILITY reading was incomplete. The resolver now observes at fence + SETTLEMENT_DELAY (`observed_at`), and eligibility stays `AVAILABLE_ASOF < fence`.
* News Hub V2 §§2, 9.0, 9.2A and Decision Context V4 A0/A1/F/H are now validators (`context/news_hub_v2.py`, `context/decision_context.py`). Field lists are the sources'. Ingestion, storage and the Drive-mirror comparison are not built.
* `schema/independent.py` now has an independent MANIFEST_HASH (producer==independent on three manifests; order-insensitive; refusals).
* Still SIM: the Gateway resolver, FW, ML, Health. Still CONTRACT: Context. Nothing is REAL except in-process baseline `tracker_identity`.

## 2. The 100 MLCore §26.S qualifiers — reconciled (file: V232_26S_QUALIFIER_RECONCILIATION_R02.csv, sha256 435940dc…13aeb)
METHOD: for each of the 100 rows I re-read MLCore, recomputed sha256 of the historical range (lines joined by LF + trailing LF), checked that every cited current line exists and is non-blank, and measured token overlap between the historical text and the cited current lines.
RESULT (INDEPENDENTLY_DERIVED, reproducible by `python3 -I recon` over the extract): 100/100 historical hashes reproduce; 100/100 cited current refs resolve; 41 units. **65 of 100 cite no current line at all**; 35 cite some. Of those 35: 4 strong, 19 partial, 12 weak lexical support.
What this does and does not show. Token overlap is a screen, not semantic equivalence, so it cannot support INCORPORATE or COVERED_BY. It shows only that **65 qualifiers have no cited current equivalent**, and that none of the 35 can be cleared by me. MLCore §26.S says history-only rules are supporting lineage unless incorporated, and that conflicting or absent ones are raised in final Coder review. All 100 therefore stay `RAISE_FOR_SOURCE_OWNER_DISPOSITION`. **Tracker-owned: 0 of 100** (all MLCore, ML-owned). I will not assign dispositions: that is the ML source owner's call.
Proposed wording for the source owner (one line per qualifier, applied to the CSV): `DISPOSITION = INCORPORATED | HISTORICAL_ONLY | COVERED_BY <current line> | NEEDS_AMENDMENT <text>`.

## 3. D19 / D22 / D25 / A02-D3 dependencies
| Item | What Governance line 103 says | What the Tracker code needs | State |
|---|---|---|---|
| D19 | direction selected, effectiveness pending; D19 ML part unresolved | Tracker side: effectiveness incorporation record | Tracker code does not depend on it; ML part not mine |
| D22 | direction selected, effectiveness pending | same | no code dependency found |
| D25 | unresolved where applicable | epoch re-resolution at point of use | `tracker/epoch_reresolution.py` is **candidate only**, not adopted |
| A02-D3 | A02 HOLD | opcode numbers, closed-grammar bytes, SQE_OPSET_V1_1 arithmetic | blocks Q3–Q8 at Annex level; tables stay PROVISIONAL |
I did not find a code path that silently relies on D19/D22. If the owner's text for them implies one, that is a source-owner statement I have not seen.

## 4. ONE decision table (every item needs a real decision or source I cannot supply)
| ID | Decision / missing item | Who | Proposed wording | Options | Consequence of each | Blocked until decided |
|---|---|---|---|---|---|---|
| D1 | Install resolver in `_governed_construction_authority` | Manager (Owner only if reserved) | "Integration design TRK-INT-01 accepts tracker/authority_bridge as the construction-authority resolver; effective on readback" | accept / reject / redesign | accept: ~10-line change + tests; reject: seam stays False and Tracker cannot authorize construction | real construction of a quant feature |
| D2 | Order-signer role | Manager | "Order-signer role = MANAGER, anchor = <record id>" | MANAGER / other role | other role: tests re-parameterised | signed construction orders |
| D3 | Code tables, opcode numbers, arithmetic spec | Manager admitting the A02 SPEC (A02 separate) | "Admit code tables vNN = <hash>; opcode/arith spec = <A02 SPEC id>" | admit candidate numbering / supply own | candidate: hashes become canonical; else stay PROVISIONAL | canonical identities, Q3–Q8 |
| D4 | Independent oracle for golden vectors | Owner staffing | "Oracle review: Codex; independence limitation recorded" | Codex / defer | defer: author-only vectors | COMPONENT VERIFIED |
| D5 | R5 provider qualification | provider custodian / Manager | "Provider <id> qualified against test list <hash>" | qualify / replace | unqualified provider means PROVIDER-DEPENDENCY QUALIFIED = NO | live use |
| D6 | Composer §27/§7A/§28 mapping | Composer owner | per-field confirmation | confirm / correct | correct: BuildPackage edit | Composer→Tracker REAL connection |
| D7 | Era-0 absence certification | source owner (amendment) | "Absence in ERA_0 is certified by <role> over <interval>; amendments by <rule>" | write rule / keep refusing | no rule: ERA_1 absence keeps refusing | certified-ABSENT producer |
| D8 | TR-06 routing predicate | source owner | one sentence | explicit flag / derived | derived: pipeline change | TR-06 final |
| D9 | stage_a→tracker_component dependency | Manager note | "Dependency accepted" | accept / move | move: refactor | none (documented) |
| D10 | Cross-journal atomicity | Manager note | "Ordering + claim_witness accepted" | accept / provider transaction | transaction: provider work | Q-atomicity closure |
| D11 | MODEL_SPECIFIC vs CONFLUENCE lane predicate | source owner | confirm or restate | confirm / restate | restate: `fw/lanes.py` edit | FW lane REAL |
| D12 | **resolved by V0.38 text** (see §1); remaining: REQUEST_AFTER_CUTOFF trigger | Connected Contract owner | "REQUEST_AFTER_CUTOFF = a first request for an identity arriving after fence + SETTLEMENT_DELAY" (mine) | confirm / restate | restate: trigger edit | REQUEST_AFTER_CUTOFF behaviour (enum exists; trigger not coded) |
| D13 | Byte encoding of FINAL_RESOLUTION_HASH, PACKAGE_HASH, FINAL_PACKAGE_HASH, EVENT/CONTEXT objects | Connected Contract / News Hub owners | "Typed Schema Annex extended to <objects>" | extend Annex / admit own | no encoding: no canonical Gateway/Context hashes | hashing those objects |
| D14 | Boundary conflicts: News Hub says ACTUAL consumable at `<=` cutoff, Gateway says `<` fence; REQUIRED with PARTIAL/DELAYED coverage unspecified | News Hub + Connected Contract owners | "Event/Context eligibility uses `AVAILABLE_ASOF < fence`; REQUIRED needs COMPLETE" (mine) | adopt / restate | else validators stay as written (<=; fail closed) | equality-at-cutoff cases |
| D15 | NON_DELIVERY status mapping per reason | Connected Contract owner | "absent/not-yet-available/late/non-current ⇒ NOT_READY; stale watermark, no status fact, vintage mismatch, health ⇒ REJECTED_FAIL_CLOSED" (mine; unknown ⇒ REJECTED) | confirm / restate | restate: `status_for_reason` edit | NON_DELIVERY status correctness |
| D16 | SETTLEMENT_DELAY value and certified max visibility lag | Tracker/Gateway operations | "SETTLEMENT_DELAY = <v>, certified max lag = <v>, evidence <ref>" | none exist in sources | none: `check_settlement` refuses | any REAL decision-window resolution |
| A07-1 | MLCore §26.S dispositions for 100 qualifiers (65 with no current ref) | ML source owner | per-row `DISPOSITION = …` | per §2 | unresolved ones keep A07/COVERAGE open | A07 acceptance |
| A07-2 | R06 V03 three-role vs Owner staffing | Owner | "R06 V03 applied as: <role split / waiver>" | meet / waive in writing | no choice: R06 candidate cannot be incorporated | R06 readback |
| A07-3 | R06 V10 whole-domain history | Owner/Manager | route 1: attach Drive Activity export hash; route 2: "BOUNDED_HISTORY_WAIVER: domain D=<ids>, horizon, residual set, scope A07 only" | export / waiver | revisions-only is insufficient | A07 acceptance |
| A07-4 | A01 currentness (21 ASSERTED_UNBOUND, 510 reference sets), QC34, D19/D22 effectiveness, D23/D24/D26/Q03 | named source owners | per item | — | — | A07/COVERAGE; A08 |

## 5. What I will not do, and why
Count the Gateway/FW/ML/Health simulations as integration; supply SETTLEMENT_DELAY, opcode numbers or hash encodings the sources lack; assign the 100 dispositions; write to Drive; call a merge a gate.
