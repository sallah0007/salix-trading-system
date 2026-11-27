# TRK-STAGE-A-TRACKER-R01 — Coder return to Manager (finished product + gaps + open decisions)

Author: Claude (Trading Bot 7), under Owner delegation (CLAUDE.md §2A). Open for Manager challenge.
CODER FINDING != SALIX DECISION. Nothing here clears a gate, hold, acceptance or stage. Drive was not touched.

## What was built (one delivery, whole component)
`stage_a/` — 46 Python files, 1,973 lines, stdlib only: shared foundations; storage; fenced object-store journal
(HEAD CAS + epoch fencing + orphan semantics + unknown-commit recovery); replay / AS_KNOWN-vs-EVENTUAL currentness /
rebuildable read model; bounded replay scheduler; generic expression kernel (schema, canonical bytes, three hashes,
capability extraction, binary64 evaluator, fit-generation refs); Tracker intake → certification → stateful
materializer (batch + incremental) → **independent** verifier (own encoder/hasher/traversal/reference evaluator,
verifier-authored probe, bit-exact cross-check) → canonical acceptance → publishable/withdrawn; baseline bridge.

## Evidence (CLAUDE.md §5)
* DERIVATION_CLASS = INDEPENDENTLY_DERIVED (run by me, this session). EXACT_INPUTS = branch `stage-a/tracker/full-component`
  on base `405fd085a8624832466b55f95ab78e8deef7659b`. METHOD: `python3 -m pytest tests -q` → 484 passed;
  `python3 -m unittest discover -s tests` → 453 OK; `python3 tests/trk_stage_a/mutation_sweep.py` → 22/22 mutants killed
  (one initially survived — "PUBLISHABLE may repeat" — and a test was added). REPRODUCIBLE_BY_MANAGER = YES.
* Evidence-state breakdown: AUTHORING COMPLETE = YES for the scope above. COMPONENT VERIFIED = author-tested only,
  **not independently reviewed** (materializer and verifier share an author). PROVIDER/DEPENDENCY QUALIFIED = NO.
  INTEGRATED/OPERATIONAL = NO.

## Gaps found and what I did
| # | Gap | Action |
|---|-----|--------|
| G1 | Baseline construction authority is hard-False and no resolver existed | Built a journal-verified fail-closed resolver (`authority_bridge`, `ClaimService.authorizes`). **Not installed.** |
| G2 | Only an in-memory journal simulator existed | Built fenced object-store journal; unqualified against any real provider |
| G3 | Cross-journal authority TOCTOU | Authority is spent first with a commit-point check (consume), acceptance carries it as witness; fence checked before spending; crash-retry idempotent |
| G4 | ERA_1 structural absence cannot proceed and **nothing produces certified `ABSENT`** | NOT fixed — see D7. Production happy path is therefore unreachable until a certified-absence producer exists |
| G5 | Verification results could be misread unqualified | Typed, scope-qualified result with no truthiness |
| G6 | Stale sidecar reads | Read model refuses when not at journal head |
| G7 | Test-suite gap (surviving mutant) | Added repeated-PUBLISHABLE / publish-after-withdraw / duplicate-acceptance replay tests |
| G8 (withdrawn) | I briefly suspected tests/test_tracker_component.py ran 0 tests | Wrong: it is pytest-style; 31 pass under pytest. Withdrawn |

## Open decisions (named, not built around)
* D1 Installing the resolver into the baseline seam is a governance decision (it makes production claims authority-bearing).
* D2 Order-signer role record; `TrustAnchor` is configurable, tests assume `MANAGER`.
* D3 Manifest schema, opcode set and binary64 numeric spec are implementation-defined; source admission (A02 SPEC) OPEN.
* D4 COV-R02 / oracle independence: expected values are self-generated; independent expected-byte review OPEN.
* D5 R5 provider: `ObjectStore` port unqualified; read model uses sqlite as a stand-in for Postgres.
* D6 Exact Composer §27/§7A field mapping (`BuildPackage`), §28 compound-field split and cross-field rules (author judgement).
* D7 Producer of certified global `ABSENT` lookup (G4).
* D8 TR-06 routing predicate: implemented as an explicit `quant_feature_requested` flag.
* D9 stage_a also depends on `tracker_component` (plan said tracker_identity only).
* D10 Cross-journal atomicity is by ordering + witness, not a multi-key transaction; a provider-level transaction would be stronger.

## Not built (outside component or unresolved)
Confluence (Q13), fit production, Health/B0 evaluation (only an event sink), Gateway/FW/ML delivery (TR-07/13/14),
real provider adapters, G1–G9/F/M integration tests (remain NOT RUN).

## Seven-lens declaration
MATHEMATICAL=YES (binary64 spec, undefined/non-finite semantics) · DATA_SCIENCE=NA (no fitting/data; fit-ref boundary only) ·
SOFTWARE_ARCHITECTURE=YES · ADVERSARIAL=YES (fenced writers, poisoned artifacts, replay, tampering) ·
TRADING_MICROSTRUCTURE=NA (no market data/execution; causality of the kernel only) · GOVERNANCE=YES ·
FALSIFICATION=YES (22 mutants, verifier-side and producer-side defect injection).
