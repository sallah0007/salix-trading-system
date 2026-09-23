"""CLI runner for the E-01 provider conformance harness.

    python -m tests.provider_conformance.e01_s3_harness selftest
    python -m tests.provider_conformance.e01_s3_harness live \
        --bucket salix-e01-conformance-ap-southeast-2-7db6a275 \
        --region ap-southeast-2 --prefix salix-e01/run-001 \
        --evidence-dir ./e01-evidence/run-001 --ack-isolated-test-only
    python -m tests.provider_conformance.e01_s3_harness verify-manifest <dir>

A `live` run refuses unless the prefix names e01 AND --ack-isolated-test-only is
given, so the harness cannot be pointed at a production namespace by accident.

PROVIDER_ACCEPTED is never emitted by this tool. The verdict it prints is
technical only: evidence for a separate governed decision.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from typing import List

from .cases import FAIL, PASS, UNPROVEN, CaseContext, CaseResult, run_all
from .evidence import EvidenceRecorder, compute_manifest, verify_manifest
from .memory_store import MemoryObjectStore


def _verdict(results: List[CaseResult], store) -> dict:
    counts = {PASS: 0, FAIL: 0, UNPROVEN: 0}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    if counts[FAIL]:
        technical = "TECHNICAL_FAIL"
    elif counts[UNPROVEN]:
        technical = "TECHNICAL_INCOMPLETE"
    else:
        technical = "TECHNICAL_PASS"
    return {
        "counts": counts,
        "technical_verdict": technical,
        "provider_id": store.PROVIDER_ID,
        "can_prove_provider_semantics": bool(store.CAN_PROVE_PROVIDER_SEMANTICS),
        # E07-M1: a fake can never prove E-01, whatever its results say.
        "is_provider_evidence": bool(store.CAN_PROVE_PROVIDER_SEMANTICS),
        "PROVIDER_ACCEPTED": "NO",
        "note": ("Technical result only. PROVIDER_ACCEPTED and READY_TO_CODE are "
                 "governed decisions taken elsewhere; this tool never sets them."),
    }


def _run(store, *, prefix: str, evidence_dir: str, ordinary_store=None,
         ordinary_principal_label: str = "", sequence_policy: str = "RESET_PER_EPOCH"
         ) -> int:
    run_id = "run-" + uuid.uuid4().hex[:12]
    recorder = EvidenceRecorder(run_dir=evidence_dir, run_id=run_id,
                                provider_id=store.PROVIDER_ID,
                                can_prove_provider_semantics=bool(
                                    store.CAN_PROVE_PROVIDER_SEMANTICS))
    ctx = CaseContext(store=store, prefix=prefix, run_id=run_id, recorder=recorder,
                      ordinary_store=ordinary_store,
                      ordinary_principal_label=ordinary_principal_label,
                      sequence_policy=sequence_policy)
    results = run_all(ctx)
    verdict = _verdict(results, store)
    summary = {
        "run_id": run_id,
        "prefix": prefix,
        "sequence_policy": sequence_policy,
        "results": [{"case_id": r.case_id, "title": r.title,
                     "requirement": r.requirement, "status": r.status,
                     "detail": r.detail, "facts": r.facts} for r in results],
        "verdict": verdict,
    }
    recorder.write_summary(summary)
    manifest = recorder.finalise()

    for result in results:
        print(f"{result.case_id} {result.status:<8} {result.title} :: {result.detail}")
    print("-" * 78)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print("evidence_dir     =", evidence_dir)
    print("evidence_digest  =", manifest["evidence_digest"])
    print("evidence_files   =", len(manifest["files"]))
    return 0 if verdict["technical_verdict"] == "TECHNICAL_PASS" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="e01_s3_harness")
    sub = parser.add_subparsers(dest="command", required=True)

    selftest = sub.add_parser("selftest", help="run against the in-memory fake "
                                               "(NOT provider evidence)")
    selftest.add_argument("--evidence-dir", default="./e01-evidence/selftest")
    selftest.add_argument("--sequence-policy", default="RESET_PER_EPOCH")

    live = sub.add_parser("live", help="run against the configured provider")
    live.add_argument("--bucket", required=True)
    live.add_argument("--region", required=True)
    live.add_argument("--prefix", required=True)
    live.add_argument("--evidence-dir", required=True)
    live.add_argument("--profile", default=None,
                      help="AWS profile for the AUTHORITY WRITER principal")
    live.add_argument("--ordinary-profile", default=None,
                      help="AWS profile for an ORDINARY caller. Required to "
                           "decide case c13; without it c13 is UNPROVEN.")
    live.add_argument("--sequence-policy", default="RESET_PER_EPOCH")
    live.add_argument("--ack-isolated-test-only", action="store_true")

    verify = sub.add_parser("verify-manifest")
    verify.add_argument("evidence_dir")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        print("MEMORY FAKE: exercises writer logic only. E07-M1 — an in-memory "
              "fake can never prove E-01 provider semantics.")
        return _run(MemoryObjectStore(), prefix="selftest",
                    evidence_dir=args.evidence_dir,
                    sequence_policy=args.sequence_policy)

    if args.command == "verify-manifest":
        report = verify_manifest(args.evidence_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["match"] else 1

    if not args.ack_isolated_test_only:
        print("REFUSED: --ack-isolated-test-only is required for a live run.",
              file=sys.stderr)
        return 2
    if "e01" not in args.prefix.lower():
        print("REFUSED: live prefix must contain 'e01' (isolated test namespace).",
              file=sys.stderr)
        return 2

    from .s3_store import S3ObjectStore
    store = S3ObjectStore(bucket=args.bucket, region=args.region,
                          profile=args.profile, principal_label="authority-writer")
    ordinary = None
    if args.ordinary_profile:
        ordinary = S3ObjectStore(bucket=args.bucket, region=args.region,
                                 profile=args.ordinary_profile,
                                 principal_label="ordinary-caller")
    return _run(store, prefix=args.prefix, evidence_dir=args.evidence_dir,
                ordinary_store=ordinary,
                ordinary_principal_label=args.ordinary_profile or "",
                sequence_policy=args.sequence_policy)


if __name__ == "__main__":
    raise SystemExit(main())
