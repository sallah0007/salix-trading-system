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
@dataclass
class CompositionResult:
    status: str; steps: list = field(default_factory=list); outcome: object = None; feature_key: object = None; reverification: object = None; stored_values: Optional[dict] = None; published_rows: int = 0; projection: object = None
    def log(self, step, state, detail=""): self.steps.append((step, state, detail)); return self
class Composition:
    def __init__(self, *, pipeline, journals, store, core, path, gateway_factory, upstream=None):
        """path: SimulationPublicationPath over the SAME feature journal namespace; gateway_factory(projection) -> SimulatedGateway (the caller chooses watermark/final_store/health_source; this module does not)."""
        for n, o in (("pipeline", pipeline), ("journals", journals), ("store", store), ("core", core), ("path", path)):
            if o is None: raise Refusal(n, code="COMPOSITION_PART_MISSING")
        if not callable(gateway_factory): raise Refusal("gateway_factory", code="COMPOSITION_PART_MISSING")
        self._p, self._js, self._st, self._core, self._path, self._gf = pipeline, journals, store, core, path, gateway_factory; self._up = dict(upstream or {}); self.gateway = None
    def accept_and_publish(self, pkg, supplied, status_token, *, sequence, now, max_age, stored_inputs=None):
        r = CompositionResult("STARTED"); out = self._p.run(pkg); r.outcome = out
        if getattr(out, "accepted", None) is None or out.accepted.kind != "CANONICAL_ACCEPTED": r.status = "NOT_ACCEPTED"; return r.log("accept", "REFUSED", str(getattr(out, "stage", "")))
        fk = out.admission.feature_key; r.feature_key = fk; key = fk.key(); r.log("accept", "OK", out.accepted.kind)
        j = self._js.journal(fk.namespace())
        for up in self._up.get(key, ()): self._core.declare_dependency(key, up)
        r.log("dependencies", "OK", ",".join(self._up.get(key, ())))
        res, state = RV.reverify_accepted(self._core, journal=j, store=self._st, feature_key=fk, now=now, max_age=max_age); r.reverification = res; r.log("reverify_l1_l2_recomputation", res.status, state)
        if stored_inputs is not None:
            SV.persist_stored_values(journal=j, store=self._st, feature_key=fk, **stored_inputs); sv = SV.record_stored_value_maintenance(self._core, journal=j, store=self._st, feature_key=fk, now=now, max_age=max_age, **stored_inputs); r.stored_values = sv; r.log("stored_values_l2", sv["overall"], sv["reason"])
        self._path.commit(fk, supplied, status_token, sequence=sequence); r.projection = self._path.status_projection(); self.gateway = self._gf(r.projection); r.published_rows = self._path.feed(self.gateway); r.log("committed_status_and_rows", "OK", "rows=%d" % r.published_rows)
        r.status = "PUBLISHED_SIMULATION"; return r
    def deliver(self, request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, result: CompositionResult, *, binding, now, ref, resolved_at, tables):
        """Gateway resolution for ONE FW window under the composed Core Health. Returns the Binding after the FW verified receive; a non-delivery raises `NON_DELIVERY`."""
        if self.gateway is None or result.feature_key is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")
        fk = result.feature_key; health = self._core.gateway_health(fk.key(), fk.feature_version, now, ref, resolved_at, binding=binding, require_ancestry=True)
        d = self.gateway.resolve_window(request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, health)
        return FWR.receive_verified(d, entry, instrument_id, timeframe_id, tables, self.gateway)
