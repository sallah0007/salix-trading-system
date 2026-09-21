from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Mapping, Any

from .models import (
    AbsentClaimToken,
    ClaimProvenance,
    IdentityLookupResult,
    LookupOutcome,
    NormalizerSpec,
    SearchPolicy,
    LOOKUP_ERA_SCOPES,
    SUBJECT_MODES,
)
from .content_identity import CONTENT_KEY_ALGORITHM_ID, build_content_identity_key
from .normalizer import normalize_subject
from .policy_registry import resolve_governed_search_policy
from .store import CanonicalIdentityStore

def _evidence_hash(payload: Mapping[str, Any]) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _subject_key(n: Mapping[str, Any]) -> tuple:
    return (
        n["feature_id"],n["feature_version"],n["definition_hash"],
        n["graph_hash"],n["instrument"],n["timeframe"],
    )

def _resolve_current_survivor(noncurrent_matches, searched_records):
    survivor_ids={r.canonical_survivor for r in noncurrent_matches if r.canonical_survivor}
    if not survivor_ids:
        return (), ()
    candidates=tuple(
        r for r in searched_records
        if r.is_current and r.feature_id in survivor_ids
    )
    unresolved=tuple(sorted(s for s in survivor_ids if not any(r.feature_id==s for r in candidates)))
    return candidates, unresolved

def identity_lookup(
    *,
    store: CanonicalIdentityStore,
    subject: Mapping[str, Any],
    request_id: str,
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
    owner: str = "TRACKER",
    now: datetime | None = None,
) -> IdentityLookupResult:
    now=now or datetime.now(timezone.utc)

    errors=list(search_policy.completeness_errors())
    # Self-consistency is not authority. The presented policy must ALSO bind to
    # a Tracker-owned governed policy version, so a caller cannot redefine what
    # duplicate-control completeness means by constructing its own policy and
    # self-hashing it. Any mismatch lands in `errors`, which forces
    # INCOMPLETE_LOOKUP below and issues no claim.
    errors.extend(resolve_governed_search_policy(search_policy))
    errors.extend(normalizer.completeness_errors())

    lookup_era_scope=str(subject.get("lookup_era_scope","ALL_ERAS")).strip().upper() or "ALL_ERAS"
    if lookup_era_scope not in LOOKUP_ERA_SCOPES:
        errors.append("LOOKUP_ERA_SCOPE_INVALID")
    if lookup_era_scope == "ALL_ERAS":
        errors.append("ALL_ERAS_COVERAGE_INCOMPLETE")
    if lookup_era_scope == "ERA_1_ONLY" and store.active_era_id != "ERA_1":
        errors.append("STORE_ACTIVE_ERA_NOT_ERA1")

    subject_mode=str(subject.get("subject_mode","CANONICAL_ID")).strip().upper() or "CANONICAL_ID"
    if subject_mode not in SUBJECT_MODES:
        errors.append("SUBJECT_MODE_INVALID:"+subject_mode)
        subject_mode="CANONICAL_ID"

    # CONTENT_IDENTITY_KEY is RECOMPUTED here from declared content. A
    # caller-supplied key is refused: a supplied key could manufacture a match.
    content_key=None
    if any(k in subject for k in ("content_key","content_identity_key","content_key_composite")):
        errors.append("SUPPLIED_CONTENT_KEY_NOT_ACCEPTED_RECOMPUTED_FROM_CONTENT")
    content_payload=subject.get("candidate_content")
    if content_payload is not None:
        content_key,content_errors=build_content_identity_key(content_payload)
        errors.extend(content_errors)
    elif subject_mode=="PRE_ID":
        errors.append("LOOKUP_SUBJECT_CANDIDATE_CONTENT_REQUIRED")

    active_era_id=store.active_era_id if lookup_era_scope=="ERA_1_ONLY" else None

    store_scopes=set(store.enumerate_scopes(active_era_id))
    required_scopes=set(search_policy.required_scopes)
    unenumerated_store_scopes=sorted(store_scopes-required_scopes)
    if unenumerated_store_scopes:
        errors.append("UNENUMERATED_STORE_SCOPE:"+",".join(unenumerated_store_scopes))

    # Scope reachability. An empty store is not proof of completeness.
    # Enforced in PRE_ID; CANONICAL_ID keeps its governed historical behaviour
    # (implementation invariant 10) and reports status without gating on it.
    scope_status=store.scope_status_report(search_policy.searched_scopes,active_era_id)
    if subject_mode=="PRE_ID":
        unproven=sorted(sc for sc,st in scope_status if st in ("UNREACHABLE","UNKNOWN"))
        if unproven:
            errors.append("SCOPE_NOT_PROVEN_REACHABLE:"+",".join(unproven))

    try:
        normalized,subject_hash=normalize_subject(subject,normalizer)
    except ValueError as exc:
        normalized={
            "feature_id":"","feature_version":"","definition_hash":"",
            "graph_hash":"","instrument":None,"timeframe":None,
        }
        subject_hash=""
        errors.append("NORMALIZER_APPLICATION_ERROR:"+str(exc))

    if subject_mode=="CANONICAL_ID":
        for required in ("feature_id","feature_version","definition_hash","graph_hash"):
            if not normalized[required]:
                errors.append(f"LOOKUP_SUBJECT_{required.upper()}_REQUIRED")
    else:
        # A PRE_ID subject has no canonical identity authority, and the stored
        # hashes are ID-contaminated, so they are inadmissible as identity here.
        if normalized["feature_id"] or normalized["feature_version"]:
            errors.append("PRE_ID_SUBJECT_MUST_NOT_CARRY_CANONICAL_IDENTITY")
        if normalized["definition_hash"] or normalized["graph_hash"]:
            errors.append("PRE_ID_SUBJECT_MUST_NOT_CARRY_ID_CONTAMINATED_HASHES")
        if content_key is None:
            errors.append("CONTENT_IDENTITY_KEY_UNRESOLVED")

    include_validation_scope=bool(subject.get("include_validation_scope",False))
    searched_records=[]
    if not errors:
        for scope in search_policy.searched_scopes:
            scoped=store.list_scope(scope,active_era_id)
            if not include_validation_scope:
                scoped=tuple(r for r in scoped if r.scope!="validation")
            searched_records.extend(scoped)

    subject_key=_subject_key(normalized)

    # ------------------------------------------------------------------
    # Content-keyed matching. Independent of any proposed feature name.
    # ------------------------------------------------------------------
    content_exact=[]; definition_related=[]; proxy_conflict=[]; unkeyed=[]
    if content_key is not None:
        subject_proxy=str(subject.get("proxy_status","") or "").strip().upper()
        for r in searched_records:
            if not r.has_content_key:
                # Participation is decided by the ACTUAL searched scope, not by
                # a static scope name. A row that is being searched but cannot
                # take part in content comparison cannot be ruled out, so it
                # must not be silently skipped. include_validation_scope=true
                # therefore brings validation rows under the same requirement.
                unkeyed.append(r)
                continue
            if r.content_key_composite==content_key.composite:
                content_exact.append(r)
                rp=str(r.proxy_status or "").strip().upper()
                if subject_proxy and rp and rp!=subject_proxy:
                    proxy_conflict.append(r)
            elif r.content_key_definition==content_key.definition_semantics:
                # Same DEFINITION/SEMANTICS, some other governed dimension
                # differs. Exact equality on part of a structured key — a
                # review trigger, not a similarity heuristic.
                definition_related.append(r)

    if subject_mode=="PRE_ID" and unkeyed:
        errors.append("CONTENT_KEY_UNRESOLVED_ROWS:"+",".join(
            sorted({r.feature_id for r in unkeyed})))

    content_current=[r for r in content_exact if r.is_current]
    content_noncurrent=[r for r in content_exact if not r.is_current]
    if len(content_current)>1:
        errors.append("AMBIGUOUS_CURRENT_CONTENT_IDENTITY")

    if subject_mode=="CANONICAL_ID":
        exact_all=[r for r in searched_records if r.canonical_key==subject_key]
    else:
        exact_all=[]
    exact_current=[r for r in exact_all if r.is_current]
    exact_noncurrent=[r for r in exact_all if not r.is_current]
    if len(exact_current)>1:
        errors.append("AMBIGUOUS_CURRENT_EXACT_CANONICAL_IDENTITY")

    # A name/hash match whose governed content disagrees is not an exact
    # identity. Contradiction is evaluated BEFORE any exact branch.
    content_conflict=[
        r for r in exact_current
        if content_key is not None and r.has_content_key
        and r.content_key_composite!=content_key.composite
    ]

    survivor_candidates,survivor_unresolved=_resolve_current_survivor(
        [*exact_noncurrent,*content_noncurrent],searched_records
    )
    if len(survivor_candidates)>1:
        errors.append("AMBIGUOUS_CANONICAL_SURVIVOR")
    if survivor_unresolved:
        errors.append("UNRESOLVED_CANONICAL_SURVIVOR:"+",".join(survivor_unresolved))

    near=[
        r for r in searched_records
        if normalized["feature_id"]
        and r.feature_id==normalized["feature_id"]
        and r.canonical_key!=subject_key
    ]
    for extra in (*exact_noncurrent,*content_noncurrent,*definition_related,
                  *content_conflict,*proxy_conflict):
        if extra not in near:
            near.append(extra)

    lookup_complete=not errors
    claim_record=None

    if errors:
        outcome=LookupOutcome.INCOMPLETE_LOOKUP
        exact_match=None; near_matches=(); absent_token=None
        collision="UNRESOLVED"
    elif content_conflict:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None; near_matches=tuple(dict.fromkeys(near)); absent_token=None
        collision="CONTENT_KEY_CONFLICT_REVIEW_REQUIRED"
    elif len(content_current)==1 and not proxy_conflict:
        outcome=LookupOutcome.EXACT_CANONICAL_IDENTITY
        exact_match=content_current[0]; near_matches=(); absent_token=None
        collision="CLEAR"
    elif proxy_conflict:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None; near_matches=tuple(dict.fromkeys(near)); absent_token=None
        collision="PROXY_STATUS_CONFLICT_REVIEW_REQUIRED"
    elif len(exact_current)==1:
        outcome=LookupOutcome.EXACT_CANONICAL_IDENTITY
        exact_match=exact_current[0]; near_matches=(); absent_token=None
        collision="CLEAR"
    elif len(survivor_candidates)==1:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None
        near_matches=tuple(dict.fromkeys((*near,*survivor_candidates)))
        absent_token=None
        collision="CANONICAL_SURVIVOR_REVIEW_REQUIRED"
    elif definition_related:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None; near_matches=tuple(dict.fromkeys(near)); absent_token=None
        collision="RELATED_VERSION_CONTENT_REVIEW_REQUIRED"
    elif near:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None; near_matches=tuple(dict.fromkeys(near)); absent_token=None
        collision="REVIEW_REQUIRED"
    elif subject_mode=="PRE_ID":
        # Absence is bounded to the certified structural class. Semantic
        # uniqueness is NOT certified and is never implied by this outcome.
        # The claim carries WHERE it came from and WHAT it permits. Construction
        # authority is NOT granted here: an ERA_1 structural absence is not a
        # global absence, GLOBAL_CANONICAL_ABSENCE_PROVEN is NO and semantic
        # uniqueness is not certified, so authorizes_construction stays False
        # and downstream registration fails closed. Setting it True here would
        # manufacture the very authority this gate exists to withhold.
        provenance=ClaimProvenance(
            request_id=request_id,
            content_key_composite=content_key.composite,
            lookup_outcome=LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1.value,
            lookup_complete=True,
            search_policy_id=search_policy.policy_id,
            search_policy_version=search_policy.version,
            search_policy_hash=search_policy.policy_hash,
            normalizer_id=normalizer.normalizer_id,
            normalizer_version=normalizer.version,
            normalizer_hash=normalizer.normalizer_hash,
            semantic_uniqueness="UNRESOLVED_NOT_CERTIFIED",
            authorizes_construction=False,
        )
        claim_record,claim_error=store.reserve_claim(
            content_key_composite=content_key.composite,
            request_id=request_id,issuer=owner,provenance=provenance,
        )
        if claim_error:
            outcome=LookupOutcome.INCOMPLETE_LOOKUP
            exact_match=None; near_matches=(); absent_token=None
            collision="UNRESOLVED"
            errors.append(claim_error)
            lookup_complete=False
        else:
            outcome=LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1
            exact_match=None; near_matches=()
            absent_token=AbsentClaimToken(
                claim_id=claim_record.claim_id,owner=owner,
                bound_request_id=request_id,
            )
            collision="CLEAR"
    else:
        outcome=LookupOutcome.ABSENT_IN_ERA_1
        exact_match=None; near_matches=()
        absent_token=AbsentClaimToken(
            claim_id=f"type1-{uuid.uuid4()}",owner=owner,bound_request_id=request_id,
        )
        collision="CLEAR"

    evidence={
        "request_id":request_id,
        "normalized_subject":normalized,
        "lookup_era_scope":lookup_era_scope,
        "active_era_id":active_era_id,
        "store_registry_id":store.registry_id,
        "store_scopes":sorted(store_scopes),
        "required_scopes":list(search_policy.required_scopes),
        "searched_scopes":list(search_policy.searched_scopes),
        "scope_exclusions":dict(search_policy.scope_exclusions),
        "search_policy_id":search_policy.policy_id,
        "search_policy_version":search_policy.version,
        "search_policy_hash":search_policy.policy_hash,
        "normalizer_id":normalizer.normalizer_id,
        "normalizer_version":normalizer.version,
        "normalizer_hash":normalizer.normalizer_hash,
        "normalizer_equivalence_classes":list(normalizer.equivalence_classes),
        "scanned_identity_keys":[
            [r.era_id,*list(r.canonical_key)]
            for r in sorted(
                searched_records,
                key=lambda x:(x.era_id,x.feature_id,x.feature_version,x.definition_hash,x.graph_hash,x.instrument or "",x.timeframe or ""),
            )
        ],
        "subject_mode":subject_mode,
        "content_key_composite":content_key.composite if content_key else "",
        "content_subkeys":list(content_key.subkeys()) if content_key else [],
        "scope_status":[list(x) for x in scope_status],
        "claim_id":claim_record.claim_id if claim_record else "",
        "outcome":outcome.value,
        "lookup_complete":lookup_complete,
        "errors":errors,
    }

    lookup_result_id=str(uuid.uuid4())
    evidence_hash=_evidence_hash(evidence)
    if claim_record is not None:
        # Tie the claim to the lookup result actually being emitted. Until this
        # write-once binding exists the claim is not redeemable, so a claim that
        # never came from a real emitted result cannot be presented later.
        store.bind_lookup_evidence(
            claim_id=claim_record.claim_id,
            lookup_result_id=lookup_result_id,
            lookup_evidence_hash=evidence_hash,
        )

    return IdentityLookupResult(
        lookup_result_id=lookup_result_id,
        request_id=request_id,
        lookup_subject_hash=subject_hash,
        normalized_definition_graph_id_or_hash=normalized["graph_hash"],
        outcome=outcome,
        lookup_complete=lookup_complete,
        scopes_searched=tuple(search_policy.searched_scopes),
        scope_exclusions=tuple(sorted(search_policy.scope_exclusions.items())),
        search_policy_id=search_policy.policy_id,
        search_policy_version=search_policy.version,
        search_policy_hash=search_policy.policy_hash,
        normalizer_id=normalizer.normalizer_id,
        normalizer_version=normalizer.version,
        normalizer_hash=normalizer.normalizer_hash,
        pending_collision_result=collision,
        exact_match=exact_match,
        near_match_candidates=near_matches,
        absent_claim_token=absent_token,
        lookup_evidence_hash=evidence_hash,
        verdict_ts=now.isoformat(),
        lookup_era_scope=lookup_era_scope,
        active_era_id=active_era_id,
        subject_mode=subject_mode,
        content_key_composite=content_key.composite if content_key else "",
        content_key_algorithm_id=CONTENT_KEY_ALGORITHM_ID if content_key else "",
        semantic_uniqueness="UNRESOLVED_NOT_CERTIFIED",
        scope_status=tuple(scope_status),
        errors=tuple(errors),
    )
