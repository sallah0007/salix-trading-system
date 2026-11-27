# Finite decision package D2, D7, D13–D18 (PROPOSED)

STATUS: every item is a PROPOSAL for Manager / source-owner review. The Coder decides nothing, appoints nobody, and no merge or passing test clears any gate. Where a value is not in a source it is listed as MISSING, never filled.
Classification: M = Manager-settleable by recording in Drive within existing authority; O = genuinely Owner (policy/appointment authority not held by Manager); S = source-owner supplies content.

## D2 — principal / grant / trust anchor (O for appointment; S for evidence)
Proposed grant-evidence record (code: `stage_a.security.principals.GRANT_EVIDENCE_FIELDS`, shape check only):
`principal_id, role, grant_generation, bootstrap_trust_anchor_ref, namespace_id, operation_scope, issued_by_record_ref, validity/supersession`.
Role is one of the ten E-06 principals; R7-proposed `acceptance-origin` / `replica-commit-service` are refused while R7 is not operative. Appoints nobody. `authorize()` is a role capability lookup, not authentication or a grant.

## D7 — certifier (M/S)
Needed: certifier role, scope (which ERA / which producer), interval proof (from, to, evidence refs). Proposed record: `certifier_role, scope_ref, interval_start, interval_end, evidence_refs, issued_by_record_ref`. Source (Binding V1 section 4) says absence rides on governed scope-emptiness evidence but names no certifier: SILENT on who.

## D13 — wire layouts (S)
Proposed (not governed): per-record `layout_version` text; fields in the order the source section lists them; optional field = byte 0x00 absent / 0x01 + value (`_opt`); fixed-width integers big-endian; timestamps via `_ts`; ids via `_vid`; refs via `_ref`; enum values encoded as the code from the supplied versioned table. Records: Gateway outcome, Context decision record, Health envelope. Missing: source field orders for Gateway/Context/Health (not in sources read). Current code tables are provisional.

## D14 — cutoff vs fence (S, Connected Contract owner + News Hub owner)
Existing authority: Gateway strict `AVAILABLE_ASOF < SNAPSHOT_FENCE_TS` (not an Owner choice). News Hub V2 uses `<=` decision cutoff. Proposal: state that cutoff = fence for consumption, hence News Hub must use strict `<` at the fence, OR state the relation explicitly with a worked boundary example. Tests already pin the current divergence.

## D15 — reason -> status (M)
Candidate list: reasons naming absent producer, stale fence, unknown outcome, conflicting reuse -> NOT_READY (retryable); reasons naming prohibited principal, identity mismatch, non-final tampering, REQUEST_AFTER_CUTOFF without defined trigger -> REJECTED. Rationale: fail closed on unknown; unknown reasons are already REJECTED in code. Source V0.38 says NOT_READY is default and "stronger fail-closed" reasons are not enumerated: SILENT on the list.

## D16 — SETTLEMENT_DELAY (M/O)
Prerequisites: clock domain + version + config (E4), measured producer-to-store lag distribution with sample window, and a time-aware committing primitive. Proposed selection rule: delay = certified p-max lag over the measurement window + a margin the Owner states. Values: MISSING (no measurement exists). Immutable final outcome is existing authority.

## D17 — News/Context Health profile home (M)
Proposed home: a governed Drive document `NEWS_CONTEXT_HEALTH_PROFILE` with fields `profile_version, producers[], per-producer cadence, staleness window, critical flag, evidence_ref_field`. Master Health V3 requires the home before first FW/ML execution and does not name it.

## D18 — registry (S)
Proposed schema: `registry_version, reason_code, class (one of the three recovery classes), critical (bool), flap_limit, threshold`. Source-supplied: B0 envelope, anti-replay, silence -> STALE_NO_PRODUCER, three recovery class names. Still to select: thresholds, flap limits, critical-set membership, reason->class entries (deferred by Master Health V3).

## Manager vs Owner
M: D7 recording, D15 list, D17 home, D14 relation (with contract owners). O: D2 appointments, D16 margin value. S: D13 layouts, D18 values, D6 bindings.
