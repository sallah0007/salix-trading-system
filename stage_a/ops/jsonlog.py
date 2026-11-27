"""E-08: structured JSON events with a stable field set to a stdout/file transport. Logs/metrics are NEVER Health authority and never establish currentness: the sink has no Health/status API and every line carries `authoritative: false`.
Missing telemetry cannot create HEALTHY/current authority because nothing here is read by any resolver."""
import json, sys, threading
from ..errors import Refusal
STABLE = ("event_name", "service_role", "subject_id", "operation_id", "job_id", "canonical_ref", "canonical_hash", "epoch", "sequence", "result", "reason_code", "duration_ns", "queue_age_ns", "resource_counters", "trace_id", "correlation_id")
class JsonEventSink:
    def __init__(self, stream=None, path=None):
        if stream is not None and path is not None: raise Refusal("transport", code="LOG_TRANSPORT_AMBIGUOUS")
        self._lock = threading.Lock(); self._path = path; self._stream = stream if (stream is not None or path is not None) else sys.stdout; self.events = []
    def emit(self, kind: str, **fields):
        if not isinstance(kind, str) or not kind: raise Refusal("kind", code="LOG_EVENT_NAME_INVALID")
        stable = {k: fields.pop(k) for k in list(fields) if k in STABLE}; rec = {"event_name": kind, **{k: stable[k] for k in STABLE if k in stable and k != "event_name"}}
        if fields: rec["extra"] = {k: fields[k] for k in sorted(fields)}
        rec["authoritative"] = False
        try: line = json.dumps(rec, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError): raise Refusal(kind, code="LOG_EVENT_NOT_JSON")
        with self._lock:
            self.events.append(rec)
            if self._path is not None:
                with open(self._path, "a", encoding="utf-8") as f: f.write(line + "\n")
            else: self._stream.write(line + "\n")
        return line
    def of_kind(self, kind):
        with self._lock: return [e for e in self.events if e["event_name"] == kind]
