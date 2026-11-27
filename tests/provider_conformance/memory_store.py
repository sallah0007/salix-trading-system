"""In-memory fake store — UNIT-TEST AID ONLY.

E07-M1 (frozen): "The in-memory fake object store is a unit-test aid only and
can never prove E-01 provider semantics." CAN_PROVE_PROVIDER_SEMANTICS is
therefore False, the suite refuses to emit a provider verdict from it, and the
runner labels such a run NOT_PROVIDER_EVIDENCE.

It models a provider that behaves correctly, so it exercises WRITER logic. It
cannot show how a real provider behaves under concurrency, delay or partition.
"""
from __future__ import annotations

import itertools
import uuid
from typing import Dict, Iterator, Optional, Tuple

from .canonical import sha256_hex
from .model import sequence_from_transition_key
from .store_port import (AccessDenied, NotFound, ObjectRead, ObjectStorePort,
                         PreconditionFailed, UnknownWriteOutcome, WriteResult)


class MemoryObjectStore(ObjectStorePort):
    CAN_PROVE_PROVIDER_SEMANTICS = False
    PROVIDER_ID = "memory-fake"

    def __init__(self, *, denied_write_prefixes: Tuple[str, ...] = (),
                 head_write_denied: bool = False):
        self._objects: Dict[str, bytes] = {}
        self._versions: Dict[str, str] = {}
        self._counter = itertools.count(1)
        # Simulated permission boundary. A SIMULATION is not evidence: the
        # suite reports bypass prevention as UNPROVEN on a fake provider.
        self._denied_write_prefixes = tuple(denied_write_prefixes)
        self._head_write_denied = head_write_denied
        # Fault injection for unknown-commit testing.
        self.fail_next_cas_as_unknown = False
        self.unknown_write_applies = True

    # -- helpers ---------------------------------------------------------
    def _new_version(self) -> str:
        return f'"{next(self._counter):08d}-{uuid.uuid4().hex[:8]}"'

    def _check_denied(self, key: str, *, is_head_write: bool) -> None:
        if is_head_write and self._head_write_denied:
            raise AccessDenied("SIMULATED_ACCESS_DENIED:" + key)
        for prefix in self._denied_write_prefixes:
            if key.startswith(prefix):
                raise AccessDenied("SIMULATED_ACCESS_DENIED:" + key)

    def _put(self, key: str, data: bytes) -> WriteResult:
        self._objects[key] = data
        version = self._new_version()
        self._versions[key] = version
        return WriteResult(key=key, version=version,
                           metadata={"content_sha256": sha256_hex(data),
                                     "content_length": len(data)})

    # -- port ------------------------------------------------------------
    def read_head(self, key: str) -> ObjectRead:
        if key not in self._objects:
            raise NotFound(key)
        data = self._objects[key]
        return ObjectRead(key=key, data=data, version=self._versions[key],
                          metadata={"content_sha256": sha256_hex(data),
                                    "content_length": len(data)})

    def create_head_if_absent(self, key: str, data: bytes) -> WriteResult:
        self._check_denied(key, is_head_write=True)
        if key in self._objects:
            raise PreconditionFailed("HEAD_ALREADY_EXISTS:" + key)
        return self._put(key, data)

    def compare_and_swap_head(self, key: str, expected_version: str,
                              data: bytes) -> WriteResult:
        self._check_denied(key, is_head_write=True)
        if key not in self._objects:
            raise PreconditionFailed("HEAD_ABSENT:" + key)
        if self._versions[key] != expected_version:
            raise PreconditionFailed("ETAG_MISMATCH:" + key)
        if self.fail_next_cas_as_unknown:
            self.fail_next_cas_as_unknown = False
            if self.unknown_write_applies:
                self._put(key, data)      # the write DID land; the answer was lost
            raise UnknownWriteOutcome("SIMULATED_UNKNOWN_OUTCOME:" + key)
        return self._put(key, data)

    def append_transition_if_absent(self, key: str, data: bytes) -> WriteResult:
        self._check_denied(key, is_head_write=False)
        if key in self._objects:
            if self._objects[key] != data:
                raise PreconditionFailed("IMMUTABLE_KEY_CONFLICT:" + key)
            # Byte-identical re-write of an immutable key is idempotent.
            return WriteResult(key=key, version=self._versions[key],
                               metadata={"idempotent_rewrite": True})
        return self._put(key, data)

    def read_transition(self, key: str) -> ObjectRead:
        if key not in self._objects:
            raise NotFound(key)
        data = self._objects[key]
        return ObjectRead(key=key, data=data, version=self._versions[key],
                          metadata={"content_sha256": sha256_hex(data)})

    def scan_transitions(self, prefix: str,
                         from_sequence: int = 0) -> Iterator[Tuple[str, bytes]]:
        # Deliberately yielded in REVERSE key order: listing order is never
        # authority, and a rebuilder that depends on it must fail its test.
        for key in sorted(self._objects, reverse=True):
            if not (key.startswith(prefix) and key.endswith(".bin")):
                continue
            sequence = sequence_from_transition_key(key)
            if sequence is not None and sequence < from_sequence:
                continue
            yield key, self._objects[key]

    def read_after_write_probe(self, key: str, data: bytes) -> Tuple[bool, dict]:
        self._check_denied(key, is_head_write=False)
        written = self._put(key, data)
        read_back = self.read_transition(key)
        return read_back.data == data, {"write_version": written.version,
                                        "read_version": read_back.version}

    def raw_put_head(self, key: str, data: bytes,
                     expected_version: Optional[str] = None) -> WriteResult:
        self._check_denied(key, is_head_write=True)
        if expected_version is not None:
            if self._versions.get(key) != expected_version:
                raise PreconditionFailed("ETAG_MISMATCH:" + key)
        return self._put(key, data)
