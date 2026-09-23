# SALIX E-01 provider conformance harness

**Classification: TEST / EVIDENCE TOOLING ONLY.**

```
E01_CONFORMANCE_PROOF_TOOLING_AUTHORIZED     = YES
PRODUCTION_STAGE_A_IMPLEMENTATION_AUTHORITY  = NO
CODE_COMMISSION_AUTHORITY                    = NO
PROVIDER_ACCEPTED                            = NO
READY_TO_CODE                                = NO
```

This directory is not Stage A runtime code. It must never be imported by a
future `stage_a/` package, it is not
`stage_a/coordination/object_store_journal.py`, and **a green run here does not
set `PROVIDER_ACCEPTED`**. It produces evidence for a separate governed
decision, nothing else.

Governed basis, read at source by the implementer (not taken from any summary):

| Document | Drive ID |
|---|---|
| Manager reconciliation — Sydney S3 probes, 2026-09-23 | `18aMPP7LmtWMK7SrczDKB_OeYiDlS4whiOdbl9TM9YHg` |
| Frozen Build Plan (E01-H1, E01-M1, E07-M1, E-09, E10-M1, §15.1, §29A) | `1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo` |

## Why the harness is shaped this way

The Sydney probe found that a request carrying the **current ETag** with an
**old epoch body** was accepted by S3, and the rollback read back. So:

- object CAS answers *"has this object changed since I read it?"*;
- it never answers *"is this body a legal successor?"*.

Everything here follows from that. `authority_writer.py` validates epoch,
sequence, previous-head hash and transition chain **before** the conditional
write, and case `c05` demonstrates both halves: the writer refuses the stale
epoch, and the raw bypass path (current ETag, no validation) still accepts it.

**The writer is not the boundary.** A writer that ordinary callers can simply
decline to call is a convention, not a control. The enforceable boundary is a
provider-side permission denial, which is what `c13` attempts to prove and what
no amount of harness code can supply.

## Layout

| File | Role |
|---|---|
| `store_port.py` | the frozen adapter contract as a port, plus `raw_put_head` (bypass probe only) |
| `model.py` | HEAD / transition records and the E-09 key layout |
| `authority_writer.py` | restricted authority writer: validate-then-CAS, unknown-commit recovery, epoch advance, journal rebuild |
| `memory_store.py` | in-memory fake. `CAN_PROVE_PROVIDER_SEMANTICS = False` (E07-M1) |
| `s3_store.py` | live S3 adapter (boto3, imported lazily) |
| `cases.py` | the 15 commissioned cases, one namespace each |
| `evidence.py` | evidence records + deterministic SHA-256 manifest |
| `e01_s3_harness.py` | CLI: `selftest`, `live`, `verify-manifest` |
| `test_e01_*.py` | logic-only unit tests (no network, no boto3, no credentials) |

## Cases

| # | Case | Proven by |
|---|---|---|
| c01 | strong read-after-write | run-scoped probe key (never an authority key) + HEAD reads its own accepted write |
| c02 | immutable create-only transition write | overwrite with different bytes refused; bytes unchanged |
| c03 | conditional HEAD CAS | create-only genesis, duplicate create refused, valid commit accepted |
| c04 | stale ETag rejection | commit against a stale snapshot → provider precondition refuses (`CAS_LOST`) |
| c05 | **stale semantic epoch refused even with the current ETag** | writer refuses; raw bypass accepted it |
| c06 | strict sequence monotonicity | replay, gap and backwards all refused |
| c07 | previous-head / transition-chain validation | broken chain and broken head link refused; control accepted |
| c08 | unknown-commit recovery | lost response → authoritative reread; blind retry cannot mint a second acceptance |
| c09 | complete journal scan / rebuild | chain rebuilt backwards from HEAD; orphan candidate excluded and reported |
| c10 | delayed / stale fencing rejection | stale token refused after epoch advance; forged future token refused |
| c11 | competing-writer race | both writers validate against the same snapshot; exactly one CAS wins |
| c12 | rollback epoch fence | epoch advance, **rebuild consistent immediately after the fence**, pre-rollback token refused, post-rollback write accepted at sequence 1, rebuild consistent again |
| c13 | **bypass prevention** | ordinary principal's direct HEAD put must be `AccessDenied` |
| c14 | evidence capture | every record carries ts, operation, request/response metadata, outcome |
| c15 | deterministic manifest | recomputation is stable; one changed byte changes the digest |

`UNPROVEN` is a distinct status and is never reported as `PASS`. A run with any
`UNPROVEN` case is `TECHNICAL_INCOMPLETE`, and exits non-zero.

## Running the logic-only unit tests

No AWS account, no credentials, no boto3 required:

```bash
python -m unittest tests.provider_conformance.test_e01_writer_logic tests.provider_conformance.test_e01_cases_and_evidence -v
```

They are also collected by the repository sweep:

```bash
python -m unittest discover -s tests
```

## Running the harness against the in-memory fake

Exercises writer logic only. **Not provider evidence** (E07-M1):

```bash
python -m tests.provider_conformance.e01_s3_harness selftest --evidence-dir ./e01-evidence/selftest
```

## Running the live suite

Prerequisites:

- an **isolated** test bucket, no production objects (the Sydney bucket is
  `salix-e01-conformance-ap-southeast-2-7db6a275`, region `ap-southeast-2`);
- `python -m pip install boto3` in a throwaway environment;
- two AWS profiles: the authority writer and an ordinary caller. Without the
  second, `c13` is `UNPROVEN` and the run cannot be complete.

```bash
python -m tests.provider_conformance.e01_s3_harness live \
  --bucket salix-e01-conformance-ap-southeast-2-7db6a275 \
  --region ap-southeast-2 \
  --prefix salix-e01/run-001 \
  --evidence-dir ./e01-evidence/run-001 \
  --profile salix-e01-authority-writer \
  --ordinary-profile salix-e01-ordinary-caller \
  --ack-isolated-test-only
```

The live run refuses unless `--ack-isolated-test-only` is given **and** the
prefix contains `e01`, so it cannot be pointed at a production namespace by
accident.

Independent verification of a retained evidence package:

```bash
python -m tests.provider_conformance.e01_s3_harness verify-manifest ./e01-evidence/run-001
```

### Principal split for c13

The two profiles must differ in exactly one respect: only the authority writer
may write the HEAD key. Sketch only — the real policy is deployment
configuration and must be reviewed separately (see finding **F-2**):

```json
{
  "Effect": "Deny",
  "Principal": {"AWS": "arn:aws:iam::<account>:role/salix-e01-ordinary-caller"},
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::<bucket>/salix-e01/*/stage-a/v1/coordination/*/HEAD"
}
```

The ordinary caller keeps `s3:GetObject` and `s3:ListBucket`, so it can still
read the HEAD and the journal. If the ordinary principal's attempt comes back
`PreconditionFailed` rather than `AccessDenied`, `c13` **fails**: a precondition
refusal is not a permission boundary, because the same caller holding the
current ETag would have succeeded.

## What this harness does NOT prove

1. **It is not the production adapter.** It emulates the frozen contract.
2. **A fake proves nothing about a provider** (E07-M1). Selftest runs are
   labelled `is_provider_evidence = false`.
3. **It does not prove the IAM boundary is correctly deployed** beyond the
   single `c13` probe against whatever principal you hand it.
4. **It does not prove linearizability under real concurrency.** `c11` drives
   two writers from one process against one provider; it cannot simulate
   partitions, clock skew across hosts, or multi-region behaviour.
5. **Unknown-commit is induced, not natural.** `_LostResponseStore` performs a
   real provider write and then discards the response, which is what a client
   timeout looks like. A genuinely dropped in-flight request is not reproduced.
6. **The time source is harness-local.** `accepted_at_ns` comes from an
   injected counter, not the governed Tracker time source, so evidence
   timestamps order events within a run and are not governed time.
7. **Scan filtering is by key, not by content.** `from_sequence` is honoured
   against the key's 020d prefix. A key with no parseable sequence is always
   yielded, so a foreign or tampered object still reaches the rebuilder and
   fails closed instead of being hidden.
8. **409 vs 412.** Both map to "conditional write refused" for control flow,
   but the provider's own status and error code are preserved in the evidence
   so the distinction survives review.

## Governed epoch / sequence semantics (S-1 RESOLVED)

Manager reconciliation CR-036, 2026-09-23:

```
E01_SEQUENCE_POLICY                 = RESET_PER_EPOCH
EPOCH_ADVANCE_REPRESENTATION        = MUTABLE_HEAD_EPOCH_FENCE
EPOCH_ADVANCE_ACCEPTED_TRANSITION   = NO
```

- a new epoch's HEAD carries `sequence = 0`;
- the first accepted governed transition in that epoch is `sequence = 1`;
- an epoch advance is a durable HEAD fence. It does **not** journal an
  accepted transition, and no new canonical `EPOCH_ADVANCE` transition type was
  invented;
- no global sequence invariant exists. Sequence is monotonic *within* an epoch.

`CONTINUE_ACROSS_EPOCH` remains selectable via `--sequence-policy` as
**non-governing regression coverage only**.

### Rebuild is epoch-aware

`rebuild_from_journal()` walks the accepted chain by hash (never by listing
order) and applies:

- `HEAD.epoch` is authority. An accepted transition in a later epoch than the
  HEAD fails closed; no journal-only inference may promote the HEAD epoch.
- sequence is validated strictly **within** each epoch; the first accepted
  transition of an epoch is 1 under the governing policy.
- if `HEAD.sequence > 0`, the tip must be in `HEAD.epoch` with
  `tip.sequence == HEAD.sequence`.
- if `HEAD.sequence == 0`, the HEAD legitimately still names the previous
  epoch's tip. That is `REBUILD_CONSISTENT_EPOCH_FENCED_NO_NEW_TRANSITION`,
  not a defect. **This was the DC-038 correction**: the earlier version
  reported `CHAIN_TIP_SEQUENCE_NOT_HEAD` for a perfectly healthy journal
  immediately after a rollback fence — a false inconsistency on exactly the
  path a recovery depends on.
- orphan candidates stay excluded and reported; missing, tampered or
  unparseable accepted transitions fail closed with a diagnosis rather than
  crashing the rebuilder.
