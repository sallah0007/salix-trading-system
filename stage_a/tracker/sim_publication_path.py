"""R37: an explicit SAME-CLASS SIMULATION committed-journal candidate path from an ACTUAL accepted receipt to the Gateway's PublishedRow and chain-status inputs.
It replaces the literal `PublishedRow` / bare `ChainStatusAuthority(allow_uncommitted_status=True)` seeding of the older test gateways with committed records:
  accepted record (the per-feature journal, re-read by `accepted_manifest.read_accepted_manifest`: bytes re-hashed) -> `commit` appends SIM_PUBLICATION_ROW and SIM_STATUS_FACT to a SEPARATE SIMULATION journal (never the feature transition journal, whose replay owns its record kinds)
  -> `rows()` re-reads each row's accepted binding from the feature journal and fails closed on any mismatch -> `status_projection()` is a `StatusProjection(simulation=True)` over that journal -> `feed(gateway)` publishes the decoded rows.
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
ROW_KIND, STATUS_KIND = "SIM_PUBLICATION_ROW", "SIM_STATUS_FACT"
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
        self._seq = 0
    def commit(self, feature_key, supplied: SuppliedRowInputs, status_token, *, sequence, correction=False):
        if not isinstance(supplied, SuppliedRowInputs) or status_token not in self._spec["status_map"] or type(sequence) is not int or sequence < 1 or type(correction) is not bool: raise Refusal("inputs", code="SIM_PUBLICATION_INPUT_INVALID")
        rb = AM.read_accepted_manifest(self._fj, self._st, feature_key)                         # the ACTUAL accepted receipt, manifest bytes re-hashed
        if not (isinstance(supplied.feature_id, bytes) and len(supplied.feature_id) == 16 and isinstance(supplied.instrument_id, bytes) and len(supplied.instrument_id) == 16 and isinstance(supplied.timeframe_id, bytes) and len(supplied.timeframe_id) == 16): raise Refusal("ids", code="SIM_PUBLICATION_INPUT_INVALID")
        row = {"feature_version": feature_key.feature_version, "quant_manifest_hash": rb.manifest_hash}                       # bound from the receipt
        for k in ("feature_id", "instrument_id", "timeframe_id", "published_projection_bits", "published_projection_hash"): row[k] = getattr(supplied, k).hex()
        for k in ("materialization_version", "step_index", "event_time", "logical_encoding_version", "published_projection_name", "data_vintage_mode", "available_asof", "visible_at"): row[k] = getattr(supplied, k)
        for k in ("fit_generation_ref", "source_or_causal_policy_ref", "canonical_transition_ref"): row[k] = _ref(getattr(supplied, k))
        self._sj.append(self._sj.head(), ROW_KIND, {"feature_key": rb.feature_key, "accepted_seq": rb.accepted_seq, "accepted_hash": rb.accepted_hash, "row": row})
        mvn = self._spec["mv"]; bf = self._spec["bytes_fields"]; vals = (supplied.feature_id, feature_key.feature_version, supplied.instrument_id, supplied.timeframe_id, supplied.materialization_version)
        body = {n: (v.hex() if n in bf else v) for n, v in zip(mvn, vals)}
        body.update({self._spec["status_field"]: status_token, self._spec["sequence_field"]: sequence, self._spec["available_asof_field"]: supplied.available_asof, self._spec["correction_field"]: correction, "accepted_seq": rb.accepted_seq, "accepted_hash": rb.accepted_hash})
        return self._sj.append(self._sj.head(), STATUS_KIND, body)
    def rows(self):
        """Decoded PublishedRows; EVERY row's accepted binding is re-read from the feature journal first (fail closed on a missing/changed accepted record)."""
        head = self._sj.head(); out = []
        for r in (self._sj.read_from(1) if head != GENESIS_HEAD else []):
            if r.kind not in (ROW_KIND, STATUS_KIND): raise Refusal(r.kind, code="SIM_PUBLICATION_UNKNOWN_RECORD_KIND")
            b = json.loads(r.body_json); ns, _, ver = b.get("feature_key", "").rpartition("/") if r.kind == ROW_KIND else ("", "", "")
            if r.kind != ROW_KIND: continue
            st = replay(ns, self._fj.read_from(1)).get(ver)
            if st is None or st.accepted_seq != b["accepted_seq"] or st.accepted_hash != b["accepted_hash"] or st.accepted_body["manifest_hash"] != b["row"]["quant_manifest_hash"]: raise Refusal(b["feature_key"], code="SIM_PUBLICATION_ACCEPTED_BINDING_MISMATCH")
            w = b["row"]
            out.append(PublishedRow(bytes.fromhex(w["feature_id"]), w["feature_version"], bytes.fromhex(w["quant_manifest_hash"]), bytes.fromhex(w["instrument_id"]), bytes.fromhex(w["timeframe_id"]), w["materialization_version"], w["step_index"], w["event_time"], w["logical_encoding_version"], w["published_projection_name"],
                                    bytes.fromhex(w["published_projection_bits"]), bytes.fromhex(w["published_projection_hash"]), _unref(w["fit_generation_ref"]), w["data_vintage_mode"], w["available_asof"], w["visible_at"], _unref(w["source_or_causal_policy_ref"]), _unref(w["canonical_transition_ref"])))
        return out
    def status_projection(self):
        p = StatusProjection(self._sj, self._decode, simulation=True); p.refresh(); return p
    def feed(self, gateway):
        rs = self.rows()
        for r in rs: gateway.publish(r)
        return len(rs)
