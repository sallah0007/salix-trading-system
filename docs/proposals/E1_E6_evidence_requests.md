# Six first-slice external items — distinct evidence requests (E1–E6)

STATUS: requests only. Collected repository-derived evidence is in E2; it is NOT commissioning authority, NOT a host/provider selection, NOT an appointment. Source: Build Plan mapping disposition lists these six as external_missing, no_selected_actual_values.

| Item | Request (to whom) | Evidence needed | Collected here |
|---|---|---|---|
| E1 K3 subject/definition/target/invocation | A02 SPEC owner | subject, definition, target, invocation record | none |
| E2 host/worktree/base/tree/branch/path/BOM/rollback | Manager (commissioning) for authority; repo-derivable parts below | commissioning statement naming host and base | repository-derived: repo sallah0007/salix-trading-system; main 99e70a59f17de6dcf86f4a3159dd89435cf9b46c, tree ae966b3fc447eb91752debe67441158935052b07 (before R09); branch stage-a/tracker/completion-r09; paths stage_a/, tests/trk_stage_a/, docs/; Python 3.13 runtime; Build Plan E-10 supplies BOM + 10-step migration + rollback text (cited, not copied). External host/provider: UNAVAILABLE |
| E3 principal/grant/bootstrap/namespace/provider | Owner/Manager | grant-evidence records per D2 | shape check only |
| E4 clock domain/version/config + time-aware committing primitive | Manager / provider custodian | clock spec; primitive proof (PR16 harness cefe69e4f60e7f126dc215de819f0b1b47e24ab7 is candidate conformance TOOLING, PROVIDER_ACCEPTED=NO, older S3 acceptance does not cover R7 commit-time deadline semantics) | none |
| E5 service/build/output Health bindings + source/config rights/provenance | Health owner | seven-field bindings per interface | none |
| E6 consumed SPEC/transitive seven-field admission + gate/commission evidence | Manager | admission records | none |

D5/D10 candidate: object store with conditional writes per Build Plan E-01 (six adapter methods mapped in stage_a/coordination/provider_contract.py; classes linearizability, conditional write, rebuild, stale fence, unknown commit). Vendor NOT selected (deployment configuration). Sydney S3 probe finding (current ETag + old-epoch body accepted) means legality must be validated before CAS; probe document not opened in this pass (id 18aMPP7LmtWMK7SrczDKB_OeYiDlS4whiOdbl9TM9YHg).

## Source access record (exact failures, not absence)
Companion whole-chain matrix: ID not found in this session. Remaining section 7A: not opened. Build Plan E-03 / 29B bodies: headers/excerpts only. Hashes stated by sources were not recomputed for R7 (464724759119...a282) or the mapping disposition (ea9e7949...dfc0).
