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
from ..composer.expression.ceilings import check_ceilings, check_capability_declaration

VERIFIER_ID = "SALIX_STAGE_A_TRACKER_INTAKE_V1"
POLICY = {"ID": "SALIX_STAGE_A_INTAKE_POLICY", "VERSION": "1"}
POLICY["HASH"] = domain_hash("SALIX_STAGE_A_INTAKE_POLICY_V1", canonical_bytes(
    {"dimensions": ["SCHEMA", "HASH_BINDING", "CAPABILITY", "FIT_ANCESTRY", "SCOPE_BINDING", "IDENTITY_CONTENT_KEY",
                    "LOOKUP_COMPLETENESS", "DUPLICATE", "CONSTRUCTION_AUTHORITY", "REQUEST_RECORD", "RESOURCE_CEILING", "CAPABILITY_DECLARATION"]}))

REQUIRED_IDENTITY_FIELDS = ("scope", "lifecycle_state", "is_current", "declared_normalization", "causal_time_semantics",
                            "completion_semantics", "availability_class", "price_basis", "data_vintage_mode",
                            "scope_universe", "parameters", "fitted_state", "proxy_status", "instrument_applicability",
                            "source_provider")

QUANT_FEATURE = "QUANT_FEATURE"
NO_QUANT_FEATURE = "NO_QUANT_FEATURE"
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
    request_record: Optional[dict] = None          # Composer s7A APPEND request record; REQUIRED for a requested quant build

    def content_hash(self) -> str:
        d = {"package_id": self.package_id, "attempt_id": self.attempt_id, "request_id": self.request_id,
             "order_id": self.order_id, "manifest_hash": self.declared_manifest_hash,
             "graph_hash": self.declared_graph_hash, "program_hash": self.declared_program_hash,
             "semantic_definition": self.semantic_definition, "era_id": self.era_id,
             "scope": [self.expected_instrument, self.expected_timeframe],
             "quant": self.quant_feature_requested}
        if self.request_record is not None: d["request_record"] = self.request_record
        if self.resource_ceiling_ref is not None: d["resource_ceiling_ref"] = self.resource_ceiling_ref
        if self.resource_ceilings is not None: d["resource_ceilings"] = self.resource_ceilings
        if self.capability_declaration is not None: d["capability_declaration"] = self.capability_declaration
        return domain_hash("SALIX_BUILD_PACKAGE_V1", canonical_bytes(d))

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

def admit(pkg: BuildPackage, *, accepted_fit_generations: dict) -> Admission:
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
        check_capability_declaration(pkg.capability_declaration, m, pkg.resource_ceiling_ref)
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
    ancestry = "PASS" if (adm.manifest is not None and not any(d in ("SCHEMA", "FIT_ANCESTRY", "HASH_BINDING") for d, _ in failed)) \
        else ("FAIL" if failed else "UNKNOWN")
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
        "OUTCOME_INFORMATION_ACCESS_VERDICT": "NOT_ASSESSED_BOUNDARY",
        "LEARNED_OR_FITTED_ANCESTRY_VERDICT": ("PASS_REFS_CURRENT" if fit_refs and not any(d == "FIT_ANCESTRY" for d, _ in failed)
                                               else ("FAIL" if any(d == "FIT_ANCESTRY" for d, _ in failed) else "NONE_DECLARED")),
        "COMPLETION_SEMANTICS_VERDICT": "DECLARED:" + str(pkg.identity_fields.get("completion_semantics")),
        "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE": "CANDIDATE_NOT_CURRENT",
        "OMISSIONS_EXCLUSIONS_REASONS": ["SOURCE_VINTAGE_NOT_ASSESSED_BOUNDARY", "OUTCOME_ACCESS_NOT_ASSESSED_BOUNDARY"],
        "SAFE_INTAKE_TS": clock.now_iso(), "TRACKER_VERIFIER_ID": VERIFIER_ID,
        "POLICY": {"ID": POLICY["ID"], "VERSION": POLICY["VERSION"], "HASH": POLICY["HASH"]},
    }
    return R.build_report(body)
