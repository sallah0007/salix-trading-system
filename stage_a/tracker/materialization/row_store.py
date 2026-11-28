"""R53 stored PendingRow + committed-predecessor receipt (CANDIDATE storage keys; NOT governed schema, no byte layout invented).
Authority of a stored row = the Annex row hash recomputed from the stored bytes by BOTH the producer encoder and the independent verifier encoder; the JSON field
document is a non-authoritative sidecar used only to rebuild the object and is accepted only if the rebuilt object re-encodes to exactly the stored bytes.
A 'committed predecessor' is therefore a row LOADED from this store by hash (bytes + both hashes re-verified), never a caller-supplied object.
One successor per predecessor (and one origin per profile identity) is claimed by a content-addressed claim key: the same row is idempotent, a different row is a FORK refusal.
Held: who may write (principal), commit-point id rule, clock, accepted-transition linkage (this store is the PENDING candidate scope only)."""
import hashlib, json
from dataclasses import dataclass
from ...errors import Refusal, IntegrityFailure
from ...schema import objects as O, independent as X
from ...schema.encoding import Ref
from ...storage.byte_primitives import canonical_bytes, domain_hash

CLAIM_DOMAIN = "SALIX_PENDING_ROW_CLAIM_V1"
def row_key(h): return "pending-row/%s" % _hex(h)
def fields_key(h): return "pending-row-fields/%s" % _hex(h)
def claim_key(c): return "pending-row-claim/%s" % _hex(c)
def _hex(h):
    if not (isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)): raise Refusal(repr(h), code="BAD_ROW_HASH")
    return h

@dataclass(frozen=True)
class RowReceipt:
    row_hash: str; key: str; byte_length: int; independent_hash_equal: bool

def _xref(t, r): return (t.ref_types[r.ref_type], r.target_id, r.target_version, r.target_hash)
def independent_dict(t, r):
    d = dict(r.__dict__)
    d["input_refs_and_hashes"] = tuple((_xref(t, a), h) for a, h in r.input_refs_and_hashes)
    for k in ("fit_generation_ref", "step_class_ref", "state_origin_ref"): d[k] = None if getattr(r, k) is None else _xref(t, getattr(r, k))
    d["speculation_mode"] = t.enums["SPECULATION_MODE"][r.speculation_mode]
    return d

def _ref_j(r): return None if r is None else [r.ref_type, r.target_id.hex(), r.target_version.hex(), None if r.target_hash is None else r.target_hash.hex()]
def _ref_o(j): return None if j is None else Ref(j[0], bytes.fromhex(j[1]), bytes.fromhex(j[2]), None if j[3] is None else bytes.fromhex(j[3]))
_B = ("feature_id", "quant_manifest_hash", "instrument_id", "timeframe_id", "state_tuple", "published_projection_bits", "predecessor_row_hash", "gate_dependency_hash", "materializer_implementation_id")
_S = ("feature_version", "materialization_version", "state_schema_version", "logical_encoding_version", "arithmetic_contract_version", "published_projection_name", "speculation_mode")
def _to_json(r):
    d = {k: (None if getattr(r, k) is None else getattr(r, k).hex()) for k in _B}; d.update({k: getattr(r, k) for k in _S}); d["step_index"] = r.step_index; d["event_time"] = r.event_time
    d["input_refs_and_hashes"] = [[_ref_j(a), h.hex()] for a, h in r.input_refs_and_hashes]
    for k in ("fit_generation_ref", "step_class_ref", "state_origin_ref"): d[k] = _ref_j(getattr(r, k))
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
def _from_json(b):
    d = json.loads(b.decode("utf-8"))
    kw = {k: (None if d[k] is None else bytes.fromhex(d[k])) for k in _B}; kw.update({k: d[k] for k in _S}); kw["step_index"] = d["step_index"]; kw["event_time"] = d["event_time"]
    kw["input_refs_and_hashes"] = tuple((_ref_o(a), bytes.fromhex(h)) for a, h in d["input_refs_and_hashes"])
    for k in ("fit_generation_ref", "step_class_ref", "state_origin_ref"): kw[k] = _ref_o(d[k])
    return O.PendingRow(**kw)

def _claim_of(row, pred_hash_hex):
    if pred_hash_hex is not None: return domain_hash(CLAIM_DOMAIN, canonical_bytes({"succ_of": pred_hash_hex}))
    ident = {"feature_id": row.feature_id.hex(), "feature_version": row.feature_version, "instrument_id": row.instrument_id.hex(), "timeframe_id": row.timeframe_id.hex(),
             "materialization_version": row.materialization_version, "state_schema_version": row.state_schema_version, "quant_manifest_hash": row.quant_manifest_hash.hex()}
    return domain_hash(CLAIM_DOMAIN, canonical_bytes({"origin_of": ident}))

class PendingRowStore:
    def __init__(self, store, tables):
        self._s, self._t = store, tables

    def _verified_bytes(self, row):
        b = O.row_content_bytes(self._t, row); h = hashlib.sha256(b).hexdigest()
        ih = X.row_hash(independent_dict(self._t, row), self._t.enums)
        if ih.hex() != h: raise IntegrityFailure("independent row hash disagrees with producer hash for %s" % h)
        return b, h

    def commit(self, row) -> RowReceipt:
        b, h = self._verified_bytes(row)
        pred = None if row.predecessor_row_hash is None else row.predecessor_row_hash.hex()
        if pred is not None:
            self.load(pred)                                                     # the predecessor must itself be a committed, re-verified row
        claim = claim_key(_claim_of(row, pred))
        if not self._s.put_if_absent(claim, h.encode("ascii")):
            got = self._s.get(claim)
            if got is None or got[0] != h.encode("ascii"): raise Refusal(h, code="PENDING_ROW_FORK")
        if not self._s.put_if_absent(row_key(h), b):
            got = self._s.get(row_key(h))
            if got is None or got[0] != b: raise IntegrityFailure("row key %s holds different bytes" % h)
        fj = _to_json(row)
        if not self._s.put_if_absent(fields_key(h), fj):                         # never overwrite: an existing sidecar is judged by the exact readback below
            got = self._s.get(fields_key(h))
            if got is None: raise IntegrityFailure("field document for %s vanished" % h)
        back = self.load(h)                                                      # exact persisted readback BEFORE any success claim (unreadable/conflicting sidecar => no receipt)
        if back != row: raise IntegrityFailure("persisted row for %s differs from the committed row" % h)
        return RowReceipt(h, row_key(h), len(b), True)

    def load(self, h):
        h = _hex(h); got = self._s.get(row_key(h)); fl = self._s.get(fields_key(h))
        if got is None or fl is None: raise Refusal(h, code="PREDECESSOR_NOT_COMMITTED")
        if hashlib.sha256(got[0]).hexdigest() != h: raise IntegrityFailure("stored row bytes do not hash to their key %s" % h)
        try: row = _from_json(fl[0])
        except Exception as e: raise IntegrityFailure("row field document unreadable for %s" % h) from e
        b, h2 = self._verified_bytes(row)
        if h2 != h or b != got[0]: raise IntegrityFailure("row field document does not re-encode to the stored bytes for %s" % h)
        return row

    def receipt_for(self, h):
        row = self.load(h); b, h2 = self._verified_bytes(row); return RowReceipt(h2, row_key(h2), len(b), True)

class CommittedRowChain:
    """Owning integration: steps a StateRowBuilder ONLY from a predecessor LOADED from the store, then commits the result. No caller-supplied predecessor object path."""
    def __init__(self, builder, rows: PendingRowStore):
        self._b, self._rows = builder, rows
    def step(self, step_fn, predecessor_hash, inputs, **row_kw):
        pred = None if predecessor_hash is None else self._rows.load(predecessor_hash)
        row = self._b.step(step_fn, pred, inputs, **row_kw)
        return row, self._rows.commit(row)
