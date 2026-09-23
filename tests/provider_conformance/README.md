# SALIX E-01 S3 Conformance Harness

**Classification:** test/evidence tooling only. This directory is not Stage A runtime code and does not grant implementation, provider-acceptance, FW, ML, or production authority.

This harness exists to test the frozen E-01 authority semantics against an isolated S3 namespace. It must never be imported by future `stage_a/` production modules.

## Required live environment

- AWS account authenticated with short-lived credentials (CloudShell is acceptable).
- Isolated private S3 bucket.
- Fixed AWS region recorded in evidence.
- No production SALIX objects.
- A restricted writer principal for the authority-bearing HEAD path.
- Ordinary test callers must be unable to write the authoritative HEAD directly.

## Frozen E-01 cases covered

1. strong read-after-write;
2. create-only immutable transition write;
3. conditional HEAD CAS;
4. stale ETag rejection;
5. **semantic stale-epoch rejection even when the request has the current ETag**;
6. sequence monotonicity;
7. transition-chain/hash validation;
8. unknown-commit resolution by rereading HEAD, never blind retry;
9. complete immutable journal scan/rebuild;
10. delayed/stale fencing rejection;
11. competing-writer race;
12. rollback epoch advance followed by rejection of pre-rollback tokens.

## Safety boundary

The harness keeps the authority-writer rules in this test-only path. It does not create `stage_a/coordination/object_store_journal.py` or any business/runtime package.

A passing test against S3 is still not enough by itself to set `PROVIDER_ACCEPTED = YES`. The evidence package must be retained, independently reviewed, and then reconciled through the separate code-commission readiness gate.

## Usage

Install the test dependency in an isolated environment:

```bash
python -m pip install boto3
```

Run logic-only unit tests:

```bash
python -m unittest tests.provider_conformance.test_e01_writer_logic -v
```

Run the live suite:

```bash
python tests/provider_conformance/e01_s3_harness.py \
  --bucket YOUR_ISOLATED_TEST_BUCKET \
  --region ap-southeast-2 \
  --prefix salix-e01/run-001 \
  --evidence-dir ./e01-evidence/run-001
```

The live harness refuses to run unless the prefix contains `e01` and `--ack-isolated-test-only` is supplied.

## Restricted-writer IAM boundary

The live test should use two identities:

- **ordinary caller**: may read the HEAD and immutable journal but cannot `PutObject` to the HEAD key;
- **authority writer**: the only principal permitted to conditionally update the HEAD.

The exact IAM/bucket-policy implementation is deployment configuration and must be reviewed separately. The important invariant is enforceable bypass prevention: ordinary runtime callers cannot directly overwrite the authoritative HEAD even if they know its current ETag.

## Evidence

Each operation writes JSONL records containing timestamp, operation, request metadata, response metadata, ETag, content hash, and pass/fail status. The run also writes a SHA-256 manifest over the evidence files.
