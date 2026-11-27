"""DURABLE FinalResolutionStore over the existing ObjectStore port (generic recovery logic; real provider qualification stays HELD - InMemoryObjectStore/SimulationStore only here).
`DurableFinalResolutionStore(store)` write-through persists, per final resolution identity, ONE immutable record (identity + the stored outcome) with `put_if_absent`, and one request-binding record per (consumer_id, request_id); `recover()` rebuilds the in-memory
maps from `list_prefix`, so a restarted process returns the SAME stored outcome for a new request id on the same identity and never re-evaluates. An identity record that already exists with DIFFERENT bytes is an IntegrityFailure (no overwrite).
ENCODING STATUS: key names and the tagged-JSON outcome codec below are CANDIDATE, UNADMITTED internal encodings (FINAL_RESOLUTION_HASH / PACKAGE_HASH canonical bytes are open item D13). The codec only (de)serialises the closed set of Gateway outcome dataclasses
it names; an unknown tag, a field-set mismatch or a type outside the set refuses (fail closed). Single process only (D10): this does not provide cross-process atomicity.
Crash windows: outcome record is written BEFORE the request binding; a crash between them leaves an identity with no binding, which recover() accepts (a later request id simply binds); a binding whose identity record is absent is an IntegrityFailure on recover."""
import dataclasses, hashlib, json
from ..errors import Refusal, IntegrityFailure
from ..schema.encoding import Ref
from ..schema import objects as O
from . import contracts as C
from . import v038 as V

_CLASSES = {c.__name__: c for c in (C.Binding, C.NonDeliveryResolution, C.AbsenceApplied, O.DeliveredFeatureEntry, Ref, V.FinalResolutionIdentity, V.NonDeliveryResolutionV038, V.StructuredOmission, V.VisibilityWatermark, V.ExpectedDependencyKey)}

def encode(x):
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)): return x
    if isinstance(x, bytes): return {"$b": x.hex()}
    if isinstance(x, tuple): return {"$tu": [encode(i) for i in x]}
    if isinstance(x, list): return [encode(i) for i in x]
    if dataclasses.is_dataclass(x) and type(x).__name__ in _CLASSES and _CLASSES[type(x).__name__] is type(x):
        return {"$t": type(x).__name__, "f": {f.name: encode(getattr(x, f.name)) for f in dataclasses.fields(x)}}
    raise Refusal(type(x).__name__, code="FINAL_OUTCOME_CODEC_TYPE_NOT_ALLOWED")
def decode(j):
    if j is None or isinstance(j, (bool, int, str)): return j
    if isinstance(j, list): return [decode(i) for i in j]
    if isinstance(j, dict):
        if set(j) == {"$b"} and isinstance(j["$b"], str): return bytes.fromhex(j["$b"])
        if set(j) == {"$tu"} and isinstance(j["$tu"], list): return tuple(decode(i) for i in j["$tu"])
        if set(j) == {"$t", "f"} and j["$t"] in _CLASSES and isinstance(j["f"], dict):
            cls = _CLASSES[j["$t"]]
            if set(j["f"]) != {f.name for f in dataclasses.fields(cls)}: raise Refusal(j["$t"], code="FINAL_OUTCOME_CODEC_FIELDS_MISMATCH")
            return cls(**{k: decode(v) for k, v in j["f"].items()})
    raise Refusal("tag", code="FINAL_OUTCOME_CODEC_UNKNOWN_TAG")
def _dump(o): return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()
def _ident_key(identity): return "final-resolution/id/" + hashlib.sha256(_dump(encode(identity))).hexdigest()
def _pin_key(identity): return "final-resolution/pin/" + hashlib.sha256(_dump(encode(identity))).hexdigest()
def _req_key(consumer_id, request_id): return "final-resolution/req/" + hashlib.sha256(_dump([consumer_id, request_id])).hexdigest()

class FinalResolutionWriteNotCommitted(Exception):
    """Internal: the durable write failed and a read-back PROVED the record is absent. The caller's original exception is chained."""
class DurableFinalResolutionStore(V.FinalResolutionStore):
    """Phase-aware write-through. Phases: (1) pin, (2) final-resolution identity record = THE COMMIT POINT of a final outcome, (3) request binding.
    A failure BEFORE the commit point (read-back proves the record absent) rolls the provisional memory state back; the original error is re-raised and nothing was published.
    A write that RAISED but whose read-back finds the exact record is treated as committed. If the read-back itself fails the identity is HELD (`FINAL_RESOLUTION_RECOVERY_REQUIRED`): no second evaluation, no outcome, until `recover()` rebuilds from the store.
    A failure AFTER the commit point (request binding) keeps the committed identity and outcome in memory (a retry returns it, never re-evaluates) and removes only the request binding it created."""
    def __init__(self, store):
        super().__init__(); self._o = store; self._held = set()
    def _put(self, key, rec, equal=None):
        try:
            if self._o.put_if_absent(key, rec): return
            got = self._o.get(key)
        except Exception as e:
            try: got = self._o.get(key)
            except Exception: raise Refusal(key, code="FINAL_RESOLUTION_RECOVERY_REQUIRED") from e                # unknown commit and no read-back: hold
            if got is None: raise FinalResolutionWriteNotCommitted() from e
        if got is None or not (equal(got[0]) if equal else got[0] == rec): raise IntegrityFailure("record differs from the stored one")
    def _check_held(self, identity):
        if identity in self._held: raise Refusal(identity, code="FINAL_RESOLUTION_RECOVERY_REQUIRED")
    def set_pin(self, identity, pin, facts=None):
        with self._lock:
            self._check_held(identity); had = identity in self._pins
            super().set_pin(identity, pin, facts)
            rec = _dump({"identity": encode(identity), "pin": self._pins[identity], "facts": self._facts[identity]}); k = _pin_key(identity)
            def same(b): d = json.loads(b); return d["identity"] == encode(identity) and d["pin"] == pin
            try: self._put(k, rec, same)
            except FinalResolutionWriteNotCommitted as e:
                if not had: self._pins.pop(identity, None); self._facts.pop(identity, None)
                raise (e.__cause__ or e)
            except Refusal:
                if not had: self._pins.pop(identity, None); self._facts.pop(identity, None)
                self._held.add(identity); raise
            except BaseException:
                if not had: self._pins.pop(identity, None); self._facts.pop(identity, None)
                raise
    def resolve(self, request_id, identity, evaluate):
        with self._lock:
            self._check_held(identity)
            had_id = identity in self._by_identity; had_rq = (identity.consumer_id, request_id) in self._req_ids
            out = super().resolve(request_id, identity, evaluate)
            def undo():
                if not had_id: self._by_identity.pop(identity, None)
                if not had_rq: self._req_ids.pop((identity.consumer_id, request_id), None)
            rec = _dump({"identity": encode(identity), "outcome": encode(out)}); k = _ident_key(identity)
            try: self._put(k, rec)
            except FinalResolutionWriteNotCommitted as e: undo(); raise (e.__cause__ or e)
            except Refusal: undo(); self._held.add(identity); raise
            except BaseException: undo(); raise
            rb = _dump({"consumer_id": identity.consumer_id, "request_id": request_id, "identity_key": k}); rk = _req_key(identity.consumer_id, request_id)
            try: self._put(rk, rb)
            except FinalResolutionWriteNotCommitted as e:
                if not had_rq: self._req_ids.pop((identity.consumer_id, request_id), None)               # the identity IS committed: keep it; only the request binding is retried
                raise (e.__cause__ or e)
            except BaseException:
                if not had_rq: self._req_ids.pop((identity.consumer_id, request_id), None)
                raise
            return out
    def recover(self):
        """Rebuild the in-memory maps from the object store (restart). Does not evaluate anything."""
        with self._lock:
            self._held.clear(); ids = {}
            for k in self._o.list_prefix("final-resolution/id/"):
                got = self._o.get(k); d = json.loads(got[0]); ident = decode(d["identity"])
                if _ident_key(ident) != k: raise IntegrityFailure("identity record key does not match its content")
                self._by_identity[ident] = decode(d["outcome"]); ids[k] = ident
            for k in self._o.list_prefix("final-resolution/pin/"):
                d = json.loads(self._o.get(k)[0]); ident = decode(d["identity"])
                if _pin_key(ident) != k: raise IntegrityFailure("pin record key does not match its content")
                self._pins[ident] = d["pin"]; self._facts[ident] = d.get("facts")
            for k in self._o.list_prefix("final-resolution/req/"):
                d = json.loads(self._o.get(k)[0]); ident = ids.get(d["identity_key"])
                if ident is None or _req_key(d["consumer_id"], d["request_id"]) != k or ident.consumer_id != d["consumer_id"]: raise IntegrityFailure("request binding without a matching identity record")
                self._req_ids[(d["consumer_id"], d["request_id"])] = ident
        return len(self._by_identity)
