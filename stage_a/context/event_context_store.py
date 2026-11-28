"""R43: a REUSABLE immutable EventContext fact store over the ObjectStore port (Manager input: reusable governed storage adapter may proceed on a SUPPLIED encoding interface and fail closed where canonical bytes / source admission are missing; E05 `stagea_event_context_index` is a rebuildable read model over it).
Nothing normative is defined here: the canonical byte layout of an Event/Context object (D13) is NOT invented - `encode(fact)->bytes`, `decode(bytes)->fact`, `identity_of(fact)->str` and the index columns are SUPPLIED by the owner; with any of them missing the store REFUSES to construct. Facts are immutable (`put_if_absent`; same identity with different bytes refuses); a correction is a NEW fact that names the identity it corrects (lineage record), never an overwrite. A stored object must round-trip decode->encode to its exact bytes and live under the key derived from its identity, else IntegrityFailure.
No canonical database, no Core write permission, no principal/admission: writes are plain store puts from a supplied caller; who may write is a source-owned grant not modelled here."""
import hashlib
from ..errors import Refusal, IntegrityFailure
FACT, CORR = "event-context/fact/", "event-context/corr/"
def _s(x): return isinstance(x, str) and bool(x)
def _k(prefix, ident): return prefix + hashlib.sha256(ident.encode("utf-8")).hexdigest()
class EventContextStore:
    def __init__(self, store, *, encode, decode, identity_of, columns_of):
        if store is None or not all(callable(f) for f in (encode, decode, identity_of, columns_of)): raise Refusal("encoding interface", code="EVENT_CONTEXT_ENCODING_INTERFACE_UNBOUND_HELD")
        self._s, self._e, self._d, self._i, self._c = store, encode, decode, identity_of, columns_of
    def put(self, fact, *, corrects=None):
        ident = self._i(fact); raw = self._e(fact)
        if not (_s(ident) and isinstance(raw, (bytes, bytearray)) and raw): raise Refusal("fact", code="EVENT_CONTEXT_FACT_INVALID")
        raw = bytes(raw)
        if self._e(self._d(raw)) != raw: raise Refusal(ident, code="EVENT_CONTEXT_ENCODING_NOT_ROUND_TRIP")
        if corrects is not None:
            if not _s(corrects) or corrects == ident or self._s.get(_k(FACT, corrects)) is None: raise Refusal(str(corrects), code="EVENT_CONTEXT_CORRECTION_TARGET_UNKNOWN")
        k = _k(FACT, ident)
        if not self._s.put_if_absent(k, raw):
            got = self._s.get(k)
            if got is None or got[0] != raw: raise IntegrityFailure("event context identity already bound to different bytes")        # a correction is a NEW identity
        if corrects is not None:
            ck = _k(CORR, ident); body = ("%s>%s" % (ident, corrects)).encode("utf-8")
            if not self._s.put_if_absent(ck, body):
                got = self._s.get(ck)
                if got is None or got[0] != body: raise IntegrityFailure("correction lineage differs")
        return ident
    def get(self, ident):
        got = self._s.get(_k(FACT, ident)) if _s(ident) else None
        if got is None: return None
        f = self._d(got[0])
        if self._i(f) != ident or self._e(f) != got[0]: raise IntegrityFailure("stored event context does not match its identity key")
        return f
    def corrections_of(self, ident):
        """identities that declare they correct `ident` (lineage only; no 'current' pick is made here)."""
        out = []
        for k in self._s.list_prefix(CORR):
            g = self._s.get(k)
            if g is None: raise IntegrityFailure("listed correction unreadable")
            new, old = g[0].decode("utf-8").split(">")
            if old == ident: out.append(new)
        return sorted(out)
    def source(self, *, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE"):
        """E05 (head, rows) source for `stagea_event_context_index`: key re-derived from the decoded identity, columns from the supplied mapper (must contain event_context_identity == the fact's identity)."""
        from ..storage import e05_sources as S
        def row_of(key, raw):
            f = self._d(raw); ident = self._i(f)
            if key != _k(FACT, ident) or self._e(f) != raw: raise Refusal(key, code="E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")
            r = dict(self._c(f))
            if r.get("event_context_identity") != ident: raise Refusal(key, code="E05_SOURCE_COLUMNS_DISAGREE_WITH_IDENTITY")
            return r
        return S.object_prefix_source(self._s, "stagea_event_context_index", FACT, row_of, vintage_mode=vintage_mode)
