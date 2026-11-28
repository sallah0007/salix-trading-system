"""R37: an explicit SAME-CLASS SIMULATION committed-journal candidate path from an ACTUAL accepted receipt to the Gateway's PublishedRow and chain-status inputs.
It replaces the literal `PublishedRow` / bare `ChainStatusAuthority(allow_uncommitted_status=True)` seeding of the older test gateways with committed records:
  accepted record (the per-feature journal, re-read by `accepted_manifest.read_accepted_manifest`: bytes re-hashed) -> `commit` appends ONE SIM_STATUS_FACT record (status fields + nested row + the owning feature journal's HEAD at commit) to a SEPARATE SIMULATION journal (never the feature transition journal, whose replay owns its record kinds)
  -> `rows()` re-reads each row's accepted binding from the feature journal and fails closed on any mismatch, on any advance of the owning feature HEAD since the latest commit (publish, withdraw, anything), and on a non-live (e.g. WITHDRAWN) version
R38 (Build Plan R3 E01-H1 p1021-1026: accepted journal + single HEAD authority; a projection journal is only a derived cache that must be caught up to the EXACT accepted HEAD): the side journal is a DERIVED CACHE, never authority. The projection's `authoritative` is also gated on the same source guard. A lawful rebuild is a fresh `commit` against the CURRENT head while the version is still live; it needs a caller-supplied status token (no WITHDRAWN=>HALTED, PUBLISHABLE=>CURRENT or other mapping is guessed). INTERPRETATION CORRECTION (Owner/root, R38): Build Plan R3 E01-H1 p1021-1026 ELIMINATES cross-head atomicity for status/currentness: a separate NON-AUTHORITATIVE projection/cache may be rebuilt AFTER the owning journal commit provided it proves caught up to that EXACT owning HEAD and fails closed otherwise. This guard is that catch-up proof (candidate), NOT a second authority HEAD and not an atomic dual commit. The owning accepted transition itself must carry its required status/currentness fact; the source-owned mapping/principal for that is HELD and not guessed here.
BOUND from the accepted receipt (never supplied): feature_version, quant_manifest_hash (the accepted manifest hash), accepted_seq/hash. SUPPLIED and UNADMITTED (`SuppliedRowInputs`): the 16-byte feature/instrument/timeframe ids (no source maps the accepted `feature_key` strings to them), materialization version, step/event/as-of/visible times,
projection name/bits/hash, refs and vintage mode - this module invents no projection hash rule or id derivation. The STATUS VALUE is the caller's supplied token mapped through the caller's supplied `status_map` (R7 s2 defines neither the mapping nor a status-origin principal; PUBLISHABLE is never mapped to CURRENT here).
This is SIMULATION only: it clears no acceptance, publication or consumer-authority gate and is not the QUALIFIED path."""
import json
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
from tracker_component.journal_port import GENESIS_HEAD
from ..coordination.object_store_journal import ObjectStoreJournal
from ..gateway.contracts import PublishedRow
from ..replay import replay
from ..schema.encoding import Ref
from ..storage.authority_class import authority_class_of, SIMULATION
from . import accepted_manifest as AM
from .status_decoder import make_decoder
from .status_projection import StatusProjection
STATUS_KIND = "SIM_STATUS_FACT"           # R38: ONE side record carries the status fact AND the row (no two-append pseudo-commit)
LIVE_STATES = ("CANONICAL_ACCEPTED", "PUBLISHABLE")      # states from which a (re)commit is lawful; WITHDRAWN is never rebuilt and no status is guessed from any state
@dataclass(frozen=True)
class SuppliedRowInputs:
    feature_id: bytes; instrument_id: bytes; timeframe_id: bytes; materialization_version: str; step_index: int; event_time: int; logical_encoding_version: str
    published_projection_name: str; published_projection_bits: bytes; published_projection_hash: bytes; fit_generation_ref: Optional[Ref]; data_vintage_mode: str
    available_asof: int; visible_at: int; source_or_causal_policy_ref: Ref; canonical_transition_ref: Ref
def _ref(r): return None if r is None else [r.ref_type, r.target_id.hex(), r.target_version.hex(), None if r.target_hash is None else r.target_hash.hex()]
def _unref(x): return None if x is None else Ref(x[0], bytes.fromhex(x[1]), bytes.fromhex(x[2]), None if x[3] is None else bytes.fromhex(x[3]))
class SimulationPublicationPath:
    def __init__(self, store, feature_journal, status_journal, status_spec):
        """status_spec: the `make_decoder` spec (its `record_kind` must be SIM_STATUS_FACT); status_journal: ObjectStoreJournal on a SIMULATION store, DISTINCT from feature_journal."""
        if type(status_journal) is not ObjectStoreJournal or authority_class_of(status_journal) != SIMULATION: raise Refusal("status journal", code="SIM_PUBLICATION_REQUIRES_SIMULATION_JOURNAL")
        if status_journal is feature_journal or not isinstance(status_spec, dict) or status_spec.get("record_kind") != STATUS_KIND: raise Refusal("spec", code="SIM_PUBLICATION_SPEC_INVALID")
        self._st, self._fj, self._sj, self._spec = store, feature_journal, status_journal, status_spec; self._decode = make_decoder(status_spec)
    def commit(self, feature_key, supplied: SuppliedRowInputs, status_token, *, sequence, correction=False, origin=None, expected_source_head=None, expected_side_head=None):
        """Also the lawful REBUILD after a source-head advance: re-commits against the CURRENT owning head, only while the version is live."""
        if not isinstance(supplied, SuppliedRowInputs) or status_token not in self._spec["status_map"] or type(sequence) is not int or sequence < 1 or type(correction) is not bool: raise Refusal("inputs", code="SIM_PUBLICATION_INPUT_INVALID")
        src = self._fj.head()                                                                    # read BEFORE the state: a race can only make the recorded head older than the state seen, which the guard fails closed on
        if expected_source_head is not None and src != expected_source_head: raise Refusal("owning head advanced", code="SIM_PUBLICATION_SOURCE_HEAD_ADVANCED")      # R51: an emitter that derived this status from the record at a pinned owning HEAD must not have a LATER head stamped onto it
        rb = AM.read_accepted_manifest(self._fj, self._st, feature_key)                         # the ACTUAL accepted receipt, manifest bytes re-hashed
        vs = replay(feature_key.namespace(), self._fj.read_from(1)).get(feature_key.feature_version)
        if vs is None or vs.status not in LIVE_STATES: raise Refusal(getattr(vs, "status", None), code="SIM_PUBLICATION_SOURCE_NOT_LIVE")
        if not (isinstance(supplied.feature_id, bytes) and len(supplied.feature_id) == 16 and isinstance(supplied.instrument_id, bytes) and len(supplied.instrument_id) == 16 and isinstance(supplied.timeframe_id, bytes) and len(supplied.timeframe_id) == 16): raise Refusal("ids", code="SIM_PUBLICATION_INPUT_INVALID")
        row = {"feature_version": feature_key.feature_version, "quant_manifest_hash": rb.manifest_hash}                       # bound from the receipt
        for k in ("feature_id", "instrument_id", "timeframe_id", "published_projection_bits", "published_projection_hash"): row[k] = getattr(supplied, k).hex()
        for k in ("materialization_version", "step_index", "event_time", "logical_encoding_version", "published_projection_name", "data_vintage_mode", "available_asof", "visible_at"): row[k] = getattr(supplied, k)
        for k in ("fit_generation_ref", "source_or_causal_policy_ref", "canonical_transition_ref"): row[k] = _ref(getattr(supplied, k))
        mvn = self._spec["mv"]; bf = self._spec["bytes_fields"]; vals = (supplied.feature_id, feature_key.feature_version, supplied.instrument_id, supplied.timeframe_id, supplied.materialization_version)
        body = {n: (v.hex() if n in bf else v) for n, v in zip(mvn, vals)}
        body.update({self._spec["status_field"]: status_token, self._spec["sequence_field"]: sequence, self._spec["available_asof_field"]: supplied.available_asof, self._spec["correction_field"]: correction,
                     "feature_key": rb.feature_key, "accepted_seq": rb.accepted_seq, "accepted_hash": rb.accepted_hash, "source_head_seq": src.seq, "source_head_hash": src.hash, "row": row})
        if origin is not None:
            if not (isinstance(origin, dict) and all(isinstance(k, str) and isinstance(v, (str, int)) and not isinstance(v, bool) for k, v in origin.items())): raise Refusal("origin", code="SIM_PUBLICATION_INPUT_INVALID")
            body["origin"] = dict(origin)                                                          # R50: the emitter's pointer to the committed lifecycle record this status was derived from (provenance, not authority)
        return self._sj.append(self._sj.head() if expected_side_head is None else expected_side_head, STATUS_KIND, body)       # R51: with a pinned side HEAD the append is compare-and-append against the basis the emitter validated (HeadMismatch otherwise)
    @property
    def feature_journal(self):
        """Read-only handle to the OWNING journal this path re-reads (the emitter reads the committed lifecycle record from it)."""
        return self._fj
    def records(self):
        """Decoded committed side records (read-only copies)."""
        return self._records()
    def _records(self):
        head = self._sj.head(); out = []
        for r in (self._sj.read_from(1) if head != GENESIS_HEAD else []):
            if r.kind != STATUS_KIND: raise Refusal(r.kind, code="SIM_PUBLICATION_UNKNOWN_RECORD_KIND")
            out.append(json.loads(r.body_json))
        return out
    def _check_source(self, recs):
        """Fail closed unless, for EVERY committed feature key, the accepted binding still holds and the LATEST record's recorded owning HEAD equals the owning journal's CURRENT head with the version still live."""
        cur = self._fj.head(); latest = {}
        for b in recs: latest[b["feature_key"]] = b
        for b in recs:
            ns, _, ver = b["feature_key"].rpartition("/"); st = replay(ns, self._fj.read_from(1)).get(ver)
            if st is None or st.accepted_seq != b["accepted_seq"] or st.accepted_hash != b["accepted_hash"] or st.accepted_body["manifest_hash"] != b["row"]["quant_manifest_hash"]: raise Refusal(b["feature_key"], code="SIM_PUBLICATION_ACCEPTED_BINDING_MISMATCH")
            if latest[b["feature_key"]] is b:
                if st.status not in LIVE_STATES: raise Refusal(st.status, code="SIM_PUBLICATION_SOURCE_NOT_LIVE")
                if (b.get("source_head_seq"), b.get("source_head_hash")) != (cur.seq, cur.hash): raise Refusal(b["feature_key"], code="SIM_PUBLICATION_SOURCE_HEAD_ADVANCED")
    def source_current(self) -> bool:
        """The guard handed to the projection: True only when `_check_source` passes. Never raises."""
        try: self._check_source(self._records()); return True
        except Refusal: return False
        except (ValueError, KeyError, TypeError): return False
    def rows(self):
        """Decoded PublishedRows; EVERY row's accepted binding and the owning HEAD are re-read from the feature journal first (fail closed on a missing/changed accepted record, an advanced head, or a non-live version)."""
        recs = self._records(); self._check_source(recs); out = []
        for b in recs:
            w = b["row"]
            out.append(PublishedRow(bytes.fromhex(w["feature_id"]), w["feature_version"], bytes.fromhex(w["quant_manifest_hash"]), bytes.fromhex(w["instrument_id"]), bytes.fromhex(w["timeframe_id"]), w["materialization_version"], w["step_index"], w["event_time"], w["logical_encoding_version"], w["published_projection_name"],
                                    bytes.fromhex(w["published_projection_bits"]), bytes.fromhex(w["published_projection_hash"]), _unref(w["fit_generation_ref"]), w["data_vintage_mode"], w["available_asof"], w["visible_at"], _unref(w["source_or_causal_policy_ref"]), _unref(w["canonical_transition_ref"])))
        return out
    def status_projection(self):
        p = StatusProjection(self._sj, self._decode, simulation=True, source_guard=self.source_current); p.refresh(); return p
    def feed(self, gateway):
        rs = self.rows()
        for r in rs: gateway.publish(r)
        return len(rs)
