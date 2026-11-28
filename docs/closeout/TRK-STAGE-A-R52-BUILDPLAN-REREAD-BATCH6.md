# R52 Build Plan re-read — batch 6 (capture lines 4260–5234: §27 TR-06..TR-15, §28, §28A, §29, §29A E-01..E-10, §29B, §30)

CODER FINDING != SALIX DECISION. Docs only. No governing-source text is copied; clauses are cited by section/range and paraphrased.
DERIVATION_CLASS = INDEPENDENTLY_DERIVED (read line by line, non-blank lines, capture `/tmp/buildplan.txt` 5234 lines) for the clause content; repo comparisons are by direct file read.
EXACT_INPUTS = Build Plan capture lines 4260–5234; repo main 964e3b0 files `stage_a/storage/keys.py`, `stage_a/coordination/object_store_journal.py`.
METHOD = sequential read; each clause compared with the named repo owner by reading the owner's code (not by name).
REPRODUCIBLE_BY_MANAGER = YES (same line range; same two repo files).

## Findings
1. **E-09 key layout vs repo layout (MEDIUM, divergence, not a defect claim).** The E-09 candidate lays coordination objects out as a versioned prefix / namespace / per-epoch transitions path with a zero-padded 20-digit sequence and the transition hash. The repo uses `journal/<ns>/<seq020d>/<hash>` and `head/<ns>` (keys.py). The 20-digit sequence-plus-hash form matches; the version prefix, the per-epoch path segment and the file suffix do not. Authority in both is the hash chain, not listing order, so this is a layout/migration question only. E-09 is itself "Manager decision, candidate, READY_TO_CODE = NO", so I did not move keys. Irreducible choice: whether the candidate layout is adopted (would need a key migration that preserves existing journal objects). Owner role: Manager. Consequence if not adopted: layout stays implementation-internal. Recommendation: keep current keys; record divergence.
2. **E-01 HEAD content (LOW).** E-01 says HEAD holds epoch, sequence, accepted transition hash and the previous-head hash. The repo HEAD doc holds seq, hash, epoch. The previous link lives in each journal record (`prev_hash`), and replay verifies the chain, so the previous-head hash is recoverable but not stored in HEAD itself. Not changed (would alter the HEAD byte shape that existing journals use). Owner role: Manager. Recommendation: accept as equivalent only if Manager says a record-level `prev_hash` satisfies the clause; otherwise a HEAD-shape change is a versioned migration.
3. **E-05 transition index carries `accepted_at` (relevant to the journal-vs-typed relation).** The read-model plan indexes transitions by (subject, accepted_at) and pending rows by event time. So the plan expects a per-transition accepted time to exist as a queryable field. This supports the optional `canonical_accepted_at` journal field added in #123/#127 (legacy records: time UNKNOWN, not backfilled). It does not define the time source or its clock; those stay held.
4. **E-09 health key uses `available_asof_ns`.** Confirms nanosecond units for the as-of component (consistent with the Annex INT64 ns fact). Not a clock appointment.
5. **E-02 sidecar rule.** Sidecar metadata is outside the governed hash unless the artifact contract says otherwise. `storage/artifact_sidecar.py` exists; I did not re-verify its field list against E-02 in this batch (name-only; INSUFFICIENT_EVIDENCE for equivalence).
6. **E-04/E-06 principal separation.** Ten worker roles and ten principals are listed. I did not verify enforcement per principal in this batch; the existing separated-handler path covers acceptor-vs-materializer; the remaining principals are NOT reviewed here.
7. **§28A / §29B / §30 status.** All E-01..E-10 are marked closed as Manager candidates, READY_TO_CODE = NO, independent Coder review pending. Under the standing §2A delegation this is not a re-permission question; nothing here clears any gate.
8. **§27 TR-06..TR-15.** Each row names owner modules and test families; the matching source-side/code comparison stays in the combined closeout and earlier batches. Not re-derived here beyond reading.

## Not done in this batch
Build Plan ranges still to read line by line: 140–2230, 2440–2960, 3232–3335. Health Profile V1 not yet read.

## Lens declaration
MATHEMATICAL=NA (no arithmetic claim); DATA_SCIENCE=NA; SOFTWARE_ARCHITECTURE=YES; ADVERSARIAL=NA (no code change); TRADING_MICROSTRUCTURE=NA; GOVERNANCE=YES; FALSIFICATION=YES (divergences stated both ways).
