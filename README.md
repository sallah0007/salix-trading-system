# SALIX Trading System — Stage A Tracker

Candidate implementation of the full Trading Tracker component and its Composer, Consumer Gateway, Forward Walk, Machine Learning, Event/Context and Health interfaces.

**Status: implementation and review are in progress. Full Tracker closure and Owner sign-off are pending.** Simulated integrations and passing tests do not establish provider qualification, production readiness or live-trading authority. SALIX AI is a separate project.

## Start here

| Need | Location |
| --- | --- |
| Current integrated code | [main branch](https://github.com/sallah0007/salix-trading-system/tree/main) |
| Requirement status, evidence and remaining gaps | [Combined Tracker closeout](docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md) — use its section marked CURRENT; later code changes must also be checked |
| Requirement-by-requirement working register | [Clause reconciliation](docs/closeout/TRK-STAGE-A-R43-CLAUSE-RECONCILIATION.md) — the R43 filename is retained; read each row's evidence date and limits |
| Saved branches, preservation evidence and historical work | [Preservation index](docs/PRESERVATION_INDEX.md) |
| Coder authority and review rules | [CLAUDE.md](CLAUDE.md) |

## What the code covers

| Directory | Purpose |
| --- | --- |
| [stage_a/](stage_a/) | Tracker integration, quantitative materialization and verification, Gateway delivery, FW/ML boundaries, Context, Health, storage and recovery |
| [tracker_component/](tracker_component/) | Construction orders, claims, lifecycle coordination and audit support |
| [tracker_identity/](tracker_identity/) | Existing Tracker identity foundation used by the Stage A adapters |
| [tests/](tests/) | Unit, integration, negative-control, mutation and provider-conformance test tooling |
| [docs/](docs/) | Closeout, source citations, design proposals and preservation records |
| [coder_returns/](coder_returns/) | Historical coder returns; newer combined closeout records qualify earlier claims |
| [tools/](tools/) | Evidence and requirement-register utilities |

## Saved-code checkpoint — 28 November 2026, Sydney

The preservation check covered integrated code through [PR #83](https://github.com/sallah0007/salix-trading-system/pull/83), code commit `b8017d408c671e96a28fbb1eb25477cfef70d6ee`. PR #82 contains lifecycle race repairs; PR #83 adds the candidate status emitter/caller and audit support. This is a saved-code checkpoint, not a completion or acceptance decision.

The [170-commit preservation list](docs/PRESERVATION_R46_LOCAL_ONLY_SHAS.tsv) matches the 170 parents of remote preservation anchor `5ece0b4fc7b0979dc98fc8ada67161500e390269` on `preserve/r46-local-only-anchor`. The anchor preserves earlier work; it is not an alternative current implementation.

Use GitHub commit history and current branches for changes after this checkpoint. Only Claude's current workspace check can establish whether newer uncommitted or unpushed work exists.

The governed Drive records remain the source of design authority and formal gate decisions. A merge, passing test or this README clears no gate.
