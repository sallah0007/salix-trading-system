# SALIX Trading System — Stage A Tracker

Candidate implementation of the full Trading Tracker component and its Composer, Consumer Gateway, Forward Walk, Machine Learning, Event/Context and Health interfaces.

**Status: implementation and review are in progress. Full Tracker closure and Owner sign-off are pending.** Simulated integrations and passing tests do not establish provider qualification, production readiness or live-trading authority. SALIX AI is a separate project.

## Start here

| Need | Location |
| --- | --- |
| Current work and resume point | [Persistent Tracker checklist](docs/closeout/TRK-STAGE-A-CHECKLIST.md) |
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

## Current pause checkpoint — 29 November 2026, Sydney

**Scope: full Tracker component and its interfaces. Work is paused for Claude's weekly allowance reset; Tracker is not closed.** The Owner said to continue after Monday's 7 o'clock reset. No AM/PM or automatic restart is inferred.

- Latest integrated code: [PR #167](https://github.com/sallah0007/salix-trading-system/pull/167), main code commit `c0988a4da74d92f44ad63f42681b12b61b462051`.
- PR #165: immutable ML view and exact consumed-row bridge; #166: per-row source-value L2 maintenance; #167: accepted-row completeness, snapshot/vintage and row-route lifecycle/recovery. These are candidate/SIM code events, with remaining review and governed-instance limits.
- Resume from the [persistent full-component checklist](docs/closeout/TRK-STAGE-A-CHECKLIST.md): ML view-path remainder; Composer/FW/ML/Health dependency review; per-clause source/code review; all 100 A07 qualifier comparisons; remaining Build Plan reads; combined closeout and final preservation check.
- GitHub API inventory: 158 remote heads across two complete pages (100 + 58). The latest five workspace branch tips are present on GitHub.
- Observed Claude workspace command output after PR #167: no tracked modifications, no untracked files, no stashes; a full local-branch ancestry check against `ls-remote` SHAs reported no branch unreachable from the remote heads. This is the observed checkpoint, not a guarantee about future edits.
- Earlier branches, preservation anchors, history and Rescue records remain retained. No cleanup or deletion was performed.

The [preservation index](docs/PRESERVATION_INDEX.md) records the exact latest branch SHAs and evidence limits. Documentation navigation updates after the code checkpoint do not change runtime code, grant acceptance or clear any gate.

The governed Drive records remain the source of design authority and formal gate decisions. A merge, passing test or this README clears no gate.
