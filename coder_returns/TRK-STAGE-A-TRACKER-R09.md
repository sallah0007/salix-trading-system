# TRK-STAGE-A-TRACKER-R09 — completion pass (candidate code + PROPOSALS; NOT a governance event; Tracker NOT labelled complete)

CODER FINDING != SALIX DECISION. Merge/tests/§2A clear no gate, hold, acceptance or stage. Posture as last read, unchanged: A07/COVERAGE OPEN; P12/N2 UNSATISFIED; A02 Class B HOLD; QC34 ALERT(HOLD); A08 READY_TO_CODE NO; Stage A HOLD. Drive untouched. SALIX AI separate. Author-only evidence; no independent review. Real dependencies remain, so the component is not complete.

## 1. Implementation delta (all CONTRACT/SIM; only in-process tracker_identity is REAL)
| Change | Where | Effect |
|---|---|---|
| Seven-field shape check | `stage_a/binding/producer_binding.py` | missing/unknown/empty field or non-sha256 hash refused. Shape only, not admission |
| Descriptor lookup boundary | `stage_a/fw/descriptor_crosswalk.py` | `require_real_binding` no longer returns arbitrary objects (Codex point 5); labelled DOCUMENTARY_LOOKUP_ONLY; MISSING/INTERNAL fields still refused |
| Role lookup labelled | `stage_a/security/principals.py` | `LOOKUP_ONLY_NOT_AUTHENTICATION`; `check_grant_evidence_shape` (proposed 8-field record; appoints nobody) |
| Health | `stage_a/health/envelope.py` | second `ML_LOCAL_STATE` field refused; `attribute_failure` keeps coexisting LOCAL_FAILURE and BLOCKED_BY_UPSTREAM separate (own R08 defect, conceded) |
| E-01 provider contract | `stage_a/coordination/provider_contract.py` | six E-01 methods mapped to ObjectStore; five required conformance classes; `require_provider_proof` refuses without named provider and all-PASS; SIM probe only |
## 2. Proposals (docs/proposals/, not runtime authority)
D6 27 absent §27 fields with producer/consumer/derivation/rule/validation; FW ten descriptors; ML creator/joins/qualifiers; finite D2/D7/D13–D18 package with M/O/S classification; E1–E6 evidence requests with repository-derived E2 evidence.
## 3. Tests (DERIVATION_CLASS = INDEPENDENTLY_DERIVED, REPRODUCIBLE_BY_MANAGER = YES)
602 pytest pass; 453 unittest pass; sweeps: base 22/22, boundaries 106/106, r05_r06 6/6, r08 14/14, r09 17/17 killed, 0 survivors. Mid-pass survivors (empty grant field; probe return) were closed with tests/code simplification. Doc drift tests were shown able to fail by editing the docs. Commands: `docs/PRESERVATION_INDEX.md` §5.
## 4. Remaining dependencies (source/role/proposed resolution/affected action)
A02 SPEC (D3/D4, A02 owner) -> TR-01/09; Composer seven-field binding (Manager/Composer owner; D6 record) -> Composer rows; FW ten bindings (Manager) -> FW REAL; D2 appointments (Owner); D5/D10 provider qualification (provider custodian; PR16 harness candidate, PROVIDER_ACCEPTED=NO); D7 certifier; D13 layouts; D14 relation; D15 list; D16 values (needs E4 measurement); D17 home; D18 registry; A07-1..4; 100 ML qualifiers at RAISE_FOR_SOURCE_OWNER_DISPOSITION (no acceptance awarded).
## 5. Not opened / failed access
Companion whole-chain matrix (ID not found); remaining §7A; E-03/§29B bodies beyond excerpts; Sydney S3 probe doc; R7/mapping hashes not recomputed.
