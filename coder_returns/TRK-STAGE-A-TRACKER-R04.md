# TRK-STAGE-A-TRACKER-R04 — Codex review fixes, governing-source reads, consolidated full-component status

Author: Claude (Trading Bot 7), CLAUDE.md §2A. CODER FINDING != SALIX DECISION. Candidate code · author tests · simulation · real integration · independent review · formal acceptance are SEPARATE and only the first three exist. Drive read-only. No gate, hold, acceptance or stage changes. Supersedes R03 where they differ.
State: AUTHORING COMPLETE = NO · COMPONENT VERIFIED = NO · PROVIDER QUALIFIED = NO · INTEGRATED = NO · INDEPENDENT REVIEW = Codex scoped source review of PR #27 only (not acceptance) · FORMAL ACCEPTANCE = NO.

## 1. Evidence floor (bound to the work, not the base)
WORK COMMIT `bbed2f3442377ea2ce25ad56337baeaf6c5cb7a3`, TREE `1521d45d00d895cdbcbb0df5ac518d2fbbd017cb`, branch `stage-a/tracker/review-r04`, on main `4c0db9e23e7f3574515fa9c17aa2b655bd779c63`. Run on that tree with bytecode off (`-B`):
`python3 -m pytest tests -q` → **570 passed** · `python3 -m unittest discover -s tests` → **OK** · `mutation_sweep.py` → **22/22 killed** · `mutation_sweep_boundaries.py` → **106/106 killed**. Doc-only commits after it do not change code (`git diff bbed2f3 HEAD --stat` lists docs only). DERIVATION_CLASS = INDEPENDENTLY_DERIVED; REPRODUCIBLE_BY_MANAGER = YES. R03's floor named the base SHA; that was wrong and is superseded.

## 2. Codex findings — all three confirmed, fixed, with controls
| # | Finding | Fix | Negative controls |
|---|---|---|---|
| 1 | `_tagged` treated every non-ENUM tag as REF (BOGUS == REF bytes) | `_tagged(enums, v)` accepts only `('ENUM', set, code)` / `('REF', ref)`; any other tag, arity, type or empty value raises | 14 malformed tags on status path, 3 on delivered path; mutant restoring the old fall-through is killed |
| 2 | `row_hash` hard-coded `speculation_mode == 2`; remapped provisional table raised | every independent hash takes the supplied versioned `enums` table; membership is `code in table.values()` (bool/str/unknown refused; absent set refused); GATED_ONE_STEP is looked up by symbol. No numbering adopted | remapped GATED_ONE_STEP→17 equals producer; same code unknown under old table; unknown codes on CURRENTNESS_STATE, TRANSITION_STATUS_EVENT, CHAIN_STATUS, DATA_VINTAGE_MODE, REFIT_MODE, PROGRAM_CAPABILITY_CLASS; hard-coded `== 2` mutant killed |
| 2b | manifest `refit_mode_is_scheduled` trusted from caller | derived from the resolved `refit_mode`; a supplied flag that disagrees is refused; presence rules follow the derived value | lie in both directions, flag omitted, bypass attempt, remapped table |
| 3 | `FinalResolutionStore` check/evaluate/store unguarded; `None` outcome defeated `is not None` | one `RLock` over the sequence; in-flight marker refuses re-entry (`REENTRANT_RESOLUTION`); evaluator exception stores nothing and clears the marker; `None` refused. **Bounded contract documented: single process, in memory.** Cross-process atomicity stays an unresolved provider decision (D5/D10) | 16 threads behind a barrier → 1 evaluation, 1 object; re-entry; raise; None; marker cleared; 4 mutants |

## 3. Governing-source reads this pass (corrects R03's "status/snippet only")
| Source | ID | Read | Class |
|---|---|---|---|
| Connected Contract V0.38 | export of the V0.38 file (head: "CURRENT … V0.38") | full text, 3,966 lines | sha256 of the export 18d620db…277c27 |
| News Hub V2; Decision Context V4 | 1GSaxvVS…; 1dwGRh2E… | full | directly read; bytes not retained |
| **Master Health Extension V3** | 1paXK6vPORaZ4QtQo3Vv3f49h7w2oHVt1-McSC2g6Bkk | **full** | directly read; bytes not retained |
| **Composer V9 baseline** (owner-frozen) | 1ghkK8apLFPsV6XEBw0tTFYnGYkfhcgp3Ty7kNhQ2CZM | **full text export, 1,524 lines**; §§7A, 27, 28 read | export sha256 e927a20c… (first 16 hex) |
| **Frozen Tracker baseline DOCX** | 15mPi14mG5MAOerZTnhbWfWXwcOIpzWsA | **bytes downloaded: 55,918 B, sha256 ecaa9af35c712dbc38bdfe8a22b1cb81406a13a6db46cf640caeca89b5f3de4c = the recorded identity (recomputed)** | INDEPENDENTLY_DERIVED |
| **C22 generic SPEC lookup (A02)** | 1I4xYDxdjD75G8N-oHGW2ccDCd9ugVX8n | **full (1,273 B)** | directly read |
| Build Plan, Governance, Matrix V5 | 1CVUUPJ4…; 1gzUPf4D… (procedure home); 1RRZD4i_… | Build Plan evidence text extract (build.txt, earlier pass) + Governance/Matrix status lines (not whole files) | partial |
Not found by search: a standalone "A02 SPEC" document. The only A02-labelled SPEC artifact found is the C22 lookup, which states **fully_operational_bindings = 0**, 84 effective-unresolved fields, A12 only 2 members, A17 only 6 Quant-partial members. So it cannot supply opcode numbers or arithmetic, and the D3 blocker stands on evidence rather than assumption.

## 4. Which "blockers" the sources actually resolve
RESOLVED OR REFRAMED BY SOURCE
* **D12** (settlement/late) — Connected Contract V0.38 text (R03).
* **Fit production is not Tracker-owned.** Build Plan R2 reconciliation: "Composer owns … governed refit/FIT_GENERATION production only"; Tracker owns materialization, verification, acceptance, publication. The Tracker slice is Q9/Q10: Q9 is now a test (new generation changes row and delivered hashes; manifest has no generation field to mutate); Q10 is the intake FIT_ANCESTRY stale/unknown test. Nothing further to build in Tracker; the producer is a Composer dependency.
* **Confluence has no merge object in any source.** Connected Contract: "baseline/GARCH/confluence are human-readable descriptions of manifest identity, not new PACKAGE_CLASS values". Build Plan Q13/F3: confluence exists only when the consumer manifest requests both, with independent lineage. Covered by the lane tests; building a "merge" would be invention. **D11 is therefore reframed**: `fw/lanes.py` is an internal classifier, never a canonical value (flag for Manager to confirm, below).
* **D6 (partial):** Composer §28's 22 bullet fields + FINAL_REPORT_HASH are all emitted by the adapter, and the baseline `tracker_component.report` schema (23 fields) matches; now a test. §27 BUILD_OUTPUT_PACKAGE and §7A mappings are NOT verified.
* **Master Health B0:** envelope, anti-replay, silence derivation, recovery gating were unbuilt and are source-exact; built as `health/envelope.py` (5 tests, 14 mutants).
* **D2/D7:** searched the frozen DOCX, Composer V9, Connected Contract V0.38 and the Build Plan extract for signer/trust-anchor/Era-0/absence-certification text: **none**. They are design decisions the sources do not make.
GENUINE GAPS FOUND IN THE SOURCES (not mine to fill)
* No byte layout exists outside Annex V1.2 for FINAL_RESOLUTION_HASH, PACKAGE_HASH, FINAL_PACKAGE_HASH, Context or Health objects (0 hits for UINT16/UINT64/big-endian in V0.38, Composer, frozen DOCX) → D13.
* SETTLEMENT_DELAY is "a versioned operational contract"; no value or certified lag → D16. REQUEST_AFTER_CUTOFF appears only in the enum → D12'.
* NEWS_CONTEXT_HEALTH_PROFILE_HOME is "REQUIRED BEFORE FIRST FW/ML EXECUTION" and not yet governed (Master Health V3 §G) → new D17.
* Health thresholds, flap limits, critical-set membership and the reason-code→recovery-class registry are DEFERRED by Master Health V3 → new D18.
* Composer SPEC/transitive closure/Engine1 baseline authority: Matrix V5 says affected items are NOT CODABLE until the seven-field evidence bindings exist.

## 5. The 100 qualifiers
Word overlap is withdrawn as any kind of disposition. The CSV columns `lexical_support` and `hist_token_overlap` are **retrieval hints only**; every row stays `RAISE_FOR_SOURCE_OWNER_DISPOSITION`, unresolved, until source-owner evidence exists. The only INDEPENDENTLY_DERIVED facts are: historical hashes reproduce (100/100) and cited current line numbers exist (100/100). 65 rows cite no current line.

## 6. Full-component status by requirement (candidate code / author tests / connection)
Connection vocabulary: REAL = executes against the real counterpart · SIM = in-memory simulation of the counterpart · CONTRACT = typed objects/validators only · NONE. **The Gateway is Tracker-owned** (issuer TRACKER_CONSUMER_GATEWAY), so `gateway/` is Tracker candidate code whose stores are simulations; its real counterparts are the unqualified provider (D5) and FW/ML consumers that are not in this repository.
| Req | Candidate code | Author tests | Connection | Exact blocker (source) |
|---|---|---|---|---|
| TR-01 | prototype expression kernel; Annex writers | yes | NONE | NON-CONFORMANT to Annex arithmetic; SQE_OPSET_V1_1 needs A02 SPEC (C22: 0 operational bindings) |
| TR-02 | `quant_intake_adapter`, pipeline, authority_bridge | 44+ | REAL in-process baseline only | D1, D7; A08 not issued |
| TR-03/04 | `schema/*`, independent hashes (row, transition, status, delivered, manifest) | yes + 106 mutants | CONTRACT | code tables PROVISIONAL (D3); Gateway/Context hashes D13 |
| TR-05 | composer prototype | yes | CONTRACT | Composer SPEC closure (NOT CODABLE per Matrix V5); D6 §27/§7A |
| TR-06 | pipeline classification | yes | SIM | D8 predicate; no source statement found |
| TR-07 | `gateway/contracts.py`, `v038.py` | G1–G9, OB1/2, V0.38 rules, concurrency | SIM | D13, D15, D16, D12'; provider D5/D10 |
| TR-08 | `health/evidence.py`, **`health/envelope.py`** | yes | CONTRACT | D17, D18; no Health service |
| TR-09 | stateful verifier | yes | NONE | Q3–Q8 need opcode spec (D3) + oracle (D4) |
| TR-10 | chain_status, currentness, settlement | yes | SIM | D16 |
| TR-11 | coordination/* | yes | SIM | provider D5; atomicity D10 |
| TR-12 | `context/*` validators | yes | CONTRACT | D13, D14; ingestion owned by News Hub component |
| TR-13 | `fw/lanes.py` | F1–F3 | SIM/CONTRACT | D11 (reframed) |
| TR-14 | `ml/receiver.py` | F4–F6, M1–M4 | SIM/CONTRACT | no ML component in repo |
| TR-15 | instrument-qualified keys | yes | SIM | — |
Families: Q1–Q3 partial (annex-level) · Q4–Q8 NOT RUN (A02) · **Q9 slice done** · Q10 done at intake · Q11–Q12 pipeline tests · Q13 lane tests · Q14 done · Q15 done · Q16 done · Q17 done + B0 · Q18–Q20 structural import tests only · Q21–Q23 done.
Not implemented and why: fit production (Composer-owned); confluence merge (no source object); Gateway/Context/Health encodings (D13); REQUEST_AFTER_CUTOFF trigger (D12'); real provider adapter (D5); Context ingestion/mirror compare (News Hub component; Drive write forbidden).

## 7. Decisions still genuinely open (nothing here is assumed)
Unchanged and exact: D1, D2, D3, D4, D5, D6(§27/§7A), D7, D8, D9, D10, D13, D14, D15, D16, A07-1..4. Changed: D11 reframed (confirm "lane names are non-canonical; classifier is internal"); D12' = REQUEST_AFTER_CUTOFF trigger. New: **D17** News/Context Health profile home; **D18** Health thresholds/registry. Wording and consequences: docs/a07/A07_CONSOLIDATED_DECISIONS_AND_SOURCE_RECONCILIATION_R03.md (rows D1–D16, A07-1..4) plus the two rows below.
| ID | Decision | Who | Proposed wording | Blocks |
|---|---|---|---|---|
| D17 | Governed News/Context Health profile home | Health/News Hub owners | "News/Context Health profile = <doc id>; subjects = deliveries, coverage objects" | first FW/ML execution; Health REAL for Context |
| D18 | Health thresholds, flap limits, critical-set membership, reason→recovery-class registry | Health owner (policy) | registry version + values | Health recovery decisions beyond the three class names |

## 8. Proposed record edits (for the Manager; I cannot write Drive)
1. Journal/QC record: "Coder R04: PR #27 review findings 1–3 fixed at work commit bbed2f34…, tree 1521d45d…; 570 pytest, 453 unittest, 22/22 and 106/106 mutants; candidate code only; no gate effect."
2. Matrix/Build Plan clarification (source owner): "Fit production is Composer-owned; Tracker Q9/Q10 are verification slices" and "confluence lane names are descriptive; no merge object is defined".
3. Connected Contract owner: add byte layouts or an Annex extension for FINAL_RESOLUTION_HASH/PACKAGE_HASH/FINAL_PACKAGE_HASH (D13); define SETTLEMENT_DELAY value and REQUEST_AFTER_CUTOFF trigger (D16, D12'); resolve `<=` vs `<` (D14).
4. Master Health owner: promote News/Context Health profile home (D17); publish registry/thresholds (D18).
5. ML source owner: dispositions for the 100 qualifiers (A07-1).

## 9. Seven lenses
MATHEMATICAL=YES · DATA_SCIENCE=NA (no data/fit) · SOFTWARE_ARCHITECTURE=YES (concurrency, idempotence, table-driven enums) · ADVERSARIAL=YES (tag confusion, replay, caller-supplied flags) · TRADING_MICROSTRUCTURE=NA (no market data; settlement/half-open tested as logic) · GOVERNANCE=YES · FALSIFICATION=YES (128 mutants killed; one dead-code branch found and removed).

## 10. Independent review
Codex source review of PR #27 received and answered here; no acceptance claimed. Request: re-review this branch (work commit above).
