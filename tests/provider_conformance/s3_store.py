"""S3 adapter for the live conformance run. boto3 is imported lazily.

Conditional semantics used:
    create-only     PutObject with If-None-Match: "*"
    CAS update      PutObject with If-Match: "<etag>"

Error mapping is deliberately narrow. An outcome that is NOT a clean success
and NOT a recognised refusal becomes UnknownWriteOutcome, which forces the
E01-M1 reread path rather than a silent assumption either way.
"""
from __future__ import annotations

from typing import Iterator, Optional, Tuple

from .canonical import sha256_hex
from .store_port import (AccessDenied, NotFound, ObjectRead, ObjectStorePort,
                         PreconditionFailed, UnknownWriteOutcome, WriteResult)

PRECONDITION_CODES = {"PreconditionFailed", "ConditionalRequestConflict",
                      "InvalidRequest412"}
NOT_FOUND_CODES = {"NoSuchKey", "404", "NotFound"}
DENIED_CODES = {"AccessDenied", "AllAccessDisabled", "403", "Forbidden",
                "UnauthorizedOperation"}


class S3ObjectStore(ObjectStorePort):
    CAN_PROVE_PROVIDER_SEMANTICS = True
    PROVIDER_ID = "aws-s3"

    def __init__(self, *, bucket: str, region: str, profile: Optional[str] = None,
                 principal_label: str = "authority-writer"):
        import boto3                      # lazy: unit tests never need boto3
        session = (boto3.Session(profile_name=profile, region_name=region)
                   if profile else boto3.Session(region_name=region))
        self.client = session.client("s3", region_name=region)
        self.bucket = bucket
        self.region = region
        self.principal_label = principal_label
        self.last_response_metadata: dict = {}

    # -- plumbing --------------------------------------------------------
    def _meta(self, response: dict) -> dict:
        raw = (response or {}).get("ResponseMetadata", {})
        headers = raw.get("HTTPHeaders", {}) or {}
        meta = {
            "http_status": raw.get("HTTPStatusCode"),
            "request_id": raw.get("RequestId"),
            "extended_request_id": headers.get("x-amz-id-2"),
            "etag": (response or {}).get("ETag") or headers.get("etag"),
            "version_id": (response or {}).get("VersionId"),
            "principal_label": self.principal_label,
            "bucket": self.bucket,
            "region": self.region,
        }
        self.last_response_metadata = meta
        return meta

    def _raise_mapped(self, exc, *, operation: str):
        from botocore.exceptions import (ClientError, ConnectionError as BotoConnError,
                                         ConnectTimeoutError, ReadTimeoutError)
        if isinstance(exc, (ConnectTimeoutError, ReadTimeoutError, BotoConnError)):
            # The request may or may not have been applied. E01-M1 requires an
            # authoritative reread, so this must never be reported as a failure.
            raise UnknownWriteOutcome(f"{operation}:{type(exc).__name__}:{exc}") from exc
        if isinstance(exc, ClientError):
            error = exc.response.get("Error", {})
            code = str(error.get("Code", ""))
            status = str(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", ""))
            self._meta(exc.response)
            if code in PRECONDITION_CODES or status == "412" or status == "409":
                raise PreconditionFailed(f"{operation}:{code}:{status}") from exc
            if code in NOT_FOUND_CODES or status == "404":
                raise NotFound(f"{operation}:{code}") from exc
            if code in DENIED_CODES or status == "403":
                raise AccessDenied(f"{operation}:{code}:{status}") from exc
            raise UnknownWriteOutcome(f"{operation}:UNMAPPED:{code}:{status}") from exc
        raise UnknownWriteOutcome(f"{operation}:{type(exc).__name__}:{exc}") from exc

    def _get(self, key: str, *, operation: str) -> ObjectRead:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            data = response["Body"].read()
        except Exception as exc:
            self._raise_mapped(exc, operation=operation)
        meta = self._meta(response)
        meta["content_sha256"] = sha256_hex(data)
        meta["content_length"] = len(data)
        return ObjectRead(key=key, data=data, version=response["ETag"], metadata=meta)

    def _put(self, key: str, data: bytes, *, operation: str, **conditions) -> WriteResult:
        try:
            response = self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                                              **conditions)
        except Exception as exc:
            self._raise_mapped(exc, operation=operation)
        meta = self._meta(response)
        meta["content_sha256"] = sha256_hex(data)
        meta["content_length"] = len(data)
        meta.update({k.lower(): v for k, v in conditions.items()})
        return WriteResult(key=key, version=response["ETag"], metadata=meta)

    # -- port ------------------------------------------------------------
    def read_head(self, key: str) -> ObjectRead:
        return self._get(key, operation="read_head")

    def create_head_if_absent(self, key: str, data: bytes) -> WriteResult:
        return self._put(key, data, operation="create_head_if_absent",
                         IfNoneMatch="*")

    def compare_and_swap_head(self, key: str, expected_version: str,
                              data: bytes) -> WriteResult:
        return self._put(key, data, operation="compare_and_swap_head",
                         IfMatch=expected_version)

    def append_transition_if_absent(self, key: str, data: bytes) -> WriteResult:
        try:
            return self._put(key, data, operation="append_transition_if_absent",
                             IfNoneMatch="*")
        except PreconditionFailed:
            existing = self._get(key, operation="append_transition_read_back")
            if existing.data == data:
                return WriteResult(key=key, version=existing.version,
                                   metadata={"idempotent_rewrite": True,
                                             **existing.metadata})
            raise

    def read_transition(self, key: str) -> ObjectRead:
        return self._get(key, operation="read_transition")

    def scan_transitions(self, prefix: str,
                         from_sequence: int = 0) -> Iterator[Tuple[str, bytes]]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []) or []:
                key = item["Key"]
                if key.endswith(".bin"):
                    yield key, self._get(key, operation="scan_transitions").data

    def read_after_write_probe(self, key: str, data: bytes) -> Tuple[bool, dict]:
        written = self._put(key, data, operation="read_after_write_write")
        read_back = self._get(key, operation="read_after_write_read")
        return read_back.data == data, {"etag": written.version,
                                        "content_sha256": read_back.metadata.get("content_sha256"),
                                        "http_status": read_back.metadata.get("http_status"),
                                        "request_id": read_back.metadata.get("request_id")}

    def raw_put_head(self, key: str, data: bytes,
                     expected_version: Optional[str] = None) -> WriteResult:
        conditions = {"IfMatch": expected_version} if expected_version else {}
        return self._put(key, data, operation="raw_put_head_bypass_probe", **conditions)
