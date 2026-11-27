"""ObjectStore port: strong read-after-write, conditional create, conditional replace.
InMemoryObjectStore is a unit aid with fault injection. It does NOT qualify any real provider (R5 OPEN)."""
import threading
from typing import Optional, Protocol, Tuple, List
from ..errors import UnknownCommit

class ObjectStore(Protocol):
    def get(self, key: str) -> Optional[Tuple[bytes, int]]: ...
    def put_if_absent(self, key: str, data: bytes) -> bool: ...
    def put_if_match(self, key: str, data: bytes, etag: int) -> bool: ...
    def list_prefix(self, prefix: str) -> List[str]: ...

class InMemoryObjectStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._d = {}
        self._etag = 0
        self.lose_ack_on_next_write = False   # commit lands, caller sees UnknownCommit
        self.drop_next_write = False          # write does not land, caller sees UnknownCommit

    def get(self, key):
        with self._lock:
            v = self._d.get(key)
            return None if v is None else (v[0], v[1])

    def _maybe_fault(self):
        if self.drop_next_write:
            self.drop_next_write = False
            raise UnknownCommit("dropped write")

    def _ack(self):
        if self.lose_ack_on_next_write:
            self.lose_ack_on_next_write = False
            raise UnknownCommit("ack lost")

    def put_if_absent(self, key, data):
        with self._lock:
            self._maybe_fault()
            if key in self._d:
                return False
            self._etag += 1
            self._d[key] = (bytes(data), self._etag)
            self._ack()
            return True

    def put_if_match(self, key, data, etag):
        with self._lock:
            self._maybe_fault()
            cur = self._d.get(key)
            if cur is None or cur[1] != etag:
                return False
            self._etag += 1
            self._d[key] = (bytes(data), self._etag)
            self._ack()
            return True

    def list_prefix(self, prefix):
        with self._lock:
            return sorted(k for k in self._d if k.startswith(prefix))
