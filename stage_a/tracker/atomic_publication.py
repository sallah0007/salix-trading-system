"""R41: CANDIDATE consumer-boundary atomic publish/read for a record that must be "fully present or entirely absent" (NL0186; MLCore native p323/p324 say immutable prospective record + deterministic idempotency key; NO current clause states reader partial-observation exclusion, and the shadow-row field set / reader contract is UNBOUND).
Mechanism (generic, over the ObjectStore port): the body is written once at a content address; a record becomes VISIBLE only when a single `put_if_absent` of the pointer under its idempotency key succeeds AFTER the body. Readers go ONLY through the pointer and re-verify body hash + mandatory field set, so a crash between the two writes leaves an unreachable orphan (absent), never a partial record. Same key + different payload = IntegrityFailure; identical retry = one record.
The mandatory field set is SUPPLIED by the owner (`required_fields`); none is invented. Whole-frame IPC is NOT claimed as shadow-record proof."""
import json
from ..errors import Refusal, IntegrityFailure
from ..storage.byte_primitives import canonical_bytes, domain_hash
DOMAIN = "SALIX_R41_CANDIDATE_ATOMIC_RECORD_V1"
class AtomicRecordStore:
    def __init__(self, store, *, required_fields, prefix="atomic"):
        if not (isinstance(required_fields, frozenset) and required_fields and all(isinstance(f, str) and f for f in required_fields) and isinstance(prefix, str) and prefix): raise Refusal("required_fields", code="ATOMIC_CONFIG_INVALID")
        self._s, self._req, self._p = store, required_fields, prefix
    def _body_key(self, h): return "%s/body/%s" % (self._p, h)
    def _ptr_key(self, idem): return "%s/ptr/%s" % (self._p, domain_hash(DOMAIN + "/KEY", idem.encode()))
    def _check(self, rec, idem):
        if not (isinstance(idem, str) and idem and isinstance(rec, dict) and self._req <= set(rec) and all(rec[f] not in (None, "") for f in self._req)): raise Refusal("record", code="ATOMIC_RECORD_INCOMPLETE_OR_KEY_INVALID")
    def publish(self, idem, rec, *, _after_body=None):
        """-> content hash. `_after_body` is a TEST fault hook run between the body write and the pointer write."""
        self._check(rec, idem); data = canonical_bytes(rec); h = domain_hash(DOMAIN, data)
        self._s.put_if_absent(self._body_key(h), data)
        g = self._s.get(self._body_key(h))
        if g is None or g[0] != data: raise IntegrityFailure("body at %s differs" % h)
        if _after_body is not None: _after_body()
        if not self._s.put_if_absent(self._ptr_key(idem), h.encode()):
            cur = self._s.get(self._ptr_key(idem))
            if cur is None or cur[0].decode() != h: raise IntegrityFailure("idempotency key already bound to a different payload")
        return h
    def read(self, idem):
        """-> the record dict, or None when absent (never a partial)."""
        if not (isinstance(idem, str) and idem): raise Refusal("key", code="ATOMIC_RECORD_INCOMPLETE_OR_KEY_INVALID")
        p = self._s.get(self._ptr_key(idem))
        if p is None: return None
        h = p[0].decode(); b = self._s.get(self._body_key(h))
        if b is None: raise IntegrityFailure("pointer names a missing body")
        if domain_hash(DOMAIN, b[0]) != h: raise IntegrityFailure("body does not hash to its pointer")
        rec = json.loads(b[0])
        if not self._req <= set(rec) or any(rec[f] in (None, "") for f in self._req): raise IntegrityFailure("stored record lacks mandatory fields")
        return rec
