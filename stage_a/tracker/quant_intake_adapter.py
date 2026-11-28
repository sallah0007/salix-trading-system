"""Tracker quant intake: SAFE INTAKE -> ADMISSIBILITY -> FEATURE IDENTIFICATION -> CLASSIFICATION.
Consumes a Composer-side build package (field names are this implementation's mapping; exact Composer §27/§7A field
binding is an OPEN source decision) and produces the §28 TRACKER_SAFE_INTAKE_REPORT. Never issues orders, never
accepts a caller-asserted authority: construction authority is a journal-verified claim."""
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from tracker_identity import (BuiltIdentityCandidate, FeatureDefinitionRecord, LookupOutcome)
from tracker_component.lookup_adapter import construction_gate, PROCEED, DUPLICATE_OR_NEAR
from tracker_component.claims import Refusal as ClaimRefusal
from tracker_component import report as R
from ..errors import Refusal
from ..clocks import Stamp, IDENTITY
from ..identifiers import Scope, FeatureKey
from ..storage.byte_primitives import canonical_bytes, domain_hash
from ..composer.expression.manifest import Manifest
from ..composer.expression.hashing import manifest_hash, graph_hash, program_hash
from ..composer.expression.capability import check_declared
from ..composer.expression.fit_generation import check_fit_refs
from ..composer.request_record import check_request_record
from .build_output_check import check_build_output, check_conformance
from ..composer.expression.ceilings import check_ceilings, check_capability_declaration

VERIFIER_ID = "SALIX_STAGE_A_TRACKER_INTAKE_V1"
POLICY = {"ID": "SALIX_STAGE_A_INTAKE_POLICY", "VERSION": "1"}
POLICY["HASH"] = domain_hash("SALIX_STAGE_A_INTAKE_POLICY_V1", canonical_bytes(
    {"dimensions": ["SCHEMA", "HASH_BINDING", "CAPABILITY", "FIT_ANCESTRY", "SCOPE_BINDING", "IDENTITY_CONTENT_KEY",
                    "LOOKUP_COMPLETENESS", "DUPLICATE", "CONSTRUCTION_AUTHORITY", "REQUEST_RECORD", "RESOURCE_CEILING", "CAPABILITY_DECLARATION", "BUILD_OUTPUT_CONTRACT", "BUILD_CONFORMANCE"]}))

REQUIRED_IDENTITY_FIELDS = ("scope", "lifecycle_state", "is_current", "declared_normalization", "causal_time_semantics",
                            "completion_semantics", "availability_class", "price_basis", "data_vintage_mode",
                            "scope_universe", "parameters", "fitted_state", "proxy_status", "instrument_applicability",
                            "source_provider")

QUANT_FEATURE = "QUANT_FEATURE"
NO_QUANT_FEATURE = "NO_QUANT_FEATURE"
CLASSIFICATION_UNRESOLVED = "CLASSIFICATION_UNRESOLVED_HELD"   # qualified route: the caller flag says no-quant but no source-owned mapping can confirm it; neither no-quant nor a failed build
FAILED_REQUESTED_BUILD = "FAILED_REQUESTED_BUILD"

@dataclass(frozen=True)
class BuildPackage:
    package_id: str
    attempt_id: str
    request_id: str
    order_id: str
    expected_instrument: str
    expected_timeframe: str
    quant_feature_requested: bool
    manifest: Optional[dict]
    declared_manifest_hash: Optional[str]
    declared_graph_hash: Optional[str]
    declared_program_hash: Optional[str]
    lookup_outcome: object
    identity_fields: dict
    semantic_definition: str
    created_by: str
    creation_reason_ref: str
    authority_ref: str
    creation_evidence_ref: str
    era_id: str
    creation_request_id: Optional[str] = None
    resource_ceiling_ref: Optional[str] = None        # RESOURCE_CEILING_REF (governed artifact id); never defaulted
    resource_ceilings: Optional[dict] = None          # the seven ceilings as resolved from that artifact (CLAIMED values)
    capability_declaration: Optional[dict] = None     # PROGRAM_CAPABILITY_DECLARATIONS entry for this program
    build_output: Optional[dict] = None               # Composer V9 s27 BUILD_OUTPUT_PACKAGE evidence (supplied, immutable)
    request_record: Optional[dict] = None          # Composer s7A APPEND request record; REQUIRED for a requested quant build
    producer_binding: Optional[dict] = None        # C25 seven-field producer binding record for the Composer BUILD_OUTPUT_PACKAGE interface (shape + admission against a SUPPLIED authority; D6 minimum admission)

    def content_hash(self) -> str:
        d = {"package_id": self.package_id, "attempt_id": self.attempt_id, "request_id": self.request_id,
             "order_id": self.order_id, "manifest_hash": self.declared_manifest_hash,
             "graph_hash": self.declared_graph_hash, "program_hash": self.declared_program_hash,
             "semantic_definition": self.semantic_definition, "era_id": self.era_id,
             "scope": [self.expected_instrument, self.expected_timeframe],
             "quant": self.quant_feature_requested}
        if self.request_record is not None: d["request_record"] = self.request_record
        if self.producer_binding is not None: d["producer_binding"] = self.producer_binding
        if self.build_output is not None: d["build_output"] = self.build_output
        if self.resource_ceiling_ref is not None: d["resource_ceiling_ref"] = self.resource_ceiling_ref
        if self.resource_ceilings is not None: d["resource_ceilings"] = self.resource_ceilings
        if self.capability_declaration is not None: d["capability_declaration"] = self.capability_declaration
        return domain_hash("SALIX_BUILD_PACKAGE_V1", canonical_bytes(d))

# Duties the Tracker cannot determine from anything it reads. They are MANDATORY: an admission carrying one cannot proceed to certification/acceptance unless a Tracker-originated
# DutyEvidence names it (pipeline.run). No such evidence provider exists in this repository; only tests construct it (ref labelled SIMULATED). No algorithm is invented.
MANDATORY_UNVERIFIED_DUTIES = ("CAPABILITY_CLASS_STRUCTURE", "OUTCOME_ACCESS_DECLARATION_GOVERNED_BEFORE_BUILD", "S28_INPUTS_RESOLVE", "S28_REPRODUCTION", "S28_FULL_CONFORMANCE")

@dataclass(frozen=True)
class DutyEvidence:
    """Tracker-originated evidence that named mandatory duties were VERIFIED by a real Tracker check. Never a package field; a caller string/dict is not evidence."""
    duties: frozenset
    evidence_ref: str
    def __post_init__(self):
        if not isinstance(self.duties, frozenset) or not self.duties or not all(isinstance(d, str) for d in self.duties):
            raise Refusal(repr(self.duties), code="DUTY_EVIDENCE_MALFORMED")
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref.strip():
            raise Refusal("evidence_ref", code="DUTY_EVIDENCE_WITHOUT_REF")

def unresolved_mandatory(adm, evidence, *, simulation=False, baseline_connected=True):
    """Mandatory duties still unverified for this admission: [(duty, reason)]. Fail closed. Evidence that is absent or not a DutyEvidence verifies nothing. In QUALIFIED mode
    (simulation=False, the default) NO evidence discharges anything, because no real Tracker verifier exists for any of these duties (a typed object anyone can construct is not
    authority); only an explicit SIMULATION run lets DutyEvidence stand in, and such a run is never qualified. A missing baseline connection is held in qualified mode (TR-02: one
    registry/lifecycle path)."""
    verified = evidence.duties if (simulation and isinstance(evidence, DutyEvidence)) else frozenset()
    out = [(d, "UNRESOLVED_MANDATORY_VERIFICATION") for d, _ in adm.unverified if d in MANDATORY_UNVERIFIED_DUTIES and d not in verified]
    if evidence is not None and not isinstance(evidence, DutyEvidence):
        out.append(("DUTY_EVIDENCE", "DUTY_EVIDENCE_MALFORMED"))
    if not simulation and not baseline_connected:
        out.append(("BASELINE_REGISTRATION", "BASELINE_NOT_CONNECTED"))
    return out

@dataclass
class Admission:
    classification: str
    manifest: Optional[Manifest] = None
    hashes: Optional[Tuple[str, str, str]] = None
    feature_key: Optional[FeatureKey] = None
    subject_key: Optional[str] = None
    definition: Optional[FeatureDefinitionRecord] = None
    failed: List[Tuple[str, str]] = field(default_factory=list)
    lookup_gate: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    ancestry: Tuple[str, str] = ("NOT_REQUIRED", "")                 # R54: whole-ancestry state, separate from the narrow fit-reference currency: NOT_REQUIRED | UNKNOWN:<why> | FAIL:<code> | PASS_CANDIDATE
    unverified: List[Tuple[str, str]] = field(default_factory=list)   # duties the Tracker could NOT determine: labelled, never certified

    @property
    def admissible(self):
        return not self.failed and self.classification == QUANT_FEATURE

def baseline_definition(pkg: BuildPackage, manifest: Manifest, prog_hash: str) -> FeatureDefinitionRecord:
    idf = pkg.identity_fields
    base = FeatureDefinitionRecord(
        manifest.feature_id, manifest.feature_version, pkg.semantic_definition,
        "SALIX_EXPR_PROGRAM_V1:" + prog_hash, (), pkg.era_id, "", "", manifest.instrument, manifest.timeframe)
    return FeatureDefinitionRecord(
        manifest.feature_id, manifest.feature_version, pkg.semantic_definition,
        "SALIX_EXPR_PROGRAM_V1:" + prog_hash, (), pkg.era_id,
        base.computed_definition_hash(), base.computed_graph_hash(), manifest.instrument, manifest.timeframe,
        declared_normalization=idf["declared_normalization"], causal_time_semantics=idf["causal_time_semantics"],
        completion_semantics=idf["completion_semantics"], availability_class=idf["availability_class"],
        source_provider=idf["source_provider"], price_basis=idf["price_basis"],
        data_vintage_mode=idf["data_vintage_mode"], scope_universe=idf["scope_universe"],
        parameters=idf["parameters"], fitted_state=idf["fitted_state"], proxy_status=idf["proxy_status"],
        instrument_applicability=idf["instrument_applicability"])

def build_candidate(pkg: BuildPackage, definition: FeatureDefinitionRecord, *, claim_request_id=None,
                    creation_evidence_ref=None) -> BuiltIdentityCandidate:
    idf = pkg.identity_fields
    return BuiltIdentityCandidate(
        feature_id=definition.feature_id, feature_version=definition.feature_version,
        definition_hash=definition.definition_hash, graph_hash=definition.graph_hash,
        semantic_definition=definition.semantic_definition, formula=definition.formula,
        lifecycle_state=idf["lifecycle_state"], is_current=idf["is_current"], scope=idf["scope"],
        dependencies=definition.dependencies, instrument=definition.instrument, timeframe=definition.timeframe,
        source_provider=idf["source_provider"], lineage_ref="build:" + pkg.attempt_id,
        creation_reason_ref=pkg.creation_reason_ref, created_by=pkg.created_by, authority_ref=pkg.authority_ref,
        creation_evidence_ref=creation_evidence_ref or pkg.creation_evidence_ref,
        declared_normalization=idf["declared_normalization"], causal_time_semantics=idf["causal_time_semantics"],
        completion_semantics=idf["completion_semantics"], availability_class=idf["availability_class"],
        price_basis=idf["price_basis"], data_vintage_mode=idf["data_vintage_mode"], scope_universe=idf["scope_universe"],
        parameters=idf["parameters"], fitted_state=idf["fitted_state"], proxy_status=idf["proxy_status"],
        claim_request_id=claim_request_id, instrument_applicability=idf["instrument_applicability"])

def _check_producer_binding(pkg, producer_authority, a):
    """Composer 27/28 BUILD_OUTPUT_PACKAGE interface producer binding (C25 'Missing is UNSATISFIED'; D6 minimum admission). `producer_authority` = {"lookup": callable(scope, interface_id, version) -> record|None, "source_ref": str, "interface_id": str}: a SOURCE-OWNED input (the governed record is Manager-only), so
    with none supplied the duty is labelled unverified (never certified, never invented) and the build is not failed for a source this repository cannot read; WITH one supplied a missing, malformed, foreign-interface or unadmitted binding FAILS the build. Admission is exact seven-field equality with the authority's record."""
    if producer_authority is None:
        a.unverified.append(("COMPOSER_PRODUCER_BINDING_ADMISSION", "NOT_VERIFIED_NO_AUTHORITY_SUPPLIED")); return
    from ..binding import producer_admission as PA
    try: lookup, ref, iface = producer_authority["lookup"], producer_authority["source_ref"], producer_authority["interface_id"]
    except (KeyError, TypeError): a.failed.append(("PRODUCER_BINDING", "PRODUCER_AUTHORITY_MALFORMED")); return
    if pkg.producer_binding is None: a.failed.append(("PRODUCER_BINDING", "PRODUCER_BINDING_MISSING_UNSATISFIED")); return
    if not isinstance(pkg.producer_binding, dict) or pkg.producer_binding.get("interface_id") != iface: a.failed.append(("PRODUCER_BINDING", "PRODUCER_BINDING_FOREIGN_INTERFACE")); return
    try: d = PA.admit(pkg.producer_binding, lookup, ref)
    except Refusal as e: a.failed.append(("PRODUCER_BINDING", e.code)); return
    if d.status != PA.ADMITTED_AGAINST_SUPPLIED_AUTHORITY: a.failed.append(("PRODUCER_BINDING", d.reason))

_LEARNED_EDGES = ("LEARNED_DERIVED_MODEL_EDGE", "MODEL_GENERATION_INPUT_EDGE")

@dataclass(frozen=True)
class AncestryBinding:
    """What an EXPLICIT owner-supplied ancestry resolver returns (R54). The resolver, not intake, owns the mapping from the package's two strings and its fit references to nodes of a closure record; intake assumes NO string/number equality between the package fields and node ids or hashes (the sources do not give one). The binding names: the closure `record` (ml/closure ClosureRecord), the node id the resolver says is this FEATURE (`subject_node`), the nodes it says correspond to UPSTREAM_MODEL_ID / UPSTREAM_GENERATION_ID, and one node per fit-reference generation. Intake then CHECKS those claims against the DERIVED closure. Candidate only: the completeness witness stays unadmitted."""
    record: object
    subject_node: str
    upstream_model_node: str
    upstream_generation_node: str
    fit_ref_nodes: dict          # fit-reference generation (int) -> closure node id

def _check_ancestry(pkg, m, a, resolver):
    """R54 (Composer V9 s27/s28): UPSTREAM_MODEL_ID/UPSTREAM_GENERATION_ID are ancestry EDGES whose closure is governed by Contract DEPENDENCY_CLOSURE_RECORD / ANCESTRY_CLOSURE_REPORT. Two strings in the package correlate to nothing by themselves, and the narrow fit-reference currency (`check_fit_refs`) is not whole-ancestry completeness. A learned-derived build (fit_refs non-empty) is therefore ancestry UNKNOWN (held: intake does not proceed) unless an EXPLICIT `ancestry_resolver(feature_key, upstream_model_id, upstream_generation_id, fit_refs)` returns an AncestryBinding whose closure (1) is well-formed, (2) DERIVES to PASS, (3) has the claimed subject node as its own subject, (4) reaches the upstream-model and upstream-generation nodes AND every fit-reference node, (5) with at least one content-carrying learned/model-generation edge among the edges into reached model/generation nodes. Any contradiction FAILS; a missing resolver/binding stays UNKNOWN."""
    if not m.data["fit_refs"]: a.ancestry = ("NOT_REQUIRED", ""); return
    bo = pkg.build_output if isinstance(pkg.build_output, dict) else {}
    mid, gid = bo.get("UPSTREAM_MODEL_ID"), bo.get("UPSTREAM_GENERATION_ID")
    def fail(code): a.ancestry = ("FAIL", code); a.failed.append(("ANCESTRY_CLOSURE", code))
    def held(why): a.ancestry = ("UNKNOWN", why); a.failed.append(("ANCESTRY_CLOSURE", "ANCESTRY_CLOSURE_UNRESOLVED_HELD"))
    if not (isinstance(mid, str) and mid.strip() and isinstance(gid, str) and gid.strip()): a.ancestry = ("FAIL", "LEARNED_DERIVED_WITHOUT_UPSTREAM_GENERATION_IDENTITY"); return      # already a failed dimension via the build-output contract check: not re-added
    if a.feature_key is None: return held("SUBJECT_IDENTITY_NOT_DERIVED")
    if resolver is None: return held("NO_RESOLVER_SUPPLIED")
    from ..ml import closure as CL
    b = resolver(a.feature_key, mid, gid, list(m.data["fit_refs"]))
    if b is None: return held("RESOLVER_RETURNED_NO_BINDING")
    if not isinstance(b, AncestryBinding) or not isinstance(b.fit_ref_nodes, dict): return fail("ANCESTRY_BINDING_MALFORMED")
    try: v = CL.derive(b.record)
    except Refusal as e: return fail("ANCESTRY_CLOSURE_MALFORMED:" + e.code)
    rec = b.record
    if v.verdict != "PASS": return fail("ANCESTRY_CLOSURE_NOT_PASS:" + ",".join(v.reasons))
    if rec.subject_id != b.subject_node: return fail("ANCESTRY_CLOSURE_FOR_ANOTHER_SUBJECT")
    reached = set(v.reached)
    if b.upstream_model_node not in reached or b.upstream_generation_node not in reached: return fail("UPSTREAM_ID_NOT_IN_CLOSURE")
    gens = [r.get("generation") for r in m.data["fit_refs"]]
    if any(g not in b.fit_ref_nodes or b.fit_ref_nodes[g] not in reached for g in gens): return fail("FIT_REFERENCE_NOT_IN_CLOSURE")
    if not any(e.edge_class in _LEARNED_EDGES and e.content_carrying and e.child in ({rec.subject_id} | reached) and e.parent in (b.upstream_model_node, b.upstream_generation_node) for e in rec.edges):
        return fail("NO_LEARNED_EDGE_TO_UPSTREAM_IDS")
    a.ancestry = ("PASS_CANDIDATE", "")

def admit(pkg: BuildPackage, *, accepted_fit_generations: dict, conformance=None, producer_authority=None, ancestry_resolver=None) -> Admission:
    """Pure admissibility + identification (no journal effects)."""
    if not pkg.quant_feature_requested:
        # Explicit NO_QUANT_FEATURE only when no quant build was requested AND none was supplied.
        if pkg.manifest is not None:
            a = Admission(FAILED_REQUESTED_BUILD)
            a.failed.append(("CLASSIFICATION", "MANIFEST_SUPPLIED_FOR_NO_QUANT_REQUEST"))
            return a
        return Admission(NO_QUANT_FEATURE)
    a = Admission(QUANT_FEATURE)
    def fail(dim, code):
        a.failed.append((dim, code))
    try:
        if not isinstance(pkg.manifest, dict):
            raise Refusal("no manifest for a requested quant build", code="MANIFEST_MISSING")
        try:                                              # ceilings first: they bound the parse; absence refuses, nothing is defaulted
            ceilings = check_ceilings(pkg.resource_ceiling_ref, pkg.resource_ceilings)
        except Refusal as e:
            a.failed.append(("RESOURCE_CEILING", e.code)); a.classification = FAILED_REQUESTED_BUILD
            return a
        m = Manifest.from_dict(pkg.manifest, ceilings)
    except Refusal as e:
        fail("SCHEMA", e.code)
        a.classification = FAILED_REQUESTED_BUILD      # TR-06: never silently baseline-only / NONE
        return a
    a.manifest = m
    # s7A request record (stage ORDER: the package carries an order_id). Missing record fails closed; UNKNOWN target -> REVIEW_REQUIRED, not admitted.
    if pkg.request_record is None:
        fail("REQUEST_RECORD", "REQUEST_RECORD_MISSING")
    else:
        try:
            if check_request_record(pkg.request_record, "ORDER") == "REVIEW_REQUIRED":
                fail("REQUEST_RECORD", "REQUEST_REVIEW_REQUIRED_TARGET_CONSUMER_UNKNOWN")
        except Refusal as e:
            fail("REQUEST_RECORD", e.code)
    _check_producer_binding(pkg, producer_authority, a)
    a.hashes = (manifest_hash(m), graph_hash(m), program_hash(m))
    if (pkg.declared_manifest_hash, pkg.declared_graph_hash, pkg.declared_program_hash) != a.hashes:
        fail("HASH_BINDING", "DECLARED_HASH_NOT_RECOMPUTED_HASH")
    if (m.instrument, m.timeframe) != (pkg.expected_instrument, pkg.expected_timeframe):
        fail("SCOPE_BINDING", "MANIFEST_SCOPE_DIFFERS_FROM_REQUEST")
    try:
        check_declared(m)
    except Refusal as e:
        fail("CAPABILITY", e.code)
    try:
        check_build_output(pkg.build_output, order_id=pkg.order_id, creation_request_id=pkg.creation_request_id or pkg.request_id,
                           learned_derived=bool(m.data["fit_refs"]))
    except Refusal as e:
        fail("BUILD_OUTPUT_CONTRACT", e.code)
    try:
        check_conformance(pkg.build_output, conformance, (pkg.request_record or {}).get("OUTCOME_INFORMATION_ACCESS"))            # Tracker-originated verification evidence; none supplied => FORBIDDEN is held
        # R18: the declaration compared above comes from the request_record SUPPLIED INSIDE the BuildPackage, not from issued-order evidence (ConstructionOrder carries no declaration;
        # ClaimService verifies order_id/subject_key/source_binding_hash/issued_by/validity only). Equality is therefore STRUCTURAL; governed-before-build binding is unverified.
        a.unverified.append(("OUTCOME_ACCESS_DECLARATION_GOVERNED_BEFORE_BUILD", "NOT_VERIFIED_SUPPLIED_RECORD_STRUCTURAL_EQUALITY"))
        # Composer s28 duties the Tracker cannot determine here (R19): exact input ids are prose-only (no key; check_inputs_resolve is never called), the pipeline's hash recomputation is
        # domain-limited (not a build-output reproduction claim), and full s28 conformance is a boundary the Tracker did not assess.
        a.unverified.extend([("S28_INPUTS_RESOLVE", "NOT_VERIFIED_NO_KEY_FOR_EXACT_INPUT_IDS"), ("S28_REPRODUCTION", "NOT_VERIFIED_DOMAIN_LIMITED_HASH_RECOMPUTE_ONLY"),
                             ("S28_FULL_CONFORMANCE", "NOT_ASSESSED_BOUNDARY")])
    except Refusal as e:
        fail("BUILD_CONFORMANCE", e.code)
    try:
        check_capability_declaration(pkg.capability_declaration, m, pkg.resource_ceiling_ref)
        # Parent V1.2 capability-emulation firewall: class-to-structure verification is mandatory. Enum membership (checked above) is NOT that verification, and no source read
        # defines the compatibility semantics: the declared class is carried UNVERIFIED (never read as certified); an ambiguous classification would route to GENERIC_EXTENSION review.
        a.unverified.append(("CAPABILITY_CLASS_STRUCTURE", "NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE"))
    except Refusal as e:
        fail("CAPABILITY_DECLARATION", e.code)
    try:
        check_fit_refs(m.data["fit_refs"], accepted_fit_generations)
    except Refusal as e:
        fail("FIT_ANCESTRY", e.code)
    missing = [k for k in REQUIRED_IDENTITY_FIELDS if k not in pkg.identity_fields or pkg.identity_fields[k] is None]
    if missing:
        fail("IDENTITY_CONTENT_KEY", "IDENTITY_FIELDS_MISSING:" + ",".join(missing))
    else:
        a.feature_key = FeatureKey(Scope(m.instrument, m.timeframe), m.feature_id, m.feature_version)
        d = baseline_definition(pkg, m, a.hashes[2])
        key, errs = d.content_identity_key()
        if key is None:
            fail("IDENTITY_CONTENT_KEY", "CONTENT_KEY_NOT_DERIVABLE:" + ",".join(errs))
        else:
            a.definition, a.subject_key = d, key.composite
    _check_ancestry(pkg, m, a, ancestry_resolver)
    gate = construction_gate(pkg.lookup_outcome)
    a.lookup_gate = gate
    if gate == DUPLICATE_OR_NEAR:
        fail("DUPLICATE", "EXACT_OR_NEAR_MATCH_EXISTS")
    elif gate != PROCEED:
        fail("LOOKUP_COMPLETENESS", "INCOMPLETE_LOOKUP")
    if a.failed:
        a.classification = FAILED_REQUESTED_BUILD
    return a

def reserve_authority(claims, pkg: BuildPackage, adm: Admission):
    """Final-authority step: journal-verified order + claim. Returns claim dict or records a failed dimension."""
    try:
        return claims.reserve(subject_key=adm.subject_key, request_id=pkg.request_id, order_id=pkg.order_id,
                              lookup_outcome=pkg.lookup_outcome)
    except ClaimRefusal as e:
        adm.failed.append(("CONSTRUCTION_AUTHORITY", e.code))
        adm.classification = FAILED_REQUESTED_BUILD
        return None

def build_safe_intake_report(pkg: BuildPackage, adm: Admission, *, clock, verdict: str, identity_decision: str,
                             registry_ref: Optional[str]) -> dict:
    Stamp(IDENTITY, clock.now_iso())
    failed = list(adm.failed)
    fit_refs = adm.manifest.data["fit_refs"] if adm.manifest else []
    # R54: ancestry completeness is NOT PASS when s27's learned-derived construction-side ancestry is missing/inconsistent (reason codes from check_build_output), nor when the manifest/hash/fit ancestry failed.
    # R54: whole-ancestry state comes from the closure check (separate from the narrow fit-reference currency verdict below). FAIL on any ancestry failure; UNKNOWN when required ancestry was not resolved; PASS only for NOT_REQUIRED (no fit_refs) or a derived candidate closure.
    _ANC_CODES = ("LEARNED_DERIVED_WITHOUT_UPSTREAM_GENERATION_IDENTITY", "UPSTREAM_ANCESTRY_WITHOUT_LEARNED_DERIVATION")
    st = getattr(adm, "ancestry", ("NOT_REQUIRED", ""))[0]
    hard = adm.manifest is None or any(d in ("SCHEMA", "FIT_ANCESTRY", "HASH_BINDING") or c in _ANC_CODES or (d == "ANCESTRY_CLOSURE" and not c.endswith("UNRESOLVED_HELD")) for d, c in failed)
    ancestry = "FAIL" if (hard and failed) else ("UNKNOWN" if (st == "UNKNOWN" or adm.manifest is None) else ("PASS" if st in ("NOT_REQUIRED", "PASS_CANDIDATE") else "FAIL"))
    oia_fail = [c for d, c in failed if d == "BUILD_CONFORMANCE"]
    oia = ("FAIL:" + oia_fail[0]) if oia_fail else ("PASS_ON_SUPPLIED_CONFORMANCE_EVIDENCE" if pkg.build_output is not None and adm.manifest is not None and not any(d == "BUILD_OUTPUT_CONTRACT" for d, _ in failed) else "NOT_ASSESSED")
    from .build_output_check import section27_status
    g27 = section27_status(pkg.build_output, learned_derived=bool(fit_refs), manifest_verified=adm.manifest is not None and not any(d in ("SCHEMA", "HASH_BINDING") for d, _ in failed))
    omissions = ["SOURCE_VINTAGE_NOT_ASSESSED_BOUNDARY"] + (["OUTCOME_ACCESS_NOT_ASSESSED_BOUNDARY"] if oia == "NOT_ASSESSED" else []) \
        + ["S27_GROUP_%d_%s" % (n, st.replace(":", "=")) for n, st in g27 if st.startswith("ABSENT_TOKEN")] \
        + ["S27_PROSE_GROUPS_NO_SOURCE_KEY_NOT_ASSESSED=" + ",".join(str(n) for n, st in g27 if st == "NO_SOURCE_KEY")]
    body = {
        "SAFE_INTAKE_REPORT_ID": "TSIR:" + pkg.attempt_id,
        "BUILD_OUTPUT_PACKAGE": {"ID": pkg.package_id, "HASH": pkg.content_hash()},
        "REQUEST": {"REQUEST_ID": pkg.request_id, "CREATION_REQUEST_ID": pkg.creation_request_id or pkg.request_id},
        "INTAKE_VERDICT": verdict, "FAILED_DIMENSIONS": [d for d, _ in failed],
        "FAILED_DIMENSION_REASON_CODES": [c for _, c in failed],
        "IDENTITY_DECISION": identity_decision,
        "RESULTING_FEATURE": ({"FEATURE_ID": adm.feature_key.feature_id, "FEATURE_VERSION": adm.feature_key.feature_version,
                               "REGISTRY_ENTRY_REF": registry_ref} if (adm.feature_key and registry_ref) else None),
        "CANONICAL_SURVIVOR": None, "FEATURE_VERSION_RELATIONSHIP_REF": None,
        "DEPENDENCY_CLOSURE_REF": "DEPCLOSURE:" + (adm.hashes[2] if adm.hashes else "NONE"),
        "ANCESTRY_COMPLETENESS": ancestry,
        "CAUSAL_AVAILABILITY_VERDICT": "PASS_EXPRESSION_CAUSAL_ONLY" if adm.manifest else "NOT_ASSESSED",
        "SOURCE_VINTAGE_PROVENANCE_VERDICT": "NOT_ASSESSED_BOUNDARY",
        "OUTCOME_INFORMATION_ACCESS_VERDICT": oia,
        "LEARNED_OR_FITTED_ANCESTRY_VERDICT": ("PASS_REFS_CURRENT" if fit_refs and not any(d == "FIT_ANCESTRY" for d, _ in failed)
                                               else ("FAIL" if any(d == "FIT_ANCESTRY" for d, _ in failed) else "NONE_DECLARED")),
        "COMPLETION_SEMANTICS_VERDICT": "DECLARED:" + str(pkg.identity_fields.get("completion_semantics")),
        "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE": "CANDIDATE_NOT_CURRENT",
        "OMISSIONS_EXCLUSIONS_REASONS": omissions + (["ANCESTRY_CLOSURE_" + adm.ancestry[0] + (":" + adm.ancestry[1] if adm.ancestry[1] else "")] if adm.ancestry[0] != "NOT_REQUIRED" else []),
        "SAFE_INTAKE_TS": clock.now_iso(), "TRACKER_VERIFIER_ID": VERIFIER_ID,
        "POLICY": {"ID": POLICY["ID"], "VERSION": POLICY["VERSION"], "HASH": POLICY["HASH"]},
    }
    return R.build_report(body)
