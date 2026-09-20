from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .importer import CanonicalEraBoundary
from .catalogue import FeatureDefinitionRecord
from .models import FeatureIdentity, LookupOutcome, NormalizerSpec, SearchPolicy
from .stale_sweep import StaleSweepResult, stale_state_sweep
from .store import CanonicalIdentityStore
from .transition import CreationProvenanceRecord

@dataclass(frozen=True)
class BuiltIdentityCandidate:
    feature_id: str
    feature_version: str
    definition_hash: str
    graph_hash: str
    semantic_definition: str
    formula: str
    lifecycle_state: str
    is_current: bool
    scope: str
    aliases: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    canonical_survivor: Optional[str] = None
    instrument: Optional[str] = None
    timeframe: Optional[str] = None
    source_provider: Optional[str] = None
    lineage_ref: Optional[str] = None
    creation_reason_ref: Optional[str] = None
    created_by: Optional[str] = None
    authority_ref: Optional[str] = None
    creation_evidence_ref: Optional[str] = None
    declared_normalization: Optional[str] = None
    causal_time_semantics: Optional[str] = None
    completion_semantics: Optional[str] = None
    availability_class: Optional[str] = None
    price_basis: Optional[str] = None
    data_vintage_mode: Optional[str] = None
    scope_universe: Optional[str] = None
    parameters: Optional[dict] = None
    fitted_state: Optional[object] = None
    proxy_status: Optional[str] = None
    claim_request_id: Optional[str] = None

@dataclass(frozen=True)
class SafeIntakeResult:
    accepted: bool
    assigned_era_id: Optional[str]
    identity: Optional[FeatureIdentity]
    definition: Optional[FeatureDefinitionRecord]
    stale_sweep: StaleSweepResult
    errors: Tuple[str, ...]

def safe_intake_built_identity(
    *,
    target_store: CanonicalIdentityStore,
    candidate: BuiltIdentityCandidate,
    era_boundary: Optional[CanonicalEraBoundary],
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
) -> SafeIntakeResult:
    errors=[]

    if era_boundary is None:
        errors.append("ACTIVE_ERA_BOUNDARY_REQUIRED")
    else:
        errors.extend(era_boundary.completeness_errors())
        if target_store.registry_id != era_boundary.registry_id:
            errors.append("ERA_BOUNDARY_REGISTRY_ID_MISMATCH")
        if target_store.active_era_id != era_boundary.era_id:
            errors.append("STORE_ACTIVE_ERA_MISMATCH")

    if not candidate.feature_id or not candidate.feature_version:
        errors.append("BUILT_IDENTITY_ID_VERSION_REQUIRED")
    if not candidate.definition_hash or not candidate.graph_hash:
        errors.append("BUILT_IDENTITY_HASHES_REQUIRED")
    if not str(candidate.creation_reason_ref or "").strip():
        errors.append("CREATION_REASON_REF_REQUIRED")
    if not str(candidate.created_by or "").strip():
        errors.append("CREATED_BY_REQUIRED")
    if not str(candidate.authority_ref or "").strip():
        errors.append("CREATION_AUTHORITY_REF_REQUIRED")
    if candidate.scope == "validation" and candidate.lifecycle_state.upper() != "CURRENT":
        errors.append("VALIDATION_SCOPE_REQUIRES_CURRENT_LIFECYCLE")
    if candidate.scope == "validation" and not candidate.is_current:
        errors.append("VALIDATION_SCOPE_REQUIRES_CURRENT_IDENTITY")

    if errors:
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,None,None,None,sweep,tuple(errors))

    # Era is deliberately not accepted from Composer/build output. Tracker assigns it
    # solely from the verified active CanonicalEraBoundary, then recomputes the
    # definition and dependency graph bindings under that era before registry mutation.
    definition=FeatureDefinitionRecord(
        feature_id=candidate.feature_id,
        feature_version=candidate.feature_version,
        semantic_definition=candidate.semantic_definition,
        formula=candidate.formula,
        dependencies=candidate.dependencies,
        era_id=era_boundary.era_id,
        definition_hash=candidate.definition_hash,
        graph_hash=candidate.graph_hash,
        instrument=candidate.instrument,
        timeframe=candidate.timeframe,
        authority="SAFE_INTAKE_BUILD_OUTPUT",
        purpose="TRACKER_SAFE_INTAKE",
        declared_normalization=candidate.declared_normalization,
        causal_time_semantics=candidate.causal_time_semantics,
        completion_semantics=candidate.completion_semantics,
        availability_class=candidate.availability_class,
        source_provider=candidate.source_provider,
        price_basis=candidate.price_basis,
        data_vintage_mode=candidate.data_vintage_mode,
        scope_universe=candidate.scope_universe,
        parameters=candidate.parameters,
        fitted_state=candidate.fitted_state,
        proxy_status=candidate.proxy_status,
    )
    definition_errors=definition.completeness_errors()
    if definition_errors:
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,definition_errors)

    # One derivation, shared with lookup: the key is recomputed from the
    # definition record's declared content, never copied in from a caller.
    content_key,content_key_errors=definition.content_identity_key()

    # A claim presented without a derivable content key cannot be validated.
    if candidate.claim_request_id is not None and content_key is None:
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,
            ("CLAIM_PRESENTED_WITHOUT_CONTENT_KEY",)+tuple(content_key_errors))

    # CANDIDATE-INTEGRITY-FIRST ORDERING.
    # Everything above this point is the candidate's own integrity: era binding,
    # required provenance, catalogue definition/graph hashes and content-key
    # derivation. Registration AUTHORITY is evaluated only now, so requiring a
    # claim can never mask an independently detectable candidate defect — a
    # tampered hash still reports the tampered hash, not "no claim".
    #
    # A valid candidate with no valid claim still fails HERE, before any
    # staging, sweep or registry mutation.
    claim_request_id=str(candidate.claim_request_id or "").strip()
    if not claim_request_id:
        # None, "" and whitespace are all the ABSENCE of a claim, never a claim.
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,
            ("CLAIM_REQUEST_ID_REQUIRED",))
    if content_key is None:
        # Claim-gated registration is only verifiable against a content key.
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,
            ("CONTENT_IDENTITY_KEY_REQUIRED_FOR_CLAIM_VALIDATION",)+tuple(content_key_errors))

    identity=FeatureIdentity(
        feature_id=candidate.feature_id,
        feature_version=candidate.feature_version,
        definition_hash=candidate.definition_hash,
        graph_hash=candidate.graph_hash,
        lifecycle_state=candidate.lifecycle_state,
        is_current=candidate.is_current,
        scope=candidate.scope,
        era_id=era_boundary.era_id,
        aliases=candidate.aliases,
        dependencies=candidate.dependencies,
        canonical_survivor=candidate.canonical_survivor,
        instrument=candidate.instrument,
        timeframe=candidate.timeframe,
        source_provider=candidate.source_provider,
        lineage_ref=candidate.lineage_ref,
        proxy_status=candidate.proxy_status,
        definition_record_ref=f"{era_boundary.era_id}:{candidate.feature_id}:{candidate.feature_version}",
        content_key_composite=content_key.composite if content_key else None,
        content_key_definition=content_key.definition_semantics if content_key else None,
        content_key_causal_time=content_key.causal_time if content_key else None,
        content_key_provenance=content_key.provenance_source if content_key else None,
        content_key_scope=content_key.scope_eligibility if content_key else None,
        content_key_fitted=content_key.fitted_learned_state if content_key else None,
        content_key_algorithm_id=(content_key.algorithm_id if content_key else None),
    )
    creation=CreationProvenanceRecord(
        creation_record_id=f"creation:{era_boundary.era_id}:{candidate.feature_id}:{candidate.feature_version}",
        segment_id="TRACKER",
        object_id=candidate.feature_id,
        object_version=candidate.feature_version,
        era_id=era_boundary.era_id,
        initial_state=candidate.lifecycle_state,
        creation_reason_ref=str(candidate.creation_reason_ref),
        created_ts=era_boundary.created_ts,
        created_by=str(candidate.created_by),
        authority_ref=str(candidate.authority_ref),
        evidence_ref=candidate.creation_evidence_ref,
    )

    staged=CanonicalIdentityStore(
        list(target_store.all())+[identity],
        registry_id=target_store.registry_id,
        active_era_id=target_store.active_era_id,
        creation_records=list(target_store.all_creation_records())+[creation],
        transitions=list(target_store.all_transitions()),
    )
    sweep=stale_state_sweep(store=staged,search_policy=search_policy,normalizer=normalizer)
    if not sweep.clean:
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,("STALE_STATE_SWEEP_FAILED",))

    # Birth event is ONE governed atomic transaction: claim re-check, identity
    # re-check, identity append, creation append and claim consumption happen
    # together under a fixed lock order. Nothing may interleave between them.
    committed,commit_error=target_store.commit_registration(
        identity=identity,
        creation=creation,
        content_key_composite=content_key.composite,
        request_id=claim_request_id,
    )
    if not committed:
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,
            ("REGISTRATION_REFUSED:"+str(commit_error),))
    return SafeIntakeResult(True,era_boundary.era_id,identity,definition,sweep,())

def composer_boundary_outcome(outcome: LookupOutcome) -> LookupOutcome:
    """Map Tracker era-qualified lookup semantics to the frozen Composer boundary.

    Composer has no era concept. Therefore an ERA_1-scoped absence cannot be
    represented as global ABSENT at that boundary.
    """
    if outcome in (LookupOutcome.ABSENT_IN_ERA_1,
                   LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1):
        return LookupOutcome.INCOMPLETE_LOOKUP
    return outcome
