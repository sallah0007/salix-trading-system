"""R38: the ACTUAL COMPOSITION CALLER around `pipeline.run` (closeout 16.6). One bounded sequence over the REAL parts, each step through the owning module's public path, stopping at the first refusal (fail closed; the step log says how far it got):
  1 `pipeline.run(pkg)`                       -> accepted receipt (SIMULATION class here; qualified acceptance stays held on the duty evidence)
  2 Core `declare_dependency` per supplied upstream (EXACT dependency scope: the feature's own key -> its supplied upstream keys; nothing inferred)
  3 `reverification.reverify_accepted`         -> Core Recording Health evidence (COMPOSED_RECOMPUTATION, simulation-labelled)
  4 `stored_values.persist/record_stored_value_maintenance` (optional, when stored-value inputs are supplied)  -> L2 outcome in the SAME Core, same-class preflight
  5 `SimulationPublicationPath.commit` + `status_projection` + `feed(gateway)`  -> owning-HEAD-bound committed status/rows, Gateway publishes decoded rows
  6 `deliver(...)`: Core `gateway_health(... require_ancestry=True)` -> Gateway `resolve_window` (durable store) -> `fw.receiver.receive_verified`.
Health scope: `gateway_health` is asked for exactly (subject key, feature_version) with an explicit HealthBinding; an UNKNOWN required ancestry stays NOT acceptable (NonDelivery HEALTH_UNACCEPTABLE) until `declare_ancestry_complete` was called with a SUPPLIED source ref; this caller never declares ancestry on its own.
Nothing here mints a gate, a status mapping (the caller's `status_token` goes through the caller's `status_map`), a principal or a provider claim. Same ClaimService/Core/Gateway objects as the rest of the Tracker, no parallel copies."""
from dataclasses import dataclass, field
from typing import Optional
from ..errors import Refusal
from ..gateway import contracts as G
from ..fw import receiver as FWR
from . import reverification as RV
from . import stored_values as SV
from . import l2_scope as L2S
from .accepted_manifest import read_accepted_manifest
from ..storage.byte_primitives import canonical_bytes, domain_hash
@dataclass(frozen=True)
class L2Applicability:
    """R39: an EXPLICIT, caller-supplied governed applicability/verification-contract scope for the stored-value (L2) comparison of this feature (Registry 206/208-212). This module defines no scope, contract or vocabulary and guesses no NOT_APPLICABLE: no scope => HELD (L2 UNAVAILABLE in the Core); `required=True` with no stored inputs => UNAVAILABLE; `required=False` only records the supplied scope refs on the result (the Core then keeps its own calculation from the evidence it holds)."""
    scope_ref: str; contract_ref: str; required: bool
    def __post_init__(self):
        if not (isinstance(self.scope_ref, str) and self.scope_ref and isinstance(self.contract_ref, str) and self.contract_ref and type(self.required) is bool): raise Refusal("l2_applicability", code="COMPOSITION_L2_APPLICABILITY_INVALID")
@dataclass
class CompositionResult:
    status: str; steps: list = field(default_factory=list); outcome: object = None; feature_key: object = None; reverification: object = None; stored_values: Optional[dict] = None; published_rows: int = 0; projection: object = None; l2_scope: Optional[dict] = None
    def log(self, step, state, detail=""): self.steps.append((step, state, detail)); return self
class Composition:
    def __init__(self, *, pipeline, journals, store, core, path, gateway_factory, upstream=None, l2_scope_resolver=None):
        """path: SimulationPublicationPath over the SAME feature journal namespace; gateway_factory(projection) -> SimulatedGateway (the caller chooses watermark/final_store/health_source; this module does not)."""
        for n, o in (("pipeline", pipeline), ("journals", journals), ("store", store), ("core", core), ("path", path)):
            if o is None: raise Refusal(n, code="COMPOSITION_PART_MISSING")
        if not callable(gateway_factory): raise Refusal("gateway_factory", code="COMPOSITION_PART_MISSING")
        self._p, self._js, self._st, self._core, self._path, self._gf = pipeline, journals, store, core, path, gateway_factory; self._up = dict(upstream or {}); self.gateway = None; self._l2r = l2_scope_resolver
    def accept_and_publish(self, pkg, supplied, status_token, *, sequence, now, max_age, stored_inputs=None, l2_applicability=None, research_lineage=None, lineage_expect=None, lifecycle=None, lifecycle_transition=None, registry_gate=None):
        if l2_applicability is not None and not isinstance(l2_applicability, L2Applicability): raise Refusal("l2_applicability", code="COMPOSITION_L2_APPLICABILITY_INVALID")
        r = CompositionResult("STARTED")
        if research_lineage is not None:                                     # R40: the attempt checked is the one the PACKAGE actually records (never a caller-chosen known id); family/battery/input lineage must match a caller-supplied expectation (no universal family vocabulary is defined here)
            if not (isinstance(lineage_expect, tuple) and len(lineage_expect) == 3 and all(isinstance(x, str) and x for x in lineage_expect)): r.status = "HELD_ATTEMPT_LINEAGE_EXPECTATION_UNBOUND"; return r.log("attempt_lineage", "HELD", "lineage_expect=(family, battery, input_hash) must be supplied with research_lineage")
            att = research_lineage.attempt(getattr(pkg, "attempt_id", None))
            if att is None: r.status = "ATTEMPT_UNRESOLVED"; return r.log("attempt_lineage", "REFUSED", "the package's own attempt id is not held by the research ledger")
            if (att["family"], att["battery"], att["input_hash"]) != lineage_expect: r.status = "ATTEMPT_LINEAGE_MISMATCH"; return r.log("attempt_lineage", "REFUSED", "family/battery/input lineage differs from the expectation")
        elif lineage_expect is not None: r.status = "HELD_ATTEMPT_LINEAGE_INPUT_INCOMPLETE"; return r.log("attempt_lineage", "HELD", "lineage_expect without research_lineage")
        out = self._p.run(pkg); r.outcome = out
        if getattr(out, "accepted", None) is None or out.accepted.kind != "CANONICAL_ACCEPTED": r.status = "NOT_ACCEPTED"; return r.log("accept", "REFUSED", str(getattr(out, "stage", "")))
        fk = out.admission.feature_key; r.feature_key = fk; key = fk.key(); r.log("accept", "OK", out.accepted.kind)
        j = self._js.journal(fk.namespace())
        if research_lineage is not None:
            try: rec_att = dict(read_accepted_manifest(j, self._st, fk).recorded_lineage).get("attempt_id")
            except Refusal as e: rec_att = None
            if rec_att != pkg.attempt_id: r.status = "ATTEMPT_RECORD_MISMATCH"; return r.log("attempt_lineage", "REFUSED", "the accepted record's recorded attempt id differs from the package's")      # not published
        for up in self._up.get(key, ()): self._core.declare_dependency(key, up)
        r.log("dependencies", "OK", ",".join(self._up.get(key, ())))
        res, state = RV.reverify_accepted(self._core, journal=j, store=self._st, feature_key=fk, now=now, max_age=max_age); r.reverification = res; r.log("reverify_l1_l2_recomputation", res.status, state)
        l2_ok = [True]
        def absent(why):          # R39: a REQUIRED (or unbound=HELD) stored-value comparison that is absent is UNAVAILABLE - the prototype recomputation above is NOT a stored-value PASS and must not mask it
            SV._require_same_class(self._core, j, self._st); l1 = RV.split_levels(res)[0]
            digest = domain_hash("SALIX_STORED_VALUE_L2_ABSENT_V1", canonical_bytes({"overall": "UNAVAILABLE", "reason": why, "l1": l1, "l2": "UNAVAILABLE"}))
            self._core.record_verification(key, fk.feature_version, "REQUIRED", "UNAVAILABLE", l1, now, max_age, SV.VERIFIER_ID, digest)
            r.stored_values = {"overall": "UNAVAILABLE", "reason": why, "l1": l1, "l2": "UNAVAILABLE", "stored_values_compared": False, "result_digest": digest}; r.l2_scope = {"scope_ref": getattr(l2_applicability, "scope_ref", None), "contract_ref": getattr(l2_applicability, "contract_ref", None), "required": True if l2_applicability is not None else None}; r.log("stored_values_l2", "UNAVAILABLE", why); l2_ok[0] = False
        if stored_inputs is not None:
            try: SV.persist_stored_values(journal=j, store=self._st, feature_key=fk, **stored_inputs)
            except Refusal as e:
                if e.code == "STORED_VALUES_CLASS_MISMATCH": raise
                absent("STORED_VALUES_NOT_PERSISTABLE:" + e.code); stored_inputs = None                           # source unusable/unavailable at write time => UNAVAILABLE in the Core, never the prototype PASS
            if stored_inputs is not None: sv = SV.record_stored_value_maintenance(self._core, journal=j, store=self._st, feature_key=fk, now=now, max_age=max_age, **stored_inputs); r.stored_values = sv; r.log("stored_values_l2", sv["overall"], sv["reason"]); l2_ok[0] = sv["l2"] == "PASS"
        elif l2_applicability is not None and not l2_applicability.required:   # R40: a flag is not a governed definition: the supplied scope must RESOLVE (exact feature/version/contract, admitted, current, unrevoked) or the L2 is UNAVAILABLE
            sstate, swhy = L2S.judge_l2_scope(self._l2r, l2_applicability.scope_ref, l2_applicability.contract_ref, key, fk.feature_version)
            if sstate == "NOT_REQUIRED_ADMITTED": r.l2_scope = {"scope_ref": l2_applicability.scope_ref, "contract_ref": l2_applicability.contract_ref, "required": False, "resolved": True}; r.log("stored_values_l2", "NOT_REQUIRED_PER_RESOLVED_ADMITTED_SCOPE", l2_applicability.scope_ref)
            else: absent(swhy if sstate == "UNAVAILABLE" else "STORED_VALUES_REQUIRED_BUT_NOT_SUPPLIED")
        else: absent("STORED_VALUES_REQUIRED_BUT_NOT_SUPPLIED" if l2_applicability is not None else "L2_APPLICABILITY_UNBOUND_HELD")
        if registry_gate is not None:                                        # R40: the integrated Registry-377 checker; anything but CHECKS_PASS_FACTS_ONLY holds publication (acceptance is not undone; nothing is guessed)
            rep = registry_gate(key, fk); r.log("registry_integrity", rep.overall, ",".join("%s:%s" % (f.check, f.state) for f in rep.findings))
            if rep.overall != "CHECKS_PASS_FACTS_ONLY": r.status = "HELD_REGISTRY_INTEGRITY_" + rep.overall; return r
        self._path.commit(fk, supplied, status_token, sequence=sequence); r.projection = self._path.status_projection(); self.gateway = self._gf(r.projection); r.published_rows = self._path.feed(self.gateway); r.log("committed_status_and_rows", "OK", "rows=%d" % r.published_rows)
        if lifecycle_transition is not None or lifecycle is not None:        # R39: the ACTUAL LifecycleFramework.apply call, only when BOTH a framework and an explicit transition are supplied; an unbound policy is HELD, never a guessed state
            if lifecycle is None or lifecycle_transition is None: r.log("lifecycle", "HELD", "COMPOSITION_LIFECYCLE_INPUT_INCOMPLETE")
            else:
                try: rec = lifecycle.apply(key, *lifecycle_transition); r.log("lifecycle", "APPLIED" if rec is not None else "IDEMPOTENT_NOOP", lifecycle_transition[0])
                except Refusal as e: r.log("lifecycle", "HELD" if e.code in ("LIFECYCLE_POLICY_HELD", "LIFECYCLE_EVIDENCE_CHECK_HELD") else "REFUSED", e.code)
        r.status = "PUBLISHED_SIMULATION" if l2_ok[0] else "PUBLISHED_SIMULATION_L2_NOT_PASS"; return r
    def deliver(self, request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, result: CompositionResult, *, binding, now, ref, resolved_at, tables):
        """Gateway resolution for ONE FW window under the composed Core Health. Returns the Binding after the FW verified receive; a non-delivery raises `NON_DELIVERY`."""
        if self.gateway is None or result.feature_key is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")
        fk = result.feature_key; health = self._core.gateway_health(fk.key(), fk.feature_version, now, ref, resolved_at, binding=binding, require_ancestry=True)
        d = self.gateway.resolve_window(request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, health)
        return FWR.receive_verified(d, entry, instrument_id, timeframe_id, tables, self.gateway)
