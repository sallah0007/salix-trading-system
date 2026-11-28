"""R37: source-present Registry semantics that no earlier module modelled (Registry p105-124 snapshot manifest field set, p242 canonical-survivor merge direction, p267-279 lifecycle vocabulary).
Typed and validated; NOTHING here fixes a byte layout: `manifest_hash` is a labelled CANDIDATE domain hash over canonical JSON bytes (the Registry says 'immutable content-hashed' but defines no encoding), no transition graph between lifecycle states is invented, and no authority is conferred (a valid manifest object is not an accepted snapshot).
"""
from dataclasses import dataclass, fields as dc_fields
from typing import Optional
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes, domain_hash
LIFECYCLE_STATES = ("PROPOSED", "REGISTERED", "VALIDATION", "ACTIVE", "ACTIVE_ON_DEMAND", "EXPERIMENTAL_UNCLASSIFIED", "QUARANTINED", "DORMANT", "SUPPRESSED", "DEPRECATED", "RETIRED", "REJECTED_INVALID")      # Registry p267-279 'as applicable'
def check_lifecycle_state(s):
    if s not in LIFECYCLE_STATES: raise Refusal(repr(s), code="LIFECYCLE_STATE_UNKNOWN")
    return s
ORIGINS = ("BUILDER", "NATIVE", "EXTERNAL")
def merge_direction(a: dict, b: dict) -> dict:
    """Registry p242: for PROVEN pure duplicates with DIFFERENT origin classes the identity with independent governed source authority survives; NATIVE survives over BUILDER when both are proven identical; the direction is explicit and recorded. a/b: {"id", "origin", "independent_source_authority": bool}, plus both must carry `proven_identical: True`.
    Anything the source does not decide (same origin, both or neither with authority and no NATIVE/BUILDER pair, unproven identity) REFUSES (`MERGE_DIRECTION_UNDETERMINED`): it is never defaulted."""
    for x in (a, b):
        if not (isinstance(x, dict) and isinstance(x.get("id"), str) and x["id"] and x.get("origin") in ORIGINS and type(x.get("independent_source_authority")) is bool): raise Refusal("identity", code="MERGE_INPUT_INVALID")
    if a["id"] == b["id"] or not (a.get("proven_identical") is True and b.get("proven_identical") is True): raise Refusal("identity", code="MERGE_DIRECTION_UNDETERMINED")
    if a["origin"] == b["origin"]: raise Refusal("origin", code="MERGE_DIRECTION_UNDETERMINED")
    auth = [x for x in (a, b) if x["independent_source_authority"]]
    if len(auth) == 1: s, rule = auth[0], "INDEPENDENT_GOVERNED_SOURCE_AUTHORITY"
    elif {a["origin"], b["origin"]} == {"NATIVE", "BUILDER"} and len(auth) in (0, 2): s, rule = (a if a["origin"] == "NATIVE" else b), "NATIVE_OVER_BUILDER"
    else: raise Refusal("rule", code="MERGE_DIRECTION_UNDETERMINED")
    m = b if s is a else a
    return {"survivor": s["id"], "merged": m["id"], "rule": rule, "recorded": True}
def resolve_survivor_chain(pointers: dict, start: str, limit: int = 64) -> tuple:
    """Registry p242 'transitive, acyclic and terminating': follow CANONICAL_SURVIVOR_ID pointers; a cycle, a chain longer than `limit` or a non-string pointer REFUSES."""
    if not isinstance(pointers, dict) or not isinstance(start, str): raise Refusal("pointers", code="SURVIVOR_INPUT_INVALID")
    chain, cur = [start], start
    while pointers.get(cur) is not None:
        nxt = pointers[cur]
        if not isinstance(nxt, str) or not nxt: raise Refusal(cur, code="SURVIVOR_INPUT_INVALID")
        if nxt in chain: raise Refusal(nxt, code="SURVIVOR_CYCLE")
        chain.append(nxt)
        if len(chain) > limit: raise Refusal(start, code="SURVIVOR_CHAIN_NOT_TERMINATING")
        cur = nxt
    return tuple(chain)
MODES = ("ORIGINAL_AS_OBSERVED", "CURRENT_CORRECTED", "CURRENT_RECOMPUTED")
@dataclass(frozen=True)
class TrackerSnapshotManifest:
    """The 15 Registry p106-120 binding fields (names as source) for ONE coherent causal read boundary. `timeframe_watermarks` = ((timeframe, resolved vintage/watermark), ...) per p102; `enrichment_ids` may be empty (p124 later enrichments are not part of the original boundary)."""
    tracker_snapshot_id: str; instrument_id: str; timeframe_or_event_class: str; canonical_bar_or_event_identity: str; broker_server_time_identity: str; utc_identity: str; broker_utc_rule_version: str; source_provider_identity: str; raw_source_version: str
    tracker_schema_calculation_family_version: str; data_quality_missingness_staleness: str; creation_effective_available_asof_identities: str; data_vintage_mode: str; external_enrichment_ids: tuple; fence_read_boundary_identity: str; query_asof: int; snapshot_fence_ts: int; timeframe_watermarks: tuple
    def validate(self):
        for f in dc_fields(self):
            v = getattr(self, f.name)
            if f.name in ("external_enrichment_ids", "timeframe_watermarks"): continue
            if f.name in ("query_asof", "snapshot_fence_ts"):
                if type(v) is not int or v < 0: raise Refusal(f.name, code="SNAPSHOT_MANIFEST_FIELD_INVALID")
            elif not isinstance(v, str) or not v: raise Refusal(f.name, code="SNAPSHOT_MANIFEST_FIELD_MISSING")
        if self.data_vintage_mode not in MODES: raise Refusal(self.data_vintage_mode, code="SNAPSHOT_VINTAGE_MODE_UNKNOWN")
        if not (isinstance(self.external_enrichment_ids, tuple) and all(isinstance(x, str) and x for x in self.external_enrichment_ids)): raise Refusal("enrichment", code="SNAPSHOT_MANIFEST_FIELD_INVALID")
        w = self.timeframe_watermarks
        if not (isinstance(w, tuple) and w and all(isinstance(p, tuple) and len(p) == 2 and isinstance(p[0], str) and p[0] and type(p[1]) is int and p[1] >= 0 for p in w)) or len({p[0] for p in w}) != len(w): raise Refusal("watermarks", code="SNAPSHOT_TIMEFRAME_WATERMARKS_REQUIRED")      # p102: no false simultaneity
        if any(p[1] > self.snapshot_fence_ts for p in w): raise Refusal("watermark", code="SNAPSHOT_WATERMARK_AFTER_FENCE")
        if self.query_asof > self.snapshot_fence_ts: raise Refusal("query_asof", code="SNAPSHOT_QUERY_ASOF_AFTER_FENCE")
        return self
    def manifest_hash(self) -> str:
        self.validate(); d = {f.name: (list(map(list, getattr(self, f.name))) if f.name == "timeframe_watermarks" else list(getattr(self, f.name)) if f.name == "external_enrichment_ids" else getattr(self, f.name)) for f in dc_fields(self)}
        return domain_hash("SALIX_TRACKER_SNAPSHOT_MANIFEST_CANDIDATE_V1", canonical_bytes(d))
def included_in_snapshot(available_asof: int, snapshot_fence_ts: int) -> bool:
    """Registry p123, half-open and architecture-level: INCLUDED iff available_asof < fence; equality excluded."""
    if type(available_asof) is not int or type(snapshot_fence_ts) is not int: raise Refusal("ts", code="SNAPSHOT_TS_INVALID")
    return available_asof < snapshot_fence_ts
def check_mixed_vintage(feature_modes: dict, declared_policy_allows_mixed: Optional[bool], claimed_mode: Optional[str]) -> str:
    """Registry p122/p182-183: a multi-feature view claims ONE homogeneous mode only if every feature has it; otherwise it must be MIXED_DECLARED and the consumer needs an explicit current allow-policy (None/False => MIXED_VINTAGE_POLICY_UNSET = REJECT)."""
    if not (isinstance(feature_modes, dict) and feature_modes and all(m in MODES for m in feature_modes.values())): raise Refusal("modes", code="SNAPSHOT_VINTAGE_MODE_UNKNOWN")
    ms = set(feature_modes.values())
    if len(ms) == 1: 
        if claimed_mode not in (None, next(iter(ms))): raise Refusal(str(claimed_mode), code="CLAIMED_MODE_NOT_HOMOGENEOUS_MODE")
        return next(iter(ms))
    if claimed_mode != "MIXED_DECLARED": raise Refusal("mixed", code="MIXED_VINTAGE_NOT_DECLARED")
    if declared_policy_allows_mixed is not True: raise Refusal("policy", code="MIXED_VINTAGE_POLICY_UNSET")
    return "MIXED_DECLARED"
