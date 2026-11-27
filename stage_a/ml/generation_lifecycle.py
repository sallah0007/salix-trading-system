"""ML Core (V1.11 overlay + retained V1.10) candidate mechanics for the generation manifest / lifecycle that the ML writer/finalizer duties rest on: immutable CERTIFIED_GENERATION_MANIFEST (section A), append-only
GENERATION_LIFECYCLE_LEDGER with a monotonic LIFECYCLE_EPOCH (28.A), eligibility from BOTH manifest and latest ledger state, request-scoped generation snapshot (28.B), ATOMIC compare-and-publish against the epoch (29.A),
fence-failure => DISCARDED/QUARANTINED with no retroactive regeneration (30.B, RETROACTIVE_SHADOW_BACKFILL = PROHIBITED) and pre-snapshot event reconstruction from the ledger with no current-generation default (31.B),
append-only later-revocation annotation read at use (29.D).
SCOPE: this is an ML-OWNED candidate store in memory (its own ledger, NOT a Tracker authority and not the Tracker journal); it creates no ML science and authorizes no training/serving. Not source-defined, so NOT invented
here: the manifest/hash byte composition (hashes are SUPPLIED strings, never recomputed or claimed verified), the lifecycle transition graph (only the four source-named states are accepted; the ONLY transitions refused are exits from REVOKED/SUPERSEDED, held as unresolved restoration - no table of permitted transitions is claimed),
the governed taxonomy beyond the three source-named outcomes, the component list beyond the source's 'at minimum' set, and who the lifecycle authority is (`authority` is a supplied label)."""
import threading
from dataclasses import dataclass, field
from typing import Optional
from ..errors import Refusal

MIN_COMPONENTS = ("model_artifact", "feature_pack", "target_pack", "fitted_transforms", "calibrator", "ood_support_objects", "code_environment_identity", "training_data_identity", "validation_generation", "authority_state")
STATES = ("CANDIDATE", "COMPLETE_CERTIFIED", "SUPERSEDED", "REVOKED")
PUBLISHED, REJECTED_DISCARDED, REJECTED_QUARANTINED = "PUBLISHED", "DISCARDED", "QUARANTINED"
MISSED, NOT_PROVABLY_RECONSTRUCTABLE = "MISSED", "NOT_PROVABLY_RECONSTRUCTABLE"
HELD_MISSED_OR_QUARANTINED, RECONSTRUCTED_CANDIDATE = "HELD_MISSED_OR_QUARANTINED", "RECONSTRUCTED_CANDIDATE_EVIDENCE_UNADMITTED"
def _s(x): return isinstance(x, str) and bool(x)
def _i(x): return type(x) is int and x >= 0

@dataclass(frozen=True)
class CertifiedGenerationManifest:
    manifest_id: str; manifest_hash: str; components: tuple; generation_id: str; fit_instrument_set: tuple      # components: ((name, hash), ...); generation id / FIT_INSTRUMENT_SET are SUPPLIED labels, not verified here
@dataclass(frozen=True)
class LifecycleEntry:
    manifest_id: str; manifest_hash: str; state: str; ts: int; reason: str; authority: str; epoch: int
@dataclass(frozen=True)
class EventIdentity:
    """31.B minimum causal event identity; knowledge_boundary is the governed knowledge-time boundary (supplied)."""
    forecast_ts: int; instrument_id: str; target_horizon_id: str; knowledge_boundary: int; source_event_id: Optional[str] = None
@dataclass(frozen=True)
class SnapshotForRequest:
    """MLCore 28.B / V1.16: binds INSTRUMENT_ID (in `event`), MANIFEST_ID/HASH, GENERATION_ID, LIFECYCLE_EPOCH, feature/target/calibration/OOD identities and request start timestamp. Identities are the manifest's SUPPLIED component hashes."""
    request_id: str; event: EventIdentity; manifest_id: str; manifest_hash: str; generation_id: str; epoch_at_snapshot: int; feature_id: str; target_id: str; calibration_id: str; ood_id: str; request_start_ts: int
@dataclass(frozen=True)
class PublishOutcome:
    status: str; reason: str = ""
@dataclass(frozen=True)
class Reconstruction:
    outcome: str; manifest_id: Optional[str] = None; reason: str = ""

class GenerationRegistry:
    """Single ledger + manifest store under one lock; every publish check and commit is one critical section."""
    def __init__(self):
        self._lock = threading.RLock(); self._manifests = {}; self._ledger = []; self._published = {}; self._events = {}; self._issued = {}; self._commit_hook = None   # hook: TEST seam, runs INSIDE the critical section
    # ---- immutable manifest ----
    def register_manifest(self, m):
        with self._lock:
            if not (isinstance(m, CertifiedGenerationManifest) and _s(m.manifest_id) and _s(m.manifest_hash) and isinstance(m.components, tuple) and _s(m.generation_id) and isinstance(m.fit_instrument_set, tuple) and m.fit_instrument_set and all(_s(i) for i in m.fit_instrument_set)): raise Refusal("manifest", code="ML_MANIFEST_MALFORMED")
            names = [c[0] for c in m.components if isinstance(c, tuple) and len(c) == 2 and _s(c[0]) and _s(c[1])]
            if len(names) != len(m.components) or len(set(names)) != len(names): raise Refusal("components", code="ML_MANIFEST_COMPONENT_MALFORMED")
            missing = [n for n in MIN_COMPONENTS if n not in names]
            if missing: raise Refusal(",".join(missing), code="ML_MANIFEST_INCOMPLETE")      # a partially specified generation is never registered as complete
            old = self._manifests.get(m.manifest_id)
            if old is not None and old != m: raise Refusal(m.manifest_id, code="ML_MANIFEST_IMMUTABLE")
            self._manifests[m.manifest_id] = m
    # ---- append-only ledger ----
    def append_lifecycle(self, manifest_id, state, ts, reason, authority):
        with self._lock:
            m = self._manifests.get(manifest_id)
            if m is None: raise Refusal(manifest_id, code="ML_LIFECYCLE_FOR_UNREGISTERED_MANIFEST")
            if state not in STATES or not _i(ts) or not _s(reason) or not _s(authority): raise Refusal(str(state), code="ML_LIFECYCLE_ENTRY_MALFORMED")
            if self._ledger and ts < self._ledger[-1].ts: raise Refusal("ts", code="ML_LIFECYCLE_TS_REGRESSED")
            prev = self._latest(manifest_id)
            if prev is not None and prev.state in ("REVOKED", "SUPERSEDED") and state != prev.state:
                raise Refusal("%s -> %s" % (prev.state, state), code="ML_LIFECYCLE_RESTORATION_HELD")   # source: a REVOKED generation is not serving-eligible; revival/restore policy (and for SUPERSEDED) is NOT source-defined => HELD, never accepted. No prior-state table is invented: only these two exits are held, all else is recorded as given.
            e = LifecycleEntry(manifest_id, m.manifest_hash, state, ts, reason, authority, len(self._ledger) + 1)     # monotonic epoch = append position
            self._ledger.append(e); return e
    def _latest(self, manifest_id, as_of_ts=None):
        last = None
        for e in self._ledger:
            if e.manifest_id == manifest_id and (as_of_ts is None or e.ts <= as_of_ts): last = e
        return last
    def eligible(self, manifest_id, as_of_ts=None) -> bool:
        """BOTH: a registered complete manifest AND the latest valid ledger state (at as_of_ts if given) COMPLETE_CERTIFIED."""
        with self._lock:
            m = self._manifests.get(manifest_id); l = self._latest(manifest_id, as_of_ts)
            return m is not None and l is not None and l.manifest_hash == m.manifest_hash and l.state == "COMPLETE_CERTIFIED"
    @property
    def epoch(self): return len(self._ledger)
    def ledger(self): return tuple(self._ledger)
    # ---- request snapshot / atomic publish ----
    def snapshot(self, request_id, event, manifest_id, request_start_ts=None) -> SnapshotForRequest:
        with self._lock:
            if not _s(request_id) or not isinstance(event, EventIdentity) or not (_i(event.forecast_ts) and _s(event.instrument_id) and _s(event.target_horizon_id) and _i(event.knowledge_boundary)): raise Refusal("event identity", code="ML_EVENT_IDENTITY_INCOMPLETE")
            if not self.eligible(manifest_id): raise Refusal(manifest_id, code="ML_GENERATION_NOT_SERVING_ELIGIBLE")
            if not _i(request_start_ts): raise Refusal("request_start_ts", code="ML_SNAPSHOT_START_TS_MISSING")
            m = self._manifests[manifest_id]; c = dict(m.components)
            if event.instrument_id not in m.fit_instrument_set: raise Refusal(event.instrument_id, code="ML_INSTRUMENT_NOT_IN_MANIFEST_SCOPE")      # instrument isolation
            snap = SnapshotForRequest(request_id, event, manifest_id, m.manifest_hash, m.generation_id, self.epoch, c["feature_pack"], c["target_pack"], c["calibrator"], c["ood_support_objects"], request_start_ts)
            old = self._issued.get(request_id)
            if old is not None and old != snap: raise Refusal(request_id, code="ML_REQUEST_ID_REUSED_WITH_DIFFERENT_BINDING")
            self._issued[request_id] = snap; return snap
    def compare_and_publish(self, snap, result) -> PublishOutcome:
        """Fence re-check and commit are ONE critical section. Succeeds only if the manifest is still serving-eligible and ITS lifecycle state is unchanged since the snapshot; otherwise the logical event is DISCARDED or
        QUARANTINED (never regenerated under a newer generation, never served as accepted). Idempotent: the same event identity publishes at most once."""
        with self._lock:
            if not isinstance(snap, SnapshotForRequest): raise Refusal("snapshot", code="ML_PUBLISH_NEEDS_REQUEST_SNAPSHOT")
            if self._issued.get(snap.request_id) != snap: raise Refusal(snap.request_id, code="ML_SNAPSHOT_NOT_ISSUED_BY_THIS_REGISTRY")     # exact issued snapshot: any altered hash/epoch/manifest/event/identity/request id fails
            if self._commit_hook: self._commit_hook()
            key = snap.event
            if key in self._published: return PublishOutcome(PUBLISHED, "ALREADY_PUBLISHED_IDEMPOTENT")
            if key in self._events and self._events[key] != PUBLISHED: return PublishOutcome(self._events[key], "EVENT_ALREADY_FAILED_NO_REGENERATION")
            cur = self._latest(snap.manifest_id); at_snap = None
            for e in self._ledger[:snap.epoch_at_snapshot]:
                if e.manifest_id == snap.manifest_id: at_snap = e
            changed = (cur is None) or (at_snap is None) or cur.epoch != at_snap.epoch
            if changed or not self.eligible(snap.manifest_id):
                st = REJECTED_QUARANTINED if (cur is not None and cur.state == "REVOKED") else REJECTED_DISCARDED
                self._events[key] = st; return PublishOutcome(st, "LIFECYCLE_FENCE_CHANGED_AT_COMMIT")
            self._published[key] = (snap, result); self._events[key] = PUBLISHED; return PublishOutcome(PUBLISHED)
    def retry_publish(self, snap, result) -> PublishOutcome:
        """30.B: a failed event may be retried only with the SAME request-scoped snapshot, and only if that generation is still eligible; otherwise it stays DISCARDED/QUARANTINED. Never rebinds to a newer generation."""
        with self._lock:
            st = self._events.get(snap.event)
            if st in (REJECTED_DISCARDED, REJECTED_QUARANTINED): return PublishOutcome(st, "NO_RETROACTIVE_REGENERATION")
            return self.compare_and_publish(snap, result)
    def published(self, event): 
        with self._lock: return self._published.get(event)
    # ---- 31.B reconstruction / 29.D annotation ----
    def reconstruct_for_event(self, event: EventIdentity, current_read_freshness=None, historical_slice_completeness=None) -> Reconstruction:
        """MLCore V1.16 (crash before snapshot persistence): eligibility may be reconstructed from lifecycle history only with BOTH CURRENT_READ_FRESHNESS = PASS and HISTORICAL_SLICE_COMPLETENESS = PASS; otherwise the event is
        MISSED / QUARANTINED (the governed taxonomy choice between them is not source-defined => typed HELD_MISSED_OR_QUARANTINED). Current-generation fallback is prohibited. The two inputs are SUPPLIED evidence tokens: nothing
        here can prove the ledger slice was durably ordered and closed, so even with both PASS the result is a CANDIDATE (RECONSTRUCTED_CANDIDATE_EVIDENCE_UNADMITTED), never AUTHORITATIVE."""
        with self._lock:
            if not isinstance(event, EventIdentity) or not (_i(event.forecast_ts) and _i(event.knowledge_boundary)): raise Refusal("event identity", code="ML_EVENT_IDENTITY_INCOMPLETE")
            if not (current_read_freshness == "PASS" and historical_slice_completeness == "PASS"):
                return Reconstruction(HELD_MISSED_OR_QUARANTINED, None, "CURRENT_READ_FRESHNESS_AND_HISTORICAL_SLICE_COMPLETENESS_NOT_BOTH_PASS")
            t = min(event.forecast_ts, event.knowledge_boundary)
            ok = sorted(m for m in self._manifests if self.eligible(m, t) and event.instrument_id in self._manifests[m].fit_instrument_set)
            if len(ok) == 1: return Reconstruction(RECONSTRUCTED_CANDIDATE, ok[0], "EVIDENCE_TOKENS_SUPPLIED_NOT_VERIFIED")
            return Reconstruction(MISSED if not ok else NOT_PROVABLY_RECONSTRUCTABLE, None, "NO_PROVABLE_ELIGIBLE_GENERATION" if not ok else "AMBIGUOUS_GENERATIONS")
    def annotated(self, event):
        """Later-revocation knowledge is read from the append-only ledger at USE; the stored record is never rewritten."""
        with self._lock:
            rec = self._published.get(event)
            if rec is None: return None
            l = self._latest(rec[0].manifest_id); return {"record": rec, "contributor_lifecycle_now": l.state if l else None, "later_revoked": bool(l and l.state == "REVOKED")}
