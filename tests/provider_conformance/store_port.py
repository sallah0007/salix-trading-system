"""The frozen E-01 adapter contract, as a port the harness can drive.

Build Plan §29A E-01 required adapter methods:
    read_head()
    compare_and_swap_head(expected_version, new_head)
    append_transition_if_absent(key, bytes)
    read_transition(key)
    scan_transitions(namespace, epoch, from_sequence)
    read_after_write_probe()

The port adds ONE method the production adapter must never expose:
`raw_put_head`. It exists so the harness can ATTEMPT the bypass the Manager's
Sydney probe performed — a direct HEAD overwrite by a caller holding the
current ETag. It is a probe, not a capability the design grants.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple


class ObjectStoreError(Exception):
    """Base for provider-surfaced outcomes the harness must distinguish."""


class NotFound(ObjectStoreError):
    pass


class PreconditionFailed(ObjectStoreError):
    """The provider refused because the conditional precondition did not hold."""


class AccessDenied(ObjectStoreError):
    """The provider refused on PERMISSION, not on precondition.

    This is the only outcome that can prove an enforceable bypass boundary: a
    refusal produced by client-side code proves nothing about the provider.
    """


class UnknownWriteOutcome(ObjectStoreError):
    """The write's result is genuinely unknown (timeout / dropped response).

    E01-M1: this MUST be resolved by rereading the authoritative HEAD, never by
    blind retry.
    """


@dataclass(frozen=True)
class ObjectRead:
    key: str
    data: bytes
    version: str            # provider ETag / generation / version id
    metadata: dict


@dataclass(frozen=True)
class WriteResult:
    key: str
    version: str
    metadata: dict


class ObjectStorePort(abc.ABC):
    """Storage port. Implementations are providers under test, or fakes.

    CAN_PROVE_PROVIDER_SEMANTICS is False for any in-process fake. E07-M1: the
    in-memory fake is a unit-test aid only and can never prove E-01.
    """

    CAN_PROVE_PROVIDER_SEMANTICS: bool = False
    PROVIDER_ID: str = "undefined"

    @abc.abstractmethod
    def read_head(self, key: str) -> ObjectRead: ...

    @abc.abstractmethod
    def create_head_if_absent(self, key: str, data: bytes) -> WriteResult:
        """Create-only write (If-None-Match: *). PreconditionFailed if present."""

    @abc.abstractmethod
    def compare_and_swap_head(self, key: str, expected_version: str,
                              data: bytes) -> WriteResult:
        """Conditional update (If-Match: expected_version)."""

    @abc.abstractmethod
    def append_transition_if_absent(self, key: str, data: bytes) -> WriteResult: ...

    @abc.abstractmethod
    def read_transition(self, key: str) -> ObjectRead: ...

    @abc.abstractmethod
    def scan_transitions(self, prefix: str,
                         from_sequence: int = 0) -> Iterator[Tuple[str, bytes]]:
        """Yield (key, bytes) for every transition object under `prefix`.

        Listing ORDER is never authority (E-09); the caller rebuilds from the
        sequence/hash chain. Implementations must not filter silently.
        """

    @abc.abstractmethod
    def read_after_write_probe(self, key: str, data: bytes) -> Tuple[bool, dict]:
        """Write then immediately read the same key; report byte equality."""

    @abc.abstractmethod
    def raw_put_head(self, key: str, data: bytes,
                     expected_version: Optional[str] = None) -> WriteResult:
        """BYPASS PROBE ONLY. Unconditional or ETag-conditional direct HEAD put,
        with NO semantic validation. Used to attempt the bypass, never to
        perform governed work."""
