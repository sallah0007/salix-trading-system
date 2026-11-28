"""R43: a REUSABLE immutable EventContext fact store over the ObjectStore port (Manager input: reusable governed storage adapter may proceed on a SUPPLIED encoding interface and fail closed where canonical bytes / source admission are missing; E05 `stagea_event_context_index` is a rebuildable read model over it).
Nothing normative is defined here: the canonical byte layout of an Event/Context object (D13) is NOT invented - `encode(fact)->bytes`, `decode(bytes)->fact`, `identity_of(fact)->str` and the index columns are SUPPLIED by the owner; with any of them missing the store REFUSES to construct. Facts are immutable (`put_if_absent`; same identity with different bytes refuses); a correction is a NEW fact that names the identity it corrects (lineage record), never an overwrite. A stored object must round-trip decode->encode to its exact bytes and live under the key derived from its identity, else IntegrityFailure.
No canonical database, no Core write permission, no principal/admission: writes are plain store puts from a supplied caller; who may write is a source-owned grant not modelled here."""
import hashlib
from ..errors import Refusal, IntegrityFailure
FACT, CORR, INTENT = "event-context/fact/", "event-context/corr/", "event-context/intent/"
def _s(x): return isinstance(x, str) and bool(x)
def _k(prefix, ident): return prefix + hashlib.sha256(ident.encode("utf-8")).hexdigest()
class EventContextStore:
    def __init__(self, store, *, encode, decode, identity_of, columns_of, semantic_validator=None):
        if store is None or not all(callable(f) for f in (encode, decode, identity_of, columns_of)): raise Refusal("encoding interface", code="EVENT_CONTEXT_ENCODING_INTERFACE_UNBOUND_HELD")
        self._s, self._e, self._d, self._i, self._c = store, encode, decode, identity_of, columns_of
        if semantic_validator is not None and not callable(semantic_validator): raise Refusal("semantic_validator", code="EVENT_CONTEXT_SEMANTIC_VALIDATOR_NOT_CALLABLE")
        self._sv = semantic_validator        # R52: OPTIONAL governed factual-semantics port (e.g. `context.news_hub_v2.check_event_record`). It governs SEMANTIC USE only; put()/get() keep storing and reading raw evidence unchanged.
    def put(self, fact, *, corrects=None):
        ident = self._i(fact); raw = self._e(fact)
        if not (_s(ident) and isinstance(raw, (bytes, bytearray)) and raw): raise Refusal("fact", code="EVENT_CONTEXT_FACT_INVALID")
        raw = bytes(raw)
        if self._e(self._d(raw)) != raw: raise Refusal(ident, code="EVENT_CONTEXT_ENCODING_NOT_ROUND_TRIP")
        if corrects is not None:
            if not _s(corrects) or corrects == ident or self.get(corrects) is None: raise Refusal(str(corrects), code="EVENT_CONTEXT_CORRECTION_TARGET_UNKNOWN")
        k = _k(FACT, ident); ik, ck = _k(INTENT, ident), _k(CORR, ident)
        if corrects is None:
            if self._s.get(ik) is not None and self._s.get(ck) is None: raise Refusal(ident, code="EVENT_CONTEXT_PARTIAL_CORRECTION_PENDING_RETRY_THE_EXACT_CORRECTION")
        else:
            # R46: a correction's fact and lineage become VISIBLE together. Order: intent (hides the fact) -> fact -> lineage (reveals it). A failure or unknown outcome in any phase
            # leaves the fact hidden (get() None, absent from the E05 source); the EXACT retry completes it idempotently; a different lineage is an integrity failure.
            body = ("%s>%s" % (ident, corrects)).encode("utf-8")
            if not self._s.put_if_absent(ik, body):
                got = self._s.get(ik)
                if got is None or got[0] != body: raise IntegrityFailure("correction lineage differs")
        if not self._s.put_if_absent(k, raw):
            got = self._s.get(k)
            if got is None or got[0] != raw: raise IntegrityFailure("event context identity already bound to different bytes")        # a correction is a NEW identity
        if corrects is not None:
            if not self._s.put_if_absent(ck, body):
                got = self._s.get(ck)
                if got is None or got[0] != body: raise IntegrityFailure("correction lineage differs")
        return ident
    def get_for_semantic_use(self, ident):
        """R52 (Manager 21:03, Registry p293): the raw store PRESERVES any supplied evidence, but a fact may be used as FACTUAL Event/Context truth only if an explicit governed semantic-validation port is bound AND accepts it. Unbound port => semantic use is HELD (refusal, nothing returned); a port refusal propagates; a missing fact returns None. No label list or grammar is defined here: whatever the bound port enforces is the only semantic rule (the pure four-token check in `news_hub_v2.check_event_record` is a PARTIAL candidate, not a complete factual-semantics validator)."""
        if self._sv is None: raise Refusal(str(ident), code="EVENT_CONTEXT_SEMANTIC_USE_HELD_NO_VALIDATION_PORT")
        f = self.get(ident)
        if f is None: return None
        raw = self._e(f); import copy; probe = copy.deepcopy(f)          # PORT CONTRACT: the port sees a DETACHED copy; success is exactly `None`; failure is a raised Refusal (propagates); every other return (False, 0, '', a dict, True...) is an unsupported verdict and is REFUSED, never read as approval.
        r = self._sv(probe)
        if r is not None: raise Refusal(repr(r)[:60], code="EVENT_CONTEXT_SEMANTIC_VALIDATOR_RETURN_UNSUPPORTED")
        if self._i(probe) != ident or self._e(probe) != raw: raise Refusal(str(ident), code="EVENT_CONTEXT_SEMANTIC_VALIDATOR_ALTERED_THE_FACT")          # the validated thing must be the ORIGINAL exact stored fact
        return self._d(raw)          # a fresh decode of the stored bytes: never the object the port touched
    def _hidden(self, fact_key):
        """a correction whose intent exists but whose lineage is not (yet) confirmed. LEGACY facts (no intent record) are visible; a legacy fact-without-lineage partial write cannot be told apart and stays readable (explicit held compatibility)."""
        h = fact_key[len(FACT):]
        return self._s.get(INTENT + h) is not None and self._s.get(CORR + h) is None
    def pending(self):
        """intent bodies ('new>corrects') whose correction is not confirmed: visible to operators, never to readers."""
        return sorted(self._s.get(k)[0].decode("utf-8") for k in self._s.list_prefix(INTENT) if self._s.get(CORR + k[len(INTENT):]) is None and self._s.get(k) is not None)
    def get(self, ident):
        if _s(ident) and self._hidden(_k(FACT, ident)): return None
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
        me = self
        class _Visible:        # R46: the E05 source sees only facts whose correction (if any) is confirmed
            def list_prefix(self, prefix): return [k for k in me._s.list_prefix(prefix) if not me._hidden(k)]
            def get(self, k): return me._s.get(k)
        return S.object_prefix_source(_Visible(), "stagea_event_context_index", FACT, row_of, vintage_mode=vintage_mode)
