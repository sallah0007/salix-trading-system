# A07 and D1–D12 — proposed resolutions and exact record edits (Coder return, 27 Nov 2026)

Author: Claude (Trading Bot 7). CODER FINDING != SALIX DECISION. Every item below is a PROPOSAL. Nothing is recorded, adopted, accepted or
closed by this file; Drive was read only. Private source text is not copied; sources are cited by Drive ID and line range.
Classification used throughout: **I** = implementable by me now (done or listed) · **P** = policy/source-owner decision · **C** = custodian/evidence-route item.

## 0. Evidence actually reproduced (vs receipt-only)
| Item | Class | Method / result |
|---|---|---|
| A07_Source_Review_Extract_R01.zip (1Avpm0dFCr5jH-ax6WhPXSXpV4jQMtY4m) | INDEPENDENTLY_DERIVED | downloaded raw; sha256 = fd594244deba849bed5a141fb96e8ae99cb5dc137d50c80b3fa0e8061a30d60e, 1,019,411 B — equals the Addendum R02 claim |
| 14 member payloads | INDEPENDENTLY_DERIVED | recomputed; 14/14 equal EXTRACTION_MANIFEST.json hashes |
| V232 finite register population | INDEPENDENTLY_DERIVED | parsed: 41 units, 100 qualifier dispositions, all 41 `runtime = NOT RUN`, all 100 status `UNCOVERED_CURRENT_EQUIVALENCE` |
| Locator range hashes | INDEPENDENTLY_DERIVED | 203 of 203 ranges whose source file is in the extract reproduce (sha256 of the lines joined with LF plus one trailing LF); 2 ranges cite sources not in the extract (MasterHealthFrozen, MasterHealthV3) = **receipt-only, not reproduced** |
| Source mix of the 41 units | INDEPENDENTLY_DERIVED | 201 of 203 ranges are MLCore; all 41 units share one authority question (MLCore 26.S, lines 456–459). None is Tracker code |
| V240 work register (1EKPazSQGUxPfnj8bTJSLAaKqJTFckYIb) | read in full (structure parsed: 18 work packages, 7 decision rows, 13 Composer items, A02/A08 tasks, V234–V240 pickups) | text via Drive connector; **no stated hash to compare**, so identity is receipt-only |
| Source ZIP V240 (1xf-IwFRcO5jHkD6eHij4UGZhLNlQLKp3, 37,132,834 B) | MANAGER_CLAIM | not downloaded; its claimed hash 6e599c5d… appears only in the extract manifest |
| V106 HTML da3af4c9…f80b40 (100,784,855 B) | MANAGER_CLAIM | not downloaded; receipt-only |
Raise-list for the 100 qualifiers: `docs/a07/V232_26S_RAISE_LIST_R01.csv` (IDs, line refs and hashes only; no source text).

## 1. Reconciling the Owner's delegation with the Manager hold
Facts (read): Owner delegation CLAUDE.md §2A authorises repo authoring/merge for this repository; A08 ("issue the applicable Stage A implementation commission")
is recorded `READY_TO_CODE NO; no general code commission`, depends on A01, A02, A07; the Manager records coding HELD and A07 OPEN.
Reading adopted by me (no gate changed): §2A is *repository authority*; A08 is the *governance commission*. They answer different questions, so I proceed
with unreleased candidate work and claim nothing from either. Consequences I hold myself to: no code is cited as released/operational; the production seam stays hard-False;
nothing here is evidence for A07/A08.
**P — Owner decision (one line, not a repeat of an earlier choice):** state whether work under §2A before A08 is (a) accepted as *candidate/pre-commission* work to be
reviewed when A08 issues, or (b) to stop. Proposed record text for the Manager (Drive): "Work done under Owner delegation §2A in sallah0007/salix-trading-system before
A08 is recorded as UNRELEASED CANDIDATE WORK; it does not satisfy A01/A02/A07/A08, clear QC34 or lift the coding hold; review is deferred to the A08 commission."

## 2. A07 — implementable vs decision, with proposals and exact edits
| # | Item | Class | Proposed resolution | Exact record edit (Manager, Drive) |
|---|---|---|---|---|
| A | 41 units / 100 qualifiers | **P** (ML source owner) with **I** done | One source-owner ruling on MLCore 26.S (456–459) applied per qualifier: INCORPORATE-AS-CURRENT, CONFIRMED-HISTORICAL-ONLY, or COVERED-BY(<current ref>). Per 26.S the Coder raises each; I raised all 100 in the CSV | In V232 register, for each (unit, index) set `status` to one of the three values with the owner's ruling ref; leave `runtime` NOT RUN. Add one row "26S-RULING-R01" naming the ruling object. No count-based closure |
| B | R06 V03 vs Owner staffing | **P** (Owner) | V03 needs three actors; staffing has two (Claude author, Codex Manager/reviewer). Option 1 (minimal): the Owner personally is the single terminal assessor/writer (distinct from both). Option 2: amend V03 to a two-actor rule with the independence limitation recorded and the Owner as acceptor of S (V13). I do not choose | Replace V03 text with the chosen option verbatim; record the limitation sentence "Codex also prepares Manager reconciliations; not third-party independent". No actor invented |
| C | R06 incorporation / readback | **P**+**C** | Manager incorporates R06 into Governance after review, then byte readback (V15). Not code | Governance: add R06 section + hash; Matrix last (per R06 decision_order) |
| D | V10 complete domain history | **C** (external evidence) / **P** if waived | Two routes: (1) Owner/Manager obtains the Drive Activity export for domain D and binds it; (2) Owner grants an explicit, bounded-history waiver (reserved decision). Revisions list alone is insufficient (R06 V10). I will not simulate history | If (2): "BOUNDED_HISTORY_WAIVER: domain D=<ids>, horizon=<from>–<to>, residual unknown set stated, scope A07 only" signed by Owner. If (1): attach export hash |
| E | O1 programme scope / O3 missing design | **P** (Manager) | Use the 13 A16.CFG.PLAN items + my coverage matrix as the inventory; each gets owner/successor/blocker | Fill per-item `state` from OPEN_DESIGN_AND_COVERAGE to a dated disposition |
| F | O2 chronology (Annex-vs-DAG) | **I**+**P** | Done in code: Annex-conformant `stage_a/schema/` + independent verifier; prototype labelled NON-CONFORMANT. Needs a scoped supersession note | Add disposition "Prototype composer/expression = historical non-conformant candidate; Annex V1.2 controls (Matrix V5)" |
| G | D19, D22 | **P** (statuses already `OWNER_DELEGATED_MANAGER_DIRECTION_SELECTED_SOURCE_EFFECTIVENESS_REVIEW_PENDING`) | The direction is selected; only effectiveness (source incorporation + review) is pending. Proposed: incorporate the D22 narrow reporting clause "where measurable; unavailable outcomes carry an explicit reason; no fabricated zero/denominator" and the D19 staged-evidence reading, each as a scoped successor | Move status to INCORPORATED only after review+readback; until then unchanged |
| H | D23, D24, D26, Q03 | **P** (ML/FW/Health owners) | Follow the 27 Oct brief's own recommended treatments; none touches Tracker code. D26/Q03 matrices to be filled by the ML owner | Fill service×operation×mode matrix; record target-owner binding rule |
| I | D25 | **P** adoption; **I** candidate built | Candidate Tracker-domain protocol (3 outcomes, stale-epoch refusal) built and tested: `stage_a/tracker/epoch_reresolution.py`. Retry/timer/enum remain unselected | Adopt/reject the protocol for TRACKER_LIFECYCLE subjects only |
| J | A01 promotion, QC34, 7-home coverage | **C**/**P** | Not code. A01 needs the actual promotion record; QC34 stays ALERT(HOLD) until its populations are joined | Unchanged until evidence exists |
| K | A02 (separate) | **P** | Class B closure; supplies SPEC/decoder, opcode numbers. See D3. Not conflated with A07 | n/a |

## 3. D1–D12 — proposals and exact record edits
| D | Class | Proposed resolution | Exact edit |
|---|---|---|---|
| D1 resolver install | **P** | The seam stays False until the Manager records an *Integration Design* that accepts `authority_bridge` (journal-verified, fail-closed, single-use) as the route and rejects callbacks/flags/claim-only paths (as the assessment already states). Install is then a ~10-line change I make with tests | "Integration design TRK-INT-01 accepts tracker/authority_bridge as the construction-authority resolver for `_governed_construction_authority`; effective on readback" |
| D2 order-signer | **P** | Name the signer role (proposed: MANAGER) and its key/identity record | "Order-signer role = <role>, anchor = <record id>" |
| D3 code tables/opcodes/arithmetic | **P** (A02 SPEC) with **I** | Candidate ENUM/REF_TYPE tables generated from the Annex symbol lists (`stage_a/schema/candidate_code_tables.py`; numbering 1.. in Annex order is *my* proposal; unlisted sets deliberately absent). Opcode numbers + SQE_OPSET_V1_1 arithmetic still need the A02 SPEC | "Admit code tables vNN = <hash of the admitted table file>; opcode/arith spec = <A02 SPEC id>" |
| D4 independent oracle | **P** (Owner staffing) | Under the Owner's no-third-party rule: Codex (Manager) re-derives expected bytes for the golden vectors from the Annex independently of my code; limitation recorded (same Manager role as reconciler) | "Oracle review: Codex; independence limitation recorded" |
| D5 R5 provider | **C** | Provider qualification is a custodian action; I supply the qualification test list (fence, orphan, unknown-commit, tamper) already in `tests/trk_stage_a` | "Provider <id> qualified against test list <hash>" |
| D6 Composer §27/§7A/§28 mapping | **P** (Composer owner) | Owner confirms or corrects my field mapping in `BuildPackage` | Per-field confirmation list |
| D7 certified ABSENT | **P** | Amendment defining Era-0 resolution: who certifies absence, over what interval, how amendments are handled. Until then ERA_1 absence refuses. Once the rule exists the producer is **I** | New rule text + id; then "producer admitted" |
| D8 TR-06 predicate | **P** | Source owner states the routing predicate (mine = explicit `quant_feature_requested`) | One sentence |
| D9 dependency on tracker_component | **P** (note) | Accept the dependency or direct a move | "Dependency stage_a→tracker_component accepted" |
| D10 cross-journal atomicity | **P** (note) | Accept ordering+witness (consume record carried as `claim_witness`) or require a provider transaction | Accept/require |
| D11 (new) MODEL_SPECIFIC vs CONFLUENCE lane predicate | **P** | Mine: listed target + declared baseline deps ⇒ CONFLUENCE else MODEL_SPECIFIC (`fw/lanes.py`) | Confirm or restate |
| D12 (new) G2 reading | **P** | "pre-fence available but late visibility classified without causal widening" implemented as non-delivery `LATE_VISIBILITY`, set unchanged (`gateway/contracts.py`) | Confirm or restate |

## 4. What remains genuinely blocked (exact source)
D3/A02 SPEC (opcode numbers, closed-grammar program bytes, SQE_OPSET_V1_1 arithmetic); D7 amendment; Event/Context field layouts (News Hub Event/Context
Delivery Contract V2, Decision Context V4, Connected Contract V0.38 H2 — none admitted into this repo; plan says I may not invent layouts); the real Gateway/FW/ML/Health
implementations (not in this repo); R5 provider; A07 items A–D above.
