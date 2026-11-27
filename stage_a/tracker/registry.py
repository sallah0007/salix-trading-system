"""Per-namespace fenced journals (one immutable journal + one mutable HEAD per authority namespace)."""
import threading
from ..coordination.object_store_journal import ObjectStoreJournal

class FeatureJournalSet:
    def __init__(self, store, writer_id: str):
        self._store, self._w = store, writer_id
        self._js, self._lock = {}, threading.Lock()
    def journal(self, namespace: str) -> ObjectStoreJournal:
        with self._lock:
            j = self._js.get(namespace)
            if j is None:
                j = ObjectStoreJournal(self._store, namespace, self._w)
                j.acquire_epoch()
                self._js[namespace] = j
            return j
    def reacquire(self, namespace: str) -> ObjectStoreJournal:
        with self._lock:
            j = ObjectStoreJournal(self._store, namespace, self._w)
            j.acquire_epoch()
            self._js[namespace] = j
            return j
