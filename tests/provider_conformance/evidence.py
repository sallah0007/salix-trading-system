"""Evidence capture and the deterministic SHA-256 manifest.

Requirements 14 and 15 of the commission: retain timestamps, request metadata,
response metadata, ETags, object hashes and pass/fail; then produce a
deterministic SHA-256 manifest over the retained evidence.

DETERMINISM CONTRACT. The manifest is a pure function of the retained evidence
BYTES. Two parties who hold the same evidence directory compute the same
digest, and any single changed byte changes it. Timestamps live inside the
evidence (they must, it is evidence) and therefore two different RUNS have
different digests — that is the intent: the digest identifies one run's
evidence exactly.

Credentials are never recorded: only header names/values on an allow-list.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .canonical import canonical_bytes, sha256_hex

MANIFEST_ALGORITHM_ID = "SALIX-E01-EVIDENCE-MANIFEST-V1"
MANIFEST_FILENAME = "evidence_manifest.json"

# Response/request metadata that may be retained. Anything not listed is
# dropped, so an Authorization header or a session token cannot reach evidence.
ALLOWED_METADATA_KEYS = frozenset({
    "http_status", "etag", "version_id", "request_id", "extended_request_id",
    "error_code", "error_message", "content_length", "content_sha256",
    "if_match", "if_none_match", "key", "bucket", "region", "operation",
    "principal_label", "retry_count", "server_side_latency_ms",
})


def _filter_metadata(metadata: Optional[dict]) -> dict:
    if not metadata:
        return {}
    out = {}
    for key, value in metadata.items():
        name = str(key)
        if name in ALLOWED_METADATA_KEYS:
            out[name] = value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
    return out


@dataclass
class EvidenceRecorder:
    run_dir: str
    run_id: str
    provider_id: str
    can_prove_provider_semantics: bool
    records: List[dict] = field(default_factory=list)
    _seq: int = 0

    def __post_init__(self):
        os.makedirs(self.records_dir, exist_ok=True)

    @property
    def records_dir(self) -> str:
        return os.path.join(self.run_dir, "records")

    def record(self, *, case_id: str, operation: str, outcome: str,
               request_metadata: Optional[dict] = None,
               response_metadata: Optional[dict] = None,
               detail: str = "", extra: Optional[dict] = None) -> dict:
        self._seq += 1
        entry = {
            "run_id": self.run_id,
            "seq": self._seq,
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ts_ns": time.time_ns(),
            "provider_id": self.provider_id,
            "can_prove_provider_semantics": self.can_prove_provider_semantics,
            "case_id": case_id,
            "operation": operation,
            "outcome": outcome,
            "detail": detail,
            "request_metadata": _filter_metadata(request_metadata),
            "response_metadata": _filter_metadata(response_metadata),
            "extra": extra or {},
        }
        self.records.append(entry)
        path = os.path.join(self.records_dir, f"{case_id}.jsonl")
        with open(path, "ab") as handle:
            handle.write(canonical_bytes(entry) + b"\n")
        return entry

    def write_summary(self, summary: dict) -> str:
        path = os.path.join(self.run_dir, "run_summary.json")
        with open(path, "wb") as handle:
            handle.write(canonical_bytes(summary))
        return path

    def finalise(self) -> dict:
        manifest = compute_manifest(self.run_dir)
        with open(os.path.join(self.run_dir, MANIFEST_FILENAME), "wb") as handle:
            handle.write(canonical_bytes(manifest))
        return manifest


def compute_manifest(run_dir: str) -> dict:
    """Deterministic manifest over every retained file except the manifest.

    Independently recomputable: a reviewer runs
        python -m tests.provider_conformance.e01_s3_harness verify-manifest <dir>
    and compares the digest.
    """
    files: List[Dict[str, object]] = []
    for root, _dirs, names in os.walk(run_dir):
        for name in sorted(names):
            if name == MANIFEST_FILENAME:
                continue
            absolute = os.path.join(root, name)
            relative = os.path.relpath(absolute, run_dir).replace(os.sep, "/")
            with open(absolute, "rb") as handle:
                data = handle.read()
            files.append({"path": relative, "size": len(data),
                          "sha256": sha256_hex(data)})
    files.sort(key=lambda item: item["path"])
    body = {"algorithm": MANIFEST_ALGORITHM_ID, "files": files}
    return {"algorithm": MANIFEST_ALGORITHM_ID, "files": files,
            "evidence_digest": sha256_hex(canonical_bytes(body))}


def verify_manifest(run_dir: str) -> dict:
    """Recompute and compare against the stored manifest."""
    path = os.path.join(run_dir, MANIFEST_FILENAME)
    with open(path, "rb") as handle:
        stored = json.loads(handle.read().decode("utf-8"))
    recomputed = compute_manifest(run_dir)
    return {
        "stored_digest": stored.get("evidence_digest"),
        "recomputed_digest": recomputed["evidence_digest"],
        "match": stored.get("evidence_digest") == recomputed["evidence_digest"],
        "file_count": len(recomputed["files"]),
    }
