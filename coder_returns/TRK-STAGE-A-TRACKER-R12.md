# TRK-STAGE-A-TRACKER-R12 - Coder return (continuing the full Tracker assignment)

CODER FINDING != SALIX DECISION. Code events only; no gate, hold, acceptance or stage is cleared. Posture unchanged (A07 OPEN, P12/N2 UNSATISFIED, A02 Class B HOLD, QC34 ALERT(HOLD), A08 READY_TO_CODE NO, Stage A HOLD). The Tracker is NOT complete. R11's statement that the remaining component work was done was wrong; withdrawn.
Authority: CLAUDE.md section 2A (this repository only); Drive read-only; no principal/provider/host appointed; no live or SALIX AI action.

## Rows actioned (implementation + call path + evidence)
1. BOTH (defect from Manager review, reproduced independently by Manager): `gateway/v038.check_both_separation` now requires CONSUMER_ID == "FW" for the FW lane and "ML" for the ML lane (V0.37 H1 CONSUMER_ID = FW | ML | other), lane PACKAGE_CLASS, TARGET_CONSUMER == BOTH, each lane H1-checked, distinct binding/package/hash fields. `check_binding_matches_identity` binds consumer and manifest/dataset binding id to the resolution identity. The suffixed request key is REMOVED: the store keys requests by (consumer_id, REQUEST_ID) (H1: REQUEST_ID is consumer-local), so caller request ids are unchanged and no alias namespace exists. Tests: test_r11_both.py (swapped/unknown/arbitrary labels, cross-lane binding, replay, rebinding, isolation, the reproduced suffix-collision case). Sweep r11b 17/17.
2. Status projection: `tracker/status_projection.py` + gateway fail-closed on non-committed status. Tests test_r12_status_projection.py (10). Unresolved clause: record->StatusFact mapping (required decoder, no default).
3. Ceilings/capability: `composer/expression/ceilings.py`, wired in `quant_intake_adapter.admit` (dimensions RESOURCE_CEILING, CAPABILITY_DECLARATION); no numeric value chosen; silent MAX_NODES/MAX_WINDOW removed. Tests test_r12_ceilings.py.
4. Operators: `sqe_opset.py` (comparison, EQ_CANONICAL, SELECT, elementwise, FIXED_SUM/DOT; no-FMA proven against exact-rounding Fraction arithmetic). Reference semantics only; not claimed as full SQE_OPSET_V1_1.
5. Blast radius: `health/blast_radius.py` (OB2 control; proven vs undetermined). 6. ML augmented lineage: `ml/receiver.check_fw_augmented`.
Evidence: DERIVATION_CLASS INDEPENDENTLY_DERIVED; full suite 709 passed locally; targeted sweeps: r11b 17/17, r12 39/39 (1 documented equivalent); reused earlier green evidence for unchanged code. REPRODUCIBLE_BY_MANAGER = YES.

## Exact blockers (source-grounded)
- context/resolver.py: resolver input/output contract not defined in any source read. FW return lineage: FW return record fields not defined (group 2). Blast-radius action for UNDETERMINED consumers: policy rule missing. Multi-branch CASE tie rule; numeric opcode table; program byte grammar; MAX_STATE_ELEMENTS counting; class-structure compatibility: missing semantic rules. D13 hash bytes, D14-D18: search incomplete (INSUFFICIENT_EVIDENCE). Status-event record mapping and origin principal: unresolved R7 clause; not appointed.
Claude authored; independent review is still required.
