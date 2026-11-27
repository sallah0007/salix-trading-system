import json, threading
from dataclasses import dataclass
from typing import Iterable, List, Protocol
from .canonical import canonical_json, sha256_hex

GENESIS_HASH = "0" * 64

@dataclass(frozen=True)
class Head:
    seq: int
    hash: str

GENESIS_HEAD = Head(0, GENESIS_HASH)

@dataclass(frozen=True)
class JournalRecord:
    seq: int
    prev_hash: str
    kind: str
    body_json: str
    record_hash: str

    def body(self):
        return json.loads(self.body_json)

class HeadMismatch(Exception):
    def __init__(self, expected: Head, actual: Head):
        super().__init__("journal head moved: expected %s actual %s" % (expected, actual))
        self.expected, self.actual = expected, actual

class JournalIntegrityError(Exception):
    pass

def record_hash(seq: int, prev_hash: str, kind: str, body_json: str) -> str:
    return sha256_hex(canonical_json({"seq": seq, "prev": prev_hash, "kind": kind, "body": body_json}))

def verify_chain(records: Iterable[JournalRecord]) -> Head:
    head = GENESIS_HEAD
    for r in records:
        if r.seq != head.seq + 1 or r.prev_hash != head.hash:
            raise JournalIntegrityError("chain break at seq %s" % r.seq)
        if r.record_hash != record_hash(r.seq, r.prev_hash, r.kind, r.body_json):
            raise JournalIntegrityError("hash mismatch at seq %s" % r.seq)
        head = Head(r.seq, r.record_hash)
    return head

class JournalPort(Protocol):
    def head(self) -> Head: ...
    def append(self, expected_head: Head, kind: str, body: dict) -> JournalRecord: ...
    def read_from(self, seq: int) -> List[JournalRecord]: ...

class InMemoryJournal:
    """Conformance simulator: linearisable compare-and-append. NOT a production adapter."""
    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[JournalRecord] = []

    def head(self) -> Head:
        with self._lock:
            return self._head_locked()

    def _head_locked(self) -> Head:
        if not self._records:
            return GENESIS_HEAD
        r = self._records[-1]
        return Head(r.seq, r.record_hash)

    def append(self, expected_head: Head, kind: str, body: dict) -> JournalRecord:
        body_json = canonical_json(body)
        with self._lock:
            actual = self._head_locked()
            if actual != expected_head:
                raise HeadMismatch(expected_head, actual)
            seq = actual.seq + 1
            rec = JournalRecord(seq, actual.hash, kind, body_json, record_hash(seq, actual.hash, kind, body_json))
            self._records.append(rec)
            return rec

    def read_from(self, seq: int) -> List[JournalRecord]:
        with self._lock:
            return [r for r in self._records if r.seq >= seq]
