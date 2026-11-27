"""Generic caller-correlated ML generation WRITER / FINALIZER facade over ONE `GenerationRegistry` (ML Integration Binding Addendum V1 s6: the certified generation manifest is distinct from merely producing model bytes; MLCore A/28.A lifecycle).
The principal GRANT table is a SUPPLIED slot: `grants = {role: {caller ids}}` with a non-empty `grant_source_ref`. With no grants every write/finalize is HELD (`ML_PRINCIPAL_GRANTS_UNBOUND_HELD`): this module appoints nobody, invents no role beyond the two the source names
(manifest writer, finalizer) and never reports a qualified result. It records WHO wrote/finalized (caller identity -> manifest id/hash) and `correlate()` cross-checks that record against the registry's own append-only ledger, so a ledger entry written around the facade
or by a caller outside the supplied grant is reported, not trusted. Limits: the registry itself is an ML-owned in-process object whose public methods can be called directly (no process boundary here); the supplied grants are unadmitted; creator != certifier is NOT
enforced (no source rule found for ML here), `writer_equals_finalizer` is reported only."""
from ..errors import Refusal
ROLES = ("MANIFEST_WRITER", "FINALIZER")
CERTIFIED = "COMPLETE_CERTIFIED"
def _s(x): return isinstance(x, str) and bool(x)

class GenerationAuthority:
    def __init__(self, registry, grants=None, grant_source_ref=None):
        self._r = registry; self._audit = []; self._grants = None
        if grants is not None:
            if not (isinstance(grants, dict) and set(grants) <= set(ROLES) and all(isinstance(v, (set, frozenset)) and v and all(_s(x) for x in v) for v in grants.values()) and _s(grant_source_ref)): raise Refusal("grants", code="ML_PRINCIPAL_GRANTS_INVALID")
            self._grants = {k: frozenset(v) for k, v in grants.items()}
        self.grant_source_ref = grant_source_ref if self._grants else None
    def _need(self, caller, role):
        if self._grants is None or role not in self._grants: raise Refusal(role, code="ML_PRINCIPAL_GRANTS_UNBOUND_HELD")
        if not _s(caller) or caller not in self._grants[role]: raise Refusal(role, code="ML_CALLER_NOT_GRANTED")
    def write_manifest(self, caller, manifest):
        self._need(caller, "MANIFEST_WRITER"); self._r.register_manifest(manifest)
        self._audit.append(("WRITE", caller, manifest.manifest_id, manifest.manifest_hash))
    def finalize(self, caller, manifest_id, ts, reason):
        self._need(caller, "FINALIZER"); m = self._r.manifest_of(manifest_id)
        if m is None or not any(a[0] == "WRITE" and a[2] == manifest_id for a in self._audit): raise Refusal(manifest_id, code="ML_FINALIZE_WITHOUT_RECORDED_WRITE")      # only a manifest written through this facade can be finalized through it
        self._r.append_lifecycle(manifest_id, CERTIFIED, ts, reason, caller)
        self._audit.append(("FINALIZE", caller, manifest_id, m.manifest_hash))
    def correlate(self, manifest_id) -> dict:
        """Cross-check the facade's record against the registry ledger. status VERIFIED_AGAINST_REGISTRY only if: one recorded writer, the registry manifest hash equals the recorded one, and EVERY CERTIFIED ledger entry for the manifest has an authority that was a recorded finalize by a caller in the supplied grant."""
        m = self._r.manifest_of(manifest_id); w = [a for a in self._audit if a[0] == "WRITE" and a[2] == manifest_id]; f = [a for a in self._audit if a[0] == "FINALIZE" and a[2] == manifest_id]
        led = [e for e in self._r.ledger() if e.manifest_id == manifest_id and e.state == CERTIFIED]
        out = {"manifest_id": manifest_id, "writer": w[0][1] if w else None, "finalizers": tuple(sorted({a[1] for a in f})), "qualified": False, "grant_source_ref": self.grant_source_ref}
        bad = None
        if self._grants is None: bad = "GRANTS_UNBOUND"
        elif m is None or len(w) != 1 or w[0][3] != m.manifest_hash: bad = "NO_SINGLE_RECORDED_WRITE_MATCHING_REGISTRY_HASH"
        elif not led: bad = "NO_CERTIFIED_LEDGER_ENTRY"
        elif any(e.authority not in {a[1] for a in f} or e.authority not in self._grants.get("FINALIZER", ()) for e in led): bad = "LEDGER_ENTRY_NOT_FROM_A_RECORDED_GRANTED_FINALIZE"
        out["status"] = "VERIFIED_AGAINST_REGISTRY" if bad is None else "MISMATCH:" + bad
        out["writer_equals_finalizer"] = bool(w and f and w[0][1] in out["finalizers"])
        return out
