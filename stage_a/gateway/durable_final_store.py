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

class DurableFinalResolutionStore(V.FinalResolutionStore):
    def __init__(self, store):
        super().__init__(); self._o = store
    def set_pin(self, identity, pin):
        super().set_pin(identity, pin); pb = _dump({"identity": encode(identity), "pin": pin}); k = _pin_key(identity)
        if not self._o.put_if_absent(k, pb):
            got = self._o.get(k)
            if got is None or got[0] != pb: raise IntegrityFailure("pin differs from the stored one")
    def resolve(self, request_id, identity, evaluate):
        out = super().resolve(request_id, identity, evaluate)
        rec = _dump({"identity": encode(identity), "outcome": encode(out)}); k = _ident_key(identity)
        if not self._o.put_if_absent(k, rec):
            got = self._o.get(k)
            if got is None or got[0] != rec: raise IntegrityFailure("final resolution record differs from the stored one")
        rb = _dump({"consumer_id": identity.consumer_id, "request_id": request_id, "identity_key": k}); rk = _req_key(identity.consumer_id, request_id)
        if not self._o.put_if_absent(rk, rb):
            got = self._o.get(rk)
            if got is None or got[0] != rb: raise IntegrityFailure("request binding differs from the stored one")
        return out
    def recover(self):
        """Rebuild the in-memory maps from the object store (restart). Does not evaluate anything."""
        with self._lock:
            ids = {}
            for k in self._o.list_prefix("final-resolution/id/"):
                got = self._o.get(k); d = json.loads(got[0]); ident = decode(d["identity"])
                if _ident_key(ident) != k: raise IntegrityFailure("identity record key does not match its content")
                self._by_identity[ident] = decode(d["outcome"]); ids[k] = ident
            for k in self._o.list_prefix("final-resolution/pin/"):
                d = json.loads(self._o.get(k)[0]); ident = decode(d["identity"])
                if _pin_key(ident) != k: raise IntegrityFailure("pin record key does not match its content")
                self._pins[ident] = d["pin"]
            for k in self._o.list_prefix("final-resolution/req/"):
                d = json.loads(self._o.get(k)[0]); ident = ids.get(d["identity_key"])
                if ident is None or _req_key(d["consumer_id"], d["request_id"]) != k or ident.consumer_id != d["consumer_id"]: raise IntegrityFailure("request binding without a matching identity record")
                self._req_ids[(d["consumer_id"], d["request_id"])] = ident
        return len(self._by_identity)
