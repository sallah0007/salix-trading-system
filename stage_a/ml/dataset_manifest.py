"""ML DATASET / FEATURE-MATRIX PROVENANCE manifest registry, reverse binding link, bind-time Health resolution and the revoked-data ancestry gate (generic, ML-side; unqualified).
Sources: ML Core V1.16 (Drive 1cf1uR0wJLPVsWitIy9aVLM9CZPk2fyd4bP_3tFyLKrw; staged text lines 398/2535/2840-2855): every training/validation/calibration/OOD dataset carries a versioned DATASET_PROVENANCE_MANIFEST (or equivalent) binding dataset hash, source contracts, source identities, row provenance,
instrument scope, construction code/version, transformation lineage and feed-era identity; DATASET manifests are first-class REVOCATION subjects (31.C) and a model trained on a revoked dataset is blocked by the revoked-ancestry review gate even with no weight ancestor in common. ML Integration Binding Addendum V1 s6: the
dataset manifest has NO forward CONSUMER_BINDING field; linkage is the REVERSE reference CONSUMER_BINDING.MANIFEST_OR_DATASET_BINDING_ID -> manifest, and through that binding to the bind-time Health Resolution Snapshot.
NOT invented: the canonical byte/hash encoding of the manifest (`manifest_hash` is a SUPPLIED label, never recomputed here), the writer principal (writes need a SUPPLIED grant slot; none => HELD), any revocation authority beyond an append-only REVOKED entry recorded with the supplied authority string."""
from dataclasses import dataclass
from ..errors import Refusal
from . import consumption_claim as CC
FIELDS = ("dataset_hash", "source_contracts", "source_identities", "row_provenance", "instrument_scope", "construction_code_version", "transformation_lineage", "feed_era_id")
def _s(x): return isinstance(x, str) and bool(x)
def _t(x): return isinstance(x, tuple) and bool(x) and all(_s(i) for i in x) and len(set(x)) == len(x)

@dataclass(frozen=True)
class DatasetProvenanceManifest:
    dataset_manifest_id: str; manifest_hash: str; dataset_hash: str; source_contracts: tuple; source_identities: tuple; row_provenance: str; instrument_scope: tuple; construction_code_version: str; transformation_lineage: tuple; feed_era_id: str

class DatasetRegistry:
    def __init__(self, grants=None, grant_source_ref=None):
        self._m = {}; self._ledger = []; self._links = {}
        if grants is not None and not (isinstance(grants, (set, frozenset)) and grants and all(_s(g) for g in grants) and _s(grant_source_ref)): raise Refusal("grants", code="ML_PRINCIPAL_GRANTS_INVALID")
        self._grants = None if grants is None else frozenset(grants); self.grant_source_ref = grant_source_ref if grants else None
    def _need(self, caller):
        if self._grants is None: raise Refusal("grants", code="ML_PRINCIPAL_GRANTS_UNBOUND_HELD")
        if not _s(caller) or caller not in self._grants: raise Refusal("caller", code="ML_CALLER_NOT_GRANTED")
    def register(self, caller, m):
        self._need(caller)
        if not (isinstance(m, DatasetProvenanceManifest) and _s(m.dataset_manifest_id) and _s(m.manifest_hash) and _s(m.dataset_hash) and _t(m.source_contracts) and _t(m.source_identities) and _s(m.row_provenance) and _t(m.instrument_scope) and _s(m.construction_code_version) and _t(m.transformation_lineage) and _s(m.feed_era_id)): raise Refusal("manifest", code="DATASET_MANIFEST_MALFORMED")
        old = self._m.get(m.dataset_manifest_id)
        if old is not None:
            if old[1] != m: raise Refusal(m.dataset_manifest_id, code="DATASET_MANIFEST_IMMUTABLE")
            return old[1]                                                                  # identical retry is idempotent, the original writer stays the writer
        self._m[m.dataset_manifest_id] = (caller, m); return m
    def manifest(self, mid): e = self._m.get(mid); return None if e is None else e[1]
    def writer_of(self, mid): e = self._m.get(mid); return None if e is None else e[0]
    def revoke(self, caller, mid, ts, reason, authority):
        """Append-only REVOKED / INVALID_FOR_NEW_CERTIFICATION (ML Core 31.C). Never un-revoked here (no restoration rule in any source read)."""
        self._need(caller)
        if mid not in self._m: raise Refusal(mid, code="DATASET_MANIFEST_UNKNOWN")
        if not (type(ts) is int and ts >= 0 and _s(reason) and _s(authority)): raise Refusal(mid, code="DATASET_REVOCATION_MALFORMED")
        if self._ledger and ts < self._ledger[-1][1]: raise Refusal("ts", code="ML_LIFECYCLE_TS_REGRESSED")
        if any(e[0] == mid for e in self._ledger): return                                      # already revoked: idempotent, first reason stays
        self._ledger.append((mid, ts, reason, authority))
    def is_revoked(self, mid, as_of_ts=None):
        """True/False for a registered dataset; None for an UNKNOWN id (never False)."""
        if mid not in self._m: return None
        return any(e[0] == mid and (as_of_ts is None or e[1] <= as_of_ts) for e in self._ledger)
    # ---- reverse link (Addendum s6) ----
    def link_binding(self, caller, manifest_or_dataset_binding_id, mid):
        self._need(caller)
        if mid not in self._m or not _s(manifest_or_dataset_binding_id): raise Refusal(str(mid), code="DATASET_LINK_UNKNOWN_MANIFEST")
        old = self._links.get(manifest_or_dataset_binding_id)
        if old is not None and old != mid: raise Refusal(manifest_or_dataset_binding_id, code="DATASET_LINK_IMMUTABLE")
        self._links[manifest_or_dataset_binding_id] = mid
    def binding_index(self): return {b: [m] for b, m in sorted(self._links.items())}            # shape check_six_joins(binding_to_manifest=...) takes
    def manifest_index(self): return {i: e[1].manifest_hash for i, e in sorted(self._m.items())}   # shape check_six_joins(dataset_manifests=...) takes
    def bind_time_health(self, manifest_or_dataset_binding_id, outcome):
        """Through the binding to the bind-time Health Resolution: ONLY from an actual Gateway Binding outcome whose stored window identity names this binding id; a non-delivery or another binding yields None (nothing is inferred)."""
        from ..gateway.contracts import Binding
        if not isinstance(outcome, Binding) or manifest_or_dataset_binding_id not in self._links: return None
        return {"binding_id": manifest_or_dataset_binding_id, "dataset_manifest_id": self._links[manifest_or_dataset_binding_id], "health_resolution_ref": outcome.entry.bound_health_resolution_ref, "health_resolved_at": outcome.entry.bound_health_resolved_at, "request_id": outcome.request_id, "verified": False}

def revoked_ancestry_gate(candidate_id, derived_from: dict, datasets: DatasetRegistry, generations=None):
    """ML Core 31.C: the ancestry graph spans learned-artifact AND dataset/source lineage. `derived_from` maps a node id to its ancestor node ids (datasets and generations alike). A node is revoked if the dataset registry says so, else (for a generation id) the generation
    registry read class says FORENSIC_ONLY. Any revoked ancestor => BLOCKED (revoked-ancestry review gate); any unknown/unresolved ancestor => BLOCKED_UNKNOWN (fail closed); only a fully resolved clean graph => CLEAR. No weight ancestor in common is needed to be blocked."""
    def rev(n):
        r = datasets.is_revoked(n)
        if r is not None: return r
        if generations is not None and generations.manifest_of(n) is not None: return generations.read_class(n)["class"] == "FORENSIC_ONLY"
        return None
    rep = CC.revocation_report(candidate_id, derived_from, rev)
    return {"verdict": {"AFFECTED": "BLOCKED", "UNKNOWN": "BLOCKED_UNKNOWN", "CLEAN": "CLEAR"}[rep["status"]], "report": rep, "qualified": False}
