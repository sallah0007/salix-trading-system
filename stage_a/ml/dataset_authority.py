"""Generic ML dataset REQUEST / UNION-LINEAGE / CLAIM caller over ONE `DatasetRegistry` (ML Integration Binding Addendum V1 s3-s7; Contract V0.38 final resolution; ML Core V1.16 dataset provenance manifests).
What it adds to the registry: (1) `request_binding` links a dataset manifest to a consumer binding ONLY for an ML outcome the SAME Gateway and the SAME final store actually issued - the binding id comes from the ISSUED identity (never a caller label) and nothing is written when the issuance check fails;
(2) `declare_union` records an append-only, idempotent UNION of member datasets and contributing generations (cycles, self-membership, unknown datasets/generations refuse: s3 renaming/caching/repackaging does not erase ancestry, so an undeclared member can only make the gate UNKNOWN, never clean);
(3) `gate` runs the revoked-ancestry gate over the declared union (unknown/unresolved = BLOCKED_UNKNOWN); (4) `record_claim` records an authority-bearing consumption claim with the dataset's OWN supplied feed era (s5/s7, exact equality) and the consulted family ledger ref.
Write authority is the registry's SUPPLIED grant slot (none => HELD); nothing is appointed. NOT built / NOT invented: the dataset->generation key (no source defines how a generation's training_data_identity equals a dataset hash: reported PRESENT_UNVERIFIED, never correlated by guess), the family-ledger encoding, any forward CONSUMER_BINDING field on the manifest (NOT_YET_NATIVE)."""
from ..errors import Refusal
from . import dataset_manifest as DM, consumption_claim as CC
def _s(x): return isinstance(x, str) and bool(x)
class DatasetAuthority:
    def __init__(self, datasets: DM.DatasetRegistry, generations=None, claims=None):
        self._d = datasets; self._g = generations; self._claims = claims if claims is not None else CC.ClaimLedger(); self._union = {}
    def request_binding(self, caller, manifest, outcome, *, gateway, final_store, request_id):
        self._d._need(caller)
        from ..gateway.contracts import Binding
        if not isinstance(outcome, Binding): return None                                       # a non-Binding outcome links nothing (no inference)
        ident = final_store.identity_of("ML", request_id) if _s(request_id) else None
        if ident is None or ident.consumer_id != "ML" or not _s(ident.manifest_or_dataset_binding_id): raise Refusal(str(request_id), code="DATASET_REQUEST_NOT_ISSUED_FOR_ML_BINDING")
        if final_store.outcome_for(ident) != outcome: raise Refusal(request_id, code="DATASET_BINDING_OUTCOME_NOT_THE_STORED_FINAL_OUTCOME")
        if gateway.outcome(outcome.request_id, "ML") is not outcome: raise Refusal(outcome.request_id, code="DATASET_BINDING_OUTCOME_NOT_GATEWAY_ISSUED")
        bid = ident.manifest_or_dataset_binding_id
        self._d.register(caller, manifest)                                                      # immutable; identical retry idempotent; different bytes refuse BEFORE the link is written
        self._d.link_binding(caller, bid, manifest.dataset_manifest_id)
        return self._d.bind_time_health(bid, outcome, gateway=gateway, final_store=final_store, request_id=request_id)
    def declare_union(self, caller, dataset_id, members=(), generation_ids=()):
        self._d._need(caller)
        if not _s(dataset_id) or self._d.manifest(dataset_id) is None: raise Refusal(str(dataset_id), code="UNION_DATASET_UNKNOWN")
        if not (isinstance(members, tuple) and isinstance(generation_ids, tuple) and all(_s(x) for x in members + generation_ids) and len(set(members)) == len(members) and len(set(generation_ids)) == len(generation_ids)): raise Refusal(dataset_id, code="UNION_MALFORMED")
        if dataset_id in members: raise Refusal(dataset_id, code="UNION_SELF_MEMBERSHIP")
        for m in members:
            if self._d.manifest(m) is None: raise Refusal(m, code="UNION_MEMBER_DATASET_UNKNOWN")
        for g in generation_ids:
            if self._g is None or self._g.manifest_of(g) is None: raise Refusal(g, code="UNION_GENERATION_UNKNOWN")
        entry = (tuple(sorted(members)), tuple(sorted(generation_ids)))
        old = self._union.get(dataset_id)
        if old is not None:
            if old != entry: raise Refusal(dataset_id, code="UNION_IMMUTABLE")                 # a later different union is a successor dataset, never a rewrite
            return old
        trial = dict(self._union); trial[dataset_id] = entry
        def reach(n, seen):
            for p in trial.get(n, ((), ()))[0]:
                if p == dataset_id or p in seen: 
                    if p == dataset_id: return True
                    continue
                seen.add(p)
                if reach(p, seen): return True
            return False
        if reach(dataset_id, set()): raise Refusal(dataset_id, code="UNION_CYCLE")
        self._union[dataset_id] = entry; return entry
    def union_of(self, dataset_id): return self._union.get(dataset_id)
    def derived_from(self, generation_lineage=None) -> dict:
        """{node: [contributors]} from the DECLARED unions only (plus any SUPPLIED generation lineage). A registered dataset with no declaration is ABSENT here, so the gate reads it as unresolved; an explicit leaf is `declare_union(id, (), ())` (the caller's assertion that it has no ancestors)."""
        d = {k: list(v[0]) + list(v[1]) for k, v in self._union.items()}
        for g, c in (generation_lineage or {}).items(): d[g] = list(c)
        return d
    def gate(self, dataset_id, generation_lineage=None):
        """Revoked-ancestry gate over the DECLARED union. No declaration for the root => UNKNOWN (an absent declaration is not a clean lineage); a member dataset/generation with no declaration => UNKNOWN; any revoked ancestor => BLOCKED."""
        if dataset_id not in self._union: return {"verdict": "BLOCKED_UNKNOWN", "report": {"status": "UNKNOWN", "unresolved": (dataset_id,)}, "qualified": False}
        return DM.revoked_ancestry_gate(dataset_id, self.derived_from(generation_lineage), self._d, self._g)
    def record_claim(self, claim: CC.ConsumptionClaim):
        m = self._d.manifest(claim.manifest_id) if isinstance(claim, CC.ConsumptionClaim) else None
        if m is None: raise Refusal("claim", code="CLAIM_DATASET_UNKNOWN")
        if self._d.is_revoked(claim.manifest_id, claim.claim_ts): raise Refusal(claim.claim_id, code="CLAIM_ON_REVOKED_DATASET")
        if self._d._links.get(claim.consumer_binding_id) != claim.manifest_id: raise Refusal(claim.claim_id, code="CLAIM_BINDING_NOT_LINKED_TO_THIS_DATASET")
        return self._claims.record(claim, manifest_feed_era_id=m.feed_era_id)
    def correlate(self, binding_id) -> dict:
        mid = self._d._links.get(binding_id)
        return {"binding_id": binding_id, "dataset_manifest_id": mid, "link": "PRESENT" if mid else "MISSING", "union_declared": mid in self._union if mid else False,
                "dataset_to_generation_key": "PRESENT_UNVERIFIED_NO_SOURCE_DEFINED_KEY", "qualified": False}
