"""DEFAULT CROSS-INSTRUMENT ACCESS = DENY (frozen Tracker DOCX s7A, s21A; Build Plan TR-15).
A dependency whose instrument differs from the consumer's TARGET instrument is delivered only if an EXPLICIT grant (consumer, target instrument, source instrument) is current. Cross-instrument permission is independent of source-feature trust.
Grants are SUPPLIED with a non-empty `source_ref` (who may grant is not named by any source read: the grant principal is UNBOUND and nothing here appoints one). A revoked grant denies NEW resolutions immediately; a stored final outcome is immutable and is not rewritten.
Delivered cross-instrument rows stay instrument-qualified (the entry keeps its own instrument). Inheritance of upstream trust/revocation/quarantine by the derived feature is NOT modelled here (needs the lineage owner's rule)."""
from ..errors import Refusal
def _s(x): return x is not None and (isinstance(x, (str, bytes)) and bool(x))
class CrossInstrumentPolicy:
    def __init__(self): self._g = {}; self.revoked = set()
    def grant(self, consumer_id, target, source, source_ref):
        if not (_s(consumer_id) and _s(target) and _s(source) and _s(source_ref)) or target == source: raise Refusal("grant", code="CROSS_INSTRUMENT_GRANT_MALFORMED")
        k = (consumer_id, target, source)
        if k in self._g and self._g[k] != source_ref: raise Refusal(str(k), code="CROSS_INSTRUMENT_GRANT_EXISTS_DIFFERENT_SOURCE")
        self._g[k] = source_ref; self.revoked.discard(k)
    def revoke(self, consumer_id, target, source):
        k = (consumer_id, target, source)
        if k not in self._g: raise Refusal(str(k), code="CROSS_INSTRUMENT_GRANT_UNKNOWN")
        self.revoked.add(k)
    def allows(self, consumer_id, target, source) -> bool:
        if target == source: return True
        k = (consumer_id, target, source); return k in self._g and k not in self.revoked
