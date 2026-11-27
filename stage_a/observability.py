"""Evidence/log sink. Emitting an event never creates authority, Health state or delivery."""
import threading

class EventSink:
    def __init__(self):
        self._lock = threading.Lock()
        self.events = []
    def emit(self, kind: str, **fields):
        with self._lock:
            self.events.append(dict(kind=kind, **fields))
    def of_kind(self, kind):
        with self._lock:
            return [e for e in self.events if e["kind"] == kind]
