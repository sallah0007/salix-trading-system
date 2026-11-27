"""Tracker->Gateway dependency resolution CONTRACT + an in-memory SIMULATED Gateway.

STATUS: contract objects and a simulated resolver. This is NOT a connection to the existing Connected Contract / Gateway
implementation (not present in this repository). It encodes Annex V1.2 §§X, XII and the G1..G9 / OB1 / OB2 families so that a
real Gateway can be held to the same behaviour. Dependency schema is generic (G8): no feature-specific connector exists.
Visibility is half-open: a row is eligible iff available_asof < consumer fence (G1)."""
from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Tuple
from ..errors import Refusal
from ..schema import objects as O
from . import binding as B
from ..schema.encoding import Ref, CodeTables
from ..tracker.chain_status import ChainStatusAuthority, CURRENT

REQUIRED, OPTIONAL = "REQUIRED", "OPTIONAL"
_ENTRY_KEYS = {"feature_id", "feature_version", "requirement_class", "expected_projection", "scope_ref", "temporal_ref",
               "vintage_ref", "health_rule_ref", "absence_rule_ref"}

@dataclass(frozen=True)
class DependencyEntry:
    feature_id: bytes; feature_version: str; requirement_class: str; expected_projection: str
    scope_ref: Ref; temporal_ref: Ref; vintage_ref: Ref; health_rule_ref: Ref; absence_rule_ref: Optional[Ref] = None
    def __post_init__(self):
        if self.requirement_class not in (REQUIRED, OPTIONAL):
            raise Refusal(self.requirement_class, code="BAD_REQUIREMENT_CLASS")
        if (self.requirement_class == OPTIONAL) != (self.absence_rule_ref is not None):
            raise Refusal("ABSENCE_HANDLING_RULE_REF required iff OPTIONAL", code="ABSENCE_RULE_PRESENCE")
    @classmethod
    def from_dict(cls, d: dict):
        extra = set(d) - _ENTRY_KEYS
        if extra:                                           # G8: no feature-specific schema fields
            raise Refusal(",".join(sorted(extra)), code="FEATURE_SPECIFIC_FIELD_REFUSED")
        return cls(**d)

@dataclass(frozen=True)
class PublishedRow:
    """What the Tracker has canonically published (the Gateway reads this; it never reads private Tracker state)."""
    feature_id: bytes; feature_version: str; quant_manifest_hash: bytes; instrument_id: bytes; timeframe_id: bytes
    materialization_version: str; step_index: int; event_time: int; logical_encoding_version: str
    published_projection_name: str; published_projection_bits: bytes; published_projection_hash: bytes
    fit_generation_ref: Optional[Ref]; data_vintage_mode: str; available_asof: int; visible_at: int
    source_or_causal_policy_ref: Ref; canonical_transition_ref: Ref

@dataclass(frozen=True)
class HealthSnapshot:
    resolution_ref: Ref; resolved_at: int; acceptable: bool

@dataclass(frozen=True)
class HealthBinding:
    """INTERNAL candidate binding of a Core-produced Health reading to the exact dependency it speaks for, in the Gateway's own identifier vocabulary (no canonical field/layout is invented; an ADMITTED
    external binding/provenance is a separate input and is not modelled here)."""
    feature_id: bytes; feature_version: str; instrument_id: bytes; timeframe_id: bytes

@dataclass(frozen=True)
class NonDeliveryResolution:
    request_id: str; feature_id: bytes; feature_version: str; reason: str; fence: int

@dataclass(frozen=True)
class AbsenceApplied:
    request_id: str; feature_id: bytes; feature_version: str; absence_handling_applied_ref: Ref

@dataclass(frozen=True)
class Binding:
    request_id: str; entry: O.DeliveredFeatureEntry; delivered_feature_hash: bytes; fence: int

class SimulatedGateway:
    """Resolves dependencies at a consumer fence and stores each outcome ONCE (G4 idempotent, G5/G6 immutable)."""
    def __init__(self, tables: CodeTables, status, watermark: int = 0, allow_uncommitted_status: bool = False, health_source=None, allow_shape_only_health: bool = False):
        """status must be a committed-journal projection (tracker.status_projection.StatusProjection, `authoritative` True). A bare in-memory ChainStatusAuthority
        is NOT consumer-authoritative: it is accepted only when allow_uncommitted_status=True (tests/simulation), never by default."""
        self.t, self.status, self.watermark = tables, status, watermark
        self.allow_uncommitted_status = allow_uncommitted_status
        self.health_source = health_source                    # object with confirm_snapshot(snapshot)->bool (the Core that issued the snapshot); no source => Core snapshots are NOT confirmable and are denied
        self.allow_shape_only_health = allow_shape_only_health  # LEGACY shape-only harness switch: a plain HealthSnapshot proves nothing about any subject. Default False: denied.
        self.final_store = None                                 # R35: optional v038.FinalResolutionStore; `resolve_window` is the ONLY path that uses it
        self._window_outcome: Dict[object, object] = {}       # identity -> the durably CONFIRMED outcome object
        self._window_issued: Dict[tuple, object] = {}         # (consumer_id, request_id) -> confirmed outcome; consumer-local namespace, never mixed with the legacy request-id cache
        self.rows: Dict[tuple, list] = {}
        self._outcomes: Dict[str, object] = {}
        self._later_lineage: Dict[str, list] = {}
    def publish(self, row: PublishedRow):
        k = (row.feature_id, row.feature_version, row.instrument_id, row.timeframe_id)
        self.rows.setdefault(k, []).append(row)
    def set_watermark(self, w: int): self.watermark = w
    def outcome(self, request_id, consumer_id=None):
        """Request-id keyed outcomes (legacy `resolve`) are global to this Gateway. WINDOW outcomes are consumer-local (H1: REQUEST_ID is consumer-local) and are visible only through a consumer-qualified read and only after the durable final store confirmed them."""
        if consumer_id is not None:
            o = self._window_issued.get((consumer_id, request_id))
            if o is not None: return o
        return self._outcomes.get(request_id)
    def later_lineage(self, request_id): return tuple(self._later_lineage.get(request_id, ()))

    def _store(self, request_id, outcome):
        self._outcomes[request_id] = outcome
        return outcome

    def resolve(self, request_id: str, entry: DependencyEntry, instrument_id: bytes, timeframe_id: bytes, step_index: int,
                fence: int, health: HealthSnapshot, require_current: bool = True, data_vintage_mode: Optional[str] = None,
                observed_at: Optional[int] = None):
        done = self._outcomes.get(request_id)
        if done is not None:                                         # G4: retry returns the identical stored outcome
            return done
        return self._compute(request_id, entry, instrument_id, timeframe_id, step_index, fence, health, require_current, data_vintage_mode, observed_at, self._store)

    def _compute(self, request_id, entry, instrument_id, timeframe_id, step_index, fence, health, require_current, data_vintage_mode, observed_at, _sink):
        """Pure evaluation of one dependency at a fence. `_sink(request_id, outcome)` is the ONLY place an outcome is published: `resolve` passes the request-id cache; `resolve_window` passes an identity function so a provisional outcome is NOT visible to any consumer until the durable final store has confirmed it (R36)."""
        def nd(reason):
            return _sink(request_id, NonDeliveryResolution(request_id, entry.feature_id, entry.feature_version, reason, fence))
        if self.watermark < fence:                                   # G7: stale currentness/revocation watermark
            return nd("STALE_WATERMARK")
        cands = [r for r in self.rows.get((entry.feature_id, entry.feature_version, instrument_id, timeframe_id), [])
                 if r.step_index == step_index and r.published_projection_name == entry.expected_projection]
        if not cands:
            if entry.requirement_class == OPTIONAL:                  # G9: only via the exact governed absence rule
                return _sink(request_id, AbsenceApplied(request_id, entry.feature_id, entry.feature_version, entry.absence_rule_ref))
            return nd("REQUIRED_DEPENDENCY_ABSENT")                  # G3
        row = cands[-1]
        if row.available_asof >= fence:                              # G1: equality at the fence is excluded
            return nd("NOT_AVAILABLE_BEFORE_FENCE") if entry.requirement_class == REQUIRED else _sink(
                request_id, AbsenceApplied(request_id, entry.feature_id, entry.feature_version, entry.absence_rule_ref))
        obs = fence if observed_at is None else observed_at         # V0.38: resolver observes at fence + SETTLEMENT_DELAY
        if row.visible_at >= obs:                                    # not visible to the resolver: causal set NOT widened
            return nd("LATE_VISIBILITY")
        if data_vintage_mode is not None and row.data_vintage_mode != data_vintage_mode:
            return nd("DATA_VINTAGE_MODE_MISMATCH")
        mv = (row.feature_id, row.feature_version, row.instrument_id, row.timeframe_id, row.materialization_version)
        if not getattr(self.status, "authoritative", False) and not self.allow_uncommitted_status:
            return nd("STATUS_SOURCE_NOT_COMMITTED_PROJECTION")      # fail closed: a direct append is not consumer authority
        try:
            st = self.status.status_at(mv, fence)
        except Refusal:
            return nd("STATUS_PROJECTION_UNAVAILABLE")
        if st is None:
            return nd("NO_STATUS_AUTHORITY_FACT")                    # fail closed on the unread
        if require_current and st.status != CURRENT:
            return nd("CHAIN_STATUS_NOT_CURRENT:" + st.status)       # CATCHING_UP where CURRENT required
        from ..core.tracker_core import CoreHealthSnapshot
        if type(health) is CoreHealthSnapshot:                       # decided by TYPE, never by an optional marker field: Core snapshot must be journal-confirmed and bound to exactly this dependency
            if self.health_source is None or not self.health_source.confirm_snapshot(health): return nd("HEALTH_SNAPSHOT_NOT_CONFIRMED")
            b = health.binding
            if b is None: return nd("HEALTH_BINDING_UNBOUND")
            if (b.feature_id, b.feature_version, b.instrument_id, b.timeframe_id) != (entry.feature_id, entry.feature_version, instrument_id, timeframe_id): return nd("HEALTH_BINDING_MISMATCH")
        elif not self.allow_shape_only_health: return nd("HEALTH_SNAPSHOT_SHAPE_ONLY_NOT_ACCEPTED")        # a plain snapshot is not verified Health for any subject
        if not health.acceptable:
            return nd("HEALTH_UNACCEPTABLE")
        if type(health) is CoreHealthSnapshot and not self.health_source.snapshot_current_at_use(health, fence):
            return nd("HEALTH_SNAPSHOT_NOT_CURRENT_AT_USE")             # issuance integrity is not current permission: re-read the CURRENT journal at use (quarantine/epoch/expiry/proof)
        if health.resolved_at >= fence:
            return nd("HEALTH_NOT_RESOLVED_BEFORE_FENCE")
        d = B.build_delivered_entry(row, st.status, health.resolution_ref, health.resolved_at)
        return _sink(request_id, Binding(request_id, d, O.delivered_hash(self.t, d), fence))

    def resolve_window(self, request_id: str, identity, entry: DependencyEntry, instrument_id: bytes, timeframe_id: bytes, step_index: int, fence: int, health,
                       require_current: bool = True, data_vintage_mode: Optional[str] = None, observed_at: Optional[int] = None):
        """Window-level resolution (Contract V0.38 FINAL RESOLUTION IDENTITY, current 52-56): a NEW REQUEST_ID for the SAME final resolution identity reuses the stored outcome and is never re-evaluated. REQUEST_ID alone is not the identity.
        The identity (consumer_id, binding id, scope, window/fence id) is SUPPLIED and its string encoding is not defined by any source read, so it is not derived here; instead the FIRST evaluation pins the exact evaluation parameters to the identity
        and a later call that names the same identity with DIFFERENT parameters (dependency, version, instrument, timeframe, step, fence, vintage mode, observation time) is refused rather than silently answered with another window's outcome.
        Candidate/simulation only: the store is the single-process FinalResolutionStore (D10); `resolve` (request-id keyed) is unchanged and does NOT use the final store."""
        if self.final_store is None: raise Refusal("no final store", code="GATEWAY_FINAL_RESOLUTION_STORE_NOT_CONFIGURED")
        if not isinstance(request_id, str) or not request_id: raise Refusal("request_id", code="GATEWAY_REQUEST_ID_INVALID")
        cid = getattr(identity, "consumer_id", None)
        gov = [x.hex() if isinstance(x, bytes) else x for x in (entry.feature_id, entry.feature_version, entry.requirement_class, entry.expected_projection, instrument_id, timeframe_id, step_index, fence, require_current, data_vintage_mode)]
        prior = self.final_store.pin_of(identity)
        if prior is not None and prior != gov: raise Refusal(request_id, code="RESOLUTION_IDENTITY_PARAMETERS_DIFFER")        # governing parameters only; the retry's observation clock is NOT part of the identity
        if request_id in self._outcomes: raise Refusal(request_id, code="REQUEST_ID_USED_OUTSIDE_THIS_WINDOW")                # the legacy global request-id cache already owns this id (misuse guard retained)
        def evaluate():
            if prior is None: self.final_store.set_pin(identity, gov, {"observed_at": observed_at, "watermark": self.watermark})   # facts of the FIRST evaluation: immutable, never compared
            return self._compute(request_id, entry, instrument_id, timeframe_id, step_index, fence, health, require_current, data_vintage_mode, observed_at, lambda rid, o: o)   # provisional: published nowhere
        out = self.final_store.resolve(request_id, identity, evaluate)                    # COMMIT POINT: raises, with nothing published, unless the store durably holds this outcome
        canon = self._window_outcome.get(identity)
        if canon is None: canon = self._window_outcome[identity] = out                  # first confirmation (or restart: adopt the STORED outcome, the store is the authority)
        elif canon != out: raise Refusal(request_id, code="WINDOW_OUTCOME_STORE_DISAGREES")
        self._window_issued.setdefault((cid, getattr(canon, "request_id", request_id)), canon)      # the outcome object names the request that first decided it; the identity record (not that request's binding) is the commit
        return self._window_issued.setdefault((cid, request_id), canon)

    def note_correction_after_bind(self, request_id: str, evidence: Ref):
        """Correction after bind: the stored binding is NOT rewritten; later lineage evidence is appended beside it."""
        if not isinstance(self._outcomes.get(request_id), Binding):
            raise Refusal(request_id, code="NO_BINDING_TO_ANNOTATE")
        self._later_lineage.setdefault(request_id, []).append(evidence)
