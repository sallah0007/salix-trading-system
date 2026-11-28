# R53 — declared INVARIANTS stage + registry-bound schema identity (before canonical row acceptance)

Source cited by ID only (no text copied): Parent p31, p181 INVARIANT_SET, p418 INVARIANT_SET_REF, p444 INVARIANTS_DECLARED, p457–465 (INVARIANT CHECKS p463); Annex III p306 INVARIANT_REF (optional, meaningful when present).

## What was built (generic wiring only; no invariant grammar/math invented)
- `verify_row_step(..., schema_registry=None, invariant_resolver=None)`.
  - Schema identity: the schema is compared with what a SUPPLIED registry returns for `row.state_schema_version`. None supplied -> `UNBOUND_HELD`; not registered -> `NOT_REGISTERED_HELD`; differing -> FAIL (`REGISTRY_MISMATCH`). Held => INSUFFICIENT_EVIDENCE, never PASS.
  - Invariants: unique `INVARIANT_REF`s from the schema. None declared => `NONE_DECLARED`. Declared but resolver absent/None/raising => `UNRESOLVED_HELD` (INSUFFICIENT_EVIDENCE). Resolved hash != ref.target_hash => FAIL. Program must return exactly `True` (False = RULE_FAILED, non-bool = RULE_NOT_BOOLEAN).
- `RowAcceptor._bind_evidence` additionally refuses a result whose subject is not `schema_identity == REGISTRY_BOUND` and `invariants in {EVALUATED_PASS, NONE_DECLARED}`.

## Tests / negative controls
genuine rule-pass; known rule-fail; unresolved applicable rule; wrong identity/hash/registry; refusals leave the journal empty and the SAME row is accepted after the rule is resolved (retry), replay returns the same record. Mutants killed: rule-fail ignored, hash pin, unresolved->ok, registry mismatch ok, unbound->ok, both acceptor checks.

## Honest limits (EVIDENCE)
- Two verifier mutants SURVIVE as shadowed/equivalent: the `held and PASS` guard in `done()` (the later `if held:` return already covers it) and the `exp is None` branch (earlier failing checks already yield FAIL). Kept as defence in depth.
- SIM rules only; no real invariant program/grammar/provider is admitted. Registry and resolver are supplied ports; the in-process receipt is a label, not a security boundary.
- Nothing here clears any gate/hold; a merge or passing test authorizes nothing.
