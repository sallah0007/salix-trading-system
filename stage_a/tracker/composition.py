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
from ..ml import receiver as MLR
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
    status: str; steps: list = field(default_factory=list); outcome: object = None; feature_key: object = None; reverification: object = None; stored_values: Optional[dict] = None; published_rows: int = 0; projection: object = None; l2_scope: Optional[dict] = None; status_event: Optional[dict] = None; audit: Optional[dict] = None
    def log(self, step, state, detail=""): self.steps.append((step, state, detail)); return self
class Composition:
    def __init__(self, *, pipeline, journals, store, core, path, gateway_factory, upstream=None, l2_scope_resolver=None):
        """path: SimulationPublicationPath over the SAME feature journal namespace; gateway_factory(projection) -> SimulatedGateway (the caller chooses watermark/final_store/health_source; this module does not)."""
        for n, o in (("pipeline", pipeline), ("journals", journals), ("store", store), ("core", core), ("path", path)):
            if o is None: raise Refusal(n, code="COMPOSITION_PART_MISSING")
        if not callable(gateway_factory): raise Refusal("gateway_factory", code="COMPOSITION_PART_MISSING")
        self._p, self._js, self._st, self._core, self._path, self._gf = pipeline, journals, store, core, path, gateway_factory; self._up = dict(upstream or {}); self.gateway = None; self._l2r = l2_scope_resolver; self._sv = {}; self._pub = {}; self._published = {}
    @staticmethod
    def _report_scope_defect(rep, key, pkg, now, max_age):
        from .registry_integrity import IntegrityReport
        if not isinstance(rep, IntegrityReport): return "MALFORMED"
        if rep.subject != key: return "SUBJECT_DIFFERS_FROM_ACCEPTED_FEATURE"
        if rep.creation_request_id != getattr(pkg, "request_id", None): return "CREATION_REQUEST_DIFFERS_FROM_PACKAGE"
        if type(rep.checked_at) is not int or type(now) is not int or type(max_age) is not int or rep.checked_at > now or now - rep.checked_at > max_age: return "NOT_CURRENT_OR_UNTIMED"
        return None
    def accept_and_publish(self, pkg, supplied, status_token, *, sequence, now, max_age, stored_inputs=None, l2_applicability=None, research_lineage=None, lineage_expect=None, lifecycle=None, lifecycle_transition=None, registry_gate=None, accept_fn=None, status_emitter=None, emit=None):
        if l2_applicability is not None and not isinstance(l2_applicability, L2Applicability): raise Refusal("l2_applicability", code="COMPOSITION_L2_APPLICABILITY_INVALID")
        r = CompositionResult("STARTED")
        if research_lineage is not None:                                     # R40: the attempt checked is the one the PACKAGE actually records (never a caller-chosen known id); family/battery/input lineage must match a caller-supplied expectation (no universal family vocabulary is defined here)
            if not (isinstance(lineage_expect, tuple) and len(lineage_expect) == 3 and all(isinstance(x, str) and x for x in lineage_expect)): r.status = "HELD_ATTEMPT_LINEAGE_EXPECTATION_UNBOUND"; return r.log("attempt_lineage", "HELD", "lineage_expect=(family, battery, input_hash) must be supplied with research_lineage")
            att = research_lineage.attempt(getattr(pkg, "attempt_id", None))
            if att is None: r.status = "ATTEMPT_UNRESOLVED"; return r.log("attempt_lineage", "REFUSED", "the package's own attempt id is not held by the research ledger")
            if (att["family"], att["battery"], att["input_hash"]) != lineage_expect: r.status = "ATTEMPT_LINEAGE_MISMATCH"; return r.log("attempt_lineage", "REFUSED", "family/battery/input lineage differs from the expectation")
        elif lineage_expect is not None: r.status = "HELD_ATTEMPT_LINEAGE_INPUT_INCOMPLETE"; return r.log("attempt_lineage", "HELD", "lineage_expect without research_lineage")
        out = self._p.run(pkg) if accept_fn is None else accept_fn(pkg); r.outcome = out
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
            rep = registry_gate(key, fk)
            why = self._report_scope_defect(rep, key, pkg, now, max_age)          # R42: a report for another subject/version/request, or one with no usable timestamp, is never accepted as THIS feature's integrity
            if why is not None: r.status = "HELD_REGISTRY_REPORT_SCOPE_" + why; return r.log("registry_integrity", "SCOPE_REFUSED", why)
            r.log("registry_integrity", rep.overall, ",".join("%s:%s" % (f.check, f.state) for f in rep.findings))
            if rep.overall != "CHECKS_PASS_FACTS_ONLY": r.status = "HELD_REGISTRY_INTEGRITY_" + rep.overall; return r
        if status_emitter is not None:                                       # R50: the OWNING status emitter replaces the bare path.commit: committed lifecycle record -> A1 status event + s25 audit evidence -> ONE SIM_STATUS_FACT append. The mapping/boundary evidence/audit fields are SUPPLIED; unbound => HELD and nothing is published
            if getattr(status_emitter, "_path", None) is not self._path or status_token is not None or not isinstance(emit, dict): r.status = "HELD_STATUS_EMIT_INPUT"; return r.log("status_emit", "HELD", "emitter must wrap THIS path, status_token must be None (the mapping is the emitter's), emit={boundary_evidence, context_known[, audit_fields]} must be supplied")
            try: em = status_emitter.emit(fk, supplied, sequence=sequence, **emit)
            except Refusal as e: r.status = "HELD_STATUS_EMIT_" + e.code; return r.log("status_emit", "HELD" if e.code.endswith("_HELD") or e.code.startswith("STATUS_EVENT_FIELD") else "REFUSED", e.code)
            r.status_event, r.audit = em["status_event"], em["audit"]; r.log("status_emit", "REPLAY" if em["replay"] else "EMITTED", "audit_complete=%s" % em["audit"]["complete"])
        else: self._path.commit(fk, supplied, status_token, sequence=sequence)
        r.projection = self._path.status_projection(); self.gateway = self._gf(r.projection); r.published_rows = self._path.feed(self.gateway); r.log("committed_status_and_rows", "OK", "rows=%d" % r.published_rows)
        if lifecycle_transition is not None or lifecycle is not None:        # R39: the ACTUAL LifecycleFramework.apply call, only when BOTH a framework and an explicit transition are supplied; an unbound policy is HELD, never a guessed state
            if lifecycle is None or lifecycle_transition is None: r.log("lifecycle", "HELD", "COMPOSITION_LIFECYCLE_INPUT_INCOMPLETE")
            else:
                try: rec = lifecycle.apply(key, *lifecycle_transition); r.log("lifecycle", "APPLIED" if rec is not None else "IDEMPOTENT_NOOP", lifecycle_transition[0])
                except Refusal as e: r.log("lifecycle", "HELD" if e.code in ("LIFECYCLE_POLICY_HELD", "LIFECYCLE_EVIDENCE_CHECK_HELD") else "REFUSED", e.code)
        r.status = "PUBLISHED_SIMULATION" if l2_ok[0] else "PUBLISHED_SIMULATION_L2_NOT_PASS"
        self._published[key] = r                                                                                                      # R54: the result THIS Composition published for this subject (delivery selects health only through it)
        if stored_inputs is not None and callable(stored_inputs.get("fetch")) and callable(stored_inputs.get("series_hash")): self._pub[key] = (r, r.status, stored_inputs["fetch"], stored_inputs["series_hash"])           # R53: the OWNING registration basis: THIS Composition accepted, persisted and published this feature with exactly these stored-value inputs
        return r
    def register_stored_maintenance(self, result, stored_inputs=None):
        """R53 owning connection: `stored_values.run_stored_value_pass` had no caller in the assembly. A `StoredBinding` is registered ONLY for a result THIS Composition itself accepted, persisted stored values for and published (`accept_and_publish` records the basis privately: the result object, its status at that moment and the exact fetch/series_hash callables used). The caller-mutable `result.status` label and a result from another Composition are NOT evidence; the stored basis is. The fetch/series_hash used by the pass are the acceptance inputs (a caller may repeat them, any different callable refuses). Same-class preflight; idempotent.
        Limit (honest): identity of the callables is object identity, not proof the fetched bytes are unchanged since acceptance (the pass re-fetches and re-hashes every stored segment for that)."""
        fk = getattr(result, "feature_key", None); basis = self._pub.get(fk.key()) if fk is not None else None
        if basis is None or basis[0] is not result: raise Refusal(getattr(result, "status", None), code="COMPOSITION_MAINTENANCE_NOT_PUBLISHED")
        _r, _st, fetch, sh = basis
        if stored_inputs is not None and not (isinstance(stored_inputs, dict) and stored_inputs.get("fetch") is fetch and stored_inputs.get("series_hash") is sh): raise Refusal(fk.key(), code="COMPOSITION_MAINTENANCE_INPUT_NOT_THE_ACCEPTANCE_INPUT")
        j = self._js.journal(fk.namespace()); SV._require_same_class(self._core, j, self._st)
        b = SV.StoredBinding(j, self._st, fk, fetch, sh); self._sv[fk.key()] = b; return b
    def register_row_maintenance(self, result, profile):
        """R53 generic per-ROW L2 over THIS feature's stored rows (`row_maintenance`): a `RowBinding` is registered only for a result this Composition published; it reuses the committed row store, the ROW_ACCEPTED journals and a SUPPLIED independent-verifier profile (absent/incomplete => the maintenance result is UNAVAILABLE/NOT_HEALTHY, never PASS). When the feature also has a feature-version StoredBinding the two are combined WORST-OF in one Core record. No cadence/calendar; the profile instance is not appointed here."""
        from . import row_maintenance as RM
        from .materialization import row_store as RS
        fk = getattr(result, "feature_key", None)
        if fk is None or self._published.get(fk.key()) is not result: raise Refusal(getattr(fk, "key", lambda: None)(), code="COMPOSITION_RESULT_NOT_THIS_PUBLICATION")
        tables = profile.get("tables") if isinstance(profile, dict) else None
        j = self._js.journal(fk.namespace()); SV._require_same_class(self._core, j, self._st)
        rows = RS.PendingRowStore(self._st, tables) if tables is not None else None
        prev = self._sv.get(fk.key()); seg = prev.segments if isinstance(prev, RM.RowBinding) else prev
        b = RM.RowBinding(self._js, rows, self._st, fk, profile if (rows is not None and RM._profile_ok(profile)) else None, seg); self._sv[fk.key()] = b; return b
    def run_maintenance(self, events=(), *, now, max_age, max_items, subjects=None):
        """One bounded all-segment L2 pass over the registered subjects through the existing `run_stored_value_pass` (Core due-ness UNION supplied (subject, trigger) events; no daemon/cadence here). Results are recorded in the SAME Core the Gateway reads health from, so a failing/unavailable segment makes later delivery NON_DELIVERY."""
        return SV.run_stored_value_pass(self._core, dict(self._sv), sorted(self._sv) if subjects is None else list(subjects), events, now=now, max_age=max_age, max_items=max_items)
    def publish_accepted_row(self, result, row_publication, row_hash, token, **supplied):
        """R53 per-ROW publication through THIS Composition: `result` must be the very object this Composition published/recovered for the subject, `row_publication` must be bound to THIS path, and the row must already be ACCEPTED (RowPublication refuses otherwise). One SIM_STATUS_FACT is
        derived from the accepted row (never from the caller); the projection must remain authoritative, then the Gateway is rebuilt from the committed side journal (its final store is durable) and the SAME result object is refreshed so delivery keeps its identity guard. SIMULATION; no per-row A1 event; clears nothing."""
        fk = getattr(result, "feature_key", None)
        if fk is None or self._published.get(fk.key()) is not result: raise Refusal(getattr(fk, "key", lambda: None)(), code="COMPOSITION_RESULT_NOT_THIS_PUBLICATION")
        if getattr(row_publication, "_path", None) is not self._path: raise Refusal("row_publication", code="COMPOSITION_ROW_PUBLICATION_FOREIGN_PATH")
        rec = row_publication.publish(fk, row_hash, token, **supplied)
        proj = self._path.status_projection()
        if not proj.authoritative: raise Refusal(fk.key(), code="COMPOSITION_ROW_PROJECTION_NOT_AUTHORITATIVE")
        gw = self._gf(proj); fs = getattr(gw, "final_store", None)
        if fs is not None and hasattr(fs, "recover"): fs.recover()
        self.gateway = gw; result.projection = proj; result.published_rows = self._path.feed(gw); result.log("row_published", "OK", "row=%s rows=%d" % (row_hash[:12], result.published_rows)); return rec

    def recover_publication(self, feature_key, *, stored_inputs=None):
        """R54 cold recovery of THIS Composition's owning connection after a restart: nothing is taken from memory. The feature must (a) still have its committed CANONICAL_ACCEPTED manifest in the owning feature journal (`read_accepted_manifest`), and (b) hold at least one committed status record in the (rebuilt) publication path whose source guard still matches the owning HEAD; a NEW Gateway is built from the path's committed projection, its durable final store is recovered (stored consumer-local outcomes and identities are authoritative, never re-evaluated), and the committed rows are fed. The result is labelled RECOVERED_PUBLISHED_SIMULATION; it does NOT restore the L2/stored-value basis unless `stored_inputs` is supplied AND the all-segment verification finds stored segments (a basis is never recreated from a caller label). Health/ancestry live in the Core journal (a new Core over the same journal)."""
        key = feature_key.key(); j = self._js.journal(feature_key.namespace())
        try: read_accepted_manifest(j, self._st, feature_key)
        except Refusal as e: raise Refusal(key, code="COMPOSITION_RECOVERY_NO_ACCEPTED_RECORD:" + e.code)
        if not any(b.get("feature_key") == key for b in self._path.records()): raise Refusal(key, code="COMPOSITION_RECOVERY_NO_COMMITTED_STATUS")
        if not self._path.source_current(): raise Refusal(key, code="COMPOSITION_RECOVERY_SOURCE_HEAD_ADVANCED")
        r = CompositionResult("RECOVERED_PUBLISHED_SIMULATION", feature_key=feature_key); proj = self._path.status_projection(); gw = self._gf(proj); fs = getattr(gw, "final_store", None)
        if fs is not None and hasattr(fs, "recover"): fs.recover()
        self.gateway = gw; r.projection = proj; r.published_rows = self._path.feed(gw); r.log("recovered_committed_status_and_rows", "OK", "rows=%d" % r.published_rows); self._published[key] = r
        if stored_inputs is not None and callable(stored_inputs.get("fetch")) and callable(stored_inputs.get("series_hash")):
            v = SV.verify_all_stored_segments(journal=j, store=self._st, feature_key=feature_key, fetch=stored_inputs["fetch"], series_hash=stored_inputs["series_hash"])
            if v["segments"]: self._pub[key] = (r, r.status, stored_inputs["fetch"], stored_inputs["series_hash"]); r.log("stored_basis", "RESTORED_FROM_STORED_SEGMENTS", v["overall"])
            else: r.log("stored_basis", "NOT_RESTORED", v["reason"])
        return r
    def _owning_subject(self, result, entry, binding):
        """R54: delivery selects Core health from the RESULT's feature key, and a result is a caller-held mutable object. The result must be the very object this Composition published for that subject, and the requested entry and health binding must name that subject's feature id/version; otherwise refuse (the Gateway's HEALTH_BINDING_MISMATCH is a second, independent check, not the only one)."""
        fk = result.feature_key
        if self._published.get(fk.key()) is not result: raise Refusal(fk.key(), code="COMPOSITION_RESULT_NOT_THIS_PUBLICATION")
        if getattr(binding, "feature_id", None) != getattr(entry, "feature_id", object()) or getattr(binding, "feature_version", None) != fk.feature_version or getattr(entry, "feature_version", None) != fk.feature_version: raise Refusal(fk.key(), code="COMPOSITION_ENTRY_BINDING_SUBJECT_MISMATCH")
        return fk
    def outcome_desk(self):
        """R54: the generic H3 REQUEST->RETURN desk (`fw/outcome_desk.OutcomeSeriesDesk`) bound to THIS composition's own Gateway, so an H1 record correlates only with identities this Gateway's durable final store issued (a rebuilt Composition re-hydrates them). Carries identities only; FW payload fields, H3 authorization inputs and the CBID source stay caller-supplied/held; every return is `delivered=False`."""
        if self.gateway is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")
        d = getattr(self, "_desk", None)
        if d is None or getattr(d, "_g", None) is not self.gateway:
            from ..fw.outcome_desk import OutcomeSeriesDesk
            d = self._desk = OutcomeSeriesDesk(self.gateway)
        return d
    def fw_association(self):
        """R54: the generic Tracker-owned FW request/return ASSOCIATION ledger (`fw/association.FwAssociation`) over THIS composition's own Gateway final store (identities only; return payload fields stay UNBOUND/held; returns are in-memory per Composition, so a rebuilt Composition starts with none - a durable return ledger is an ownership decision, not built)."""
        if self.gateway is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")
        a = getattr(self, "_fwa", None)
        if a is None or getattr(a, "_store", None) is not self.gateway.final_store:
            from ..fw.association import FwAssociation
            a = self._fwa = FwAssociation(self.gateway.final_store)
        return a
    def deliver(self, request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, result: CompositionResult, *, binding, now, ref, resolved_at, tables, health=None, consumer_manifest_id=None):
        """Gateway resolution for ONE FW window under the composed Core Health. Returns the Binding after the FW verified receive; a non-delivery raises `NON_DELIVERY`. Optional `health` (health.impact_supplier) adds the consumer-closure carried-upstream check BEFORE resolution; omitted => only the Core ancestry check applies (named in closeout 27)."""
        if self.gateway is None or result.feature_key is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")
        if health is not None:                                               # R49: the SAME supplier/relations as the ML path; requiredness derives from `entry`; the FW consumer manifest id is caller-named but must exist in the supplier's governed registry with kind FW
            use, _imp = health.decide(consumer_manifest_id, "FW", entry)
            if use == "BLOCK_PROVEN_DEPENDENCY" or use.startswith("REFUSE_"): raise Refusal(use, code="HEALTH_IMPACT_" + use)
        fk = self._owning_subject(result, entry, binding); health = self._core.gateway_health(fk.key(), fk.feature_version, now, ref, resolved_at, binding=binding, require_ancestry=True)
        d = self.gateway.resolve_window(request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, health)
        return FWR.receive_verified(d, entry, instrument_id, timeframe_id, tables, self.gateway)
    def deliver_ml(self, request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, result: CompositionResult, *, binding, now, ref, resolved_at, tables, row_id, generation_ref, vintage_mode, omissions, exclusion_reason, health=None, consumer_manifest_id=None):
        """R53: the ML twin of `deliver`: the SAME composed Core Health (require_ancestry=True), the SAME Gateway window path (ML's OWN consumer-local outcome under the durable final store) and then `ml.receiver.build_row`. A required non-delivery needs the caller's explicit tagged exclusion reason (build_row refuses without); the returned row is `included` only for a delivered Binding. The ML closure check (optional `health`) uses the ML consumer kind. Nothing here fabricates a generation, dataset or manifest: `generation_ref`/`vintage_mode`/`omissions` are supplied."""
        if self.gateway is None or result.feature_key is None: raise Refusal("not published", code="COMPOSITION_NOT_PUBLISHED")
        if health is not None:
            use, _imp = health.decide(consumer_manifest_id, "ML", entry)
            if use == "BLOCK_PROVEN_DEPENDENCY" or use.startswith("REFUSE_"): raise Refusal(use, code="HEALTH_IMPACT_" + use)
        fk = self._owning_subject(result, entry, binding); h = self._core.gateway_health(fk.key(), fk.feature_version, now, ref, resolved_at, binding=binding, require_ancestry=True)
        d = self.gateway.resolve_window(request_id, identity, entry, instrument_id, timeframe_id, step_index, event_time, h)
        return MLR.build_row(row_id, generation_ref, [entry], [d], self.gateway, vintage_mode, omissions, exclusion_reason, tables=tables)
