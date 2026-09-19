from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Mapping, Any

from .models import (
    AbsentClaimToken,
    IdentityLookupResult,
    LookupOutcome,
    NormalizerSpec,
    SearchPolicy,
    LOOKUP_ERA_SCOPES,
)
from .normalizer import normalize_subject
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
    errors.extend(normalizer.completeness_errors())

    lookup_era_scope=str(subject.get("lookup_era_scope","ALL_ERAS")).strip().upper() or "ALL_ERAS"
    if lookup_era_scope not in LOOKUP_ERA_SCOPES:
        errors.append("LOOKUP_ERA_SCOPE_INVALID")
    if lookup_era_scope == "ALL_ERAS":
        errors.append("ALL_ERAS_COVERAGE_INCOMPLETE")
    if lookup_era_scope == "ERA_1_ONLY" and store.active_era_id != "ERA_1":
        errors.append("STORE_ACTIVE_ERA_NOT_ERA1")

    active_era_id=store.active_era_id if lookup_era_scope=="ERA_1_ONLY" else None

    store_scopes=set(store.enumerate_scopes(active_era_id))
    required_scopes=set(search_policy.required_scopes)
    unenumerated_store_scopes=sorted(store_scopes-required_scopes)
    if unenumerated_store_scopes:
        errors.append("UNENUMERATED_STORE_SCOPE:"+",".join(unenumerated_store_scopes))

    try:
        normalized,subject_hash=normalize_subject(subject,normalizer)
    except ValueError as exc:
        normalized={
            "feature_id":"","feature_version":"","definition_hash":"",
            "graph_hash":"","instrument":None,"timeframe":None,
        }
        subject_hash=""
        errors.append("NORMALIZER_APPLICATION_ERROR:"+str(exc))

    for required in ("feature_id","feature_version","definition_hash","graph_hash"):
        if not normalized[required]:
            errors.append(f"LOOKUP_SUBJECT_{required.upper()}_REQUIRED")

    searched_records=[]
    if not errors:
        for scope in search_policy.searched_scopes:
            searched_records.extend(store.list_scope(scope,active_era_id))

    subject_key=_subject_key(normalized)
    exact_all=[r for r in searched_records if r.canonical_key==subject_key]
    exact_current=[r for r in exact_all if r.is_current]
    exact_noncurrent=[r for r in exact_all if not r.is_current]

    if len(exact_current)>1:
        errors.append("AMBIGUOUS_CURRENT_EXACT_CANONICAL_IDENTITY")

    survivor_candidates,survivor_unresolved=_resolve_current_survivor(exact_noncurrent,searched_records)
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
    near.extend(r for r in exact_noncurrent if r not in near)

    lookup_complete=not errors

    if errors:
        outcome=LookupOutcome.INCOMPLETE_LOOKUP
        exact_match=None
        near_matches=()
        absent_token=None
        collision="UNRESOLVED"
    elif len(exact_current)==1:
        outcome=LookupOutcome.EXACT_CANONICAL_IDENTITY
        exact_match=exact_current[0]
        near_matches=()
        absent_token=None
        collision="CLEAR"
    elif len(survivor_candidates)==1:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None
        near_matches=tuple(dict.fromkeys((*near,*survivor_candidates)))
        absent_token=None
        collision="CANONICAL_SURVIVOR_REVIEW_REQUIRED"
    elif near:
        outcome=LookupOutcome.NEAR_MATCH
        exact_match=None
        near_matches=tuple(dict.fromkeys(near))
        absent_token=None
        collision="REVIEW_REQUIRED"
    else:
        outcome=LookupOutcome.ABSENT
        exact_match=None
        near_matches=()
        absent_token=AbsentClaimToken(
            claim_id=f"type1-{uuid.uuid4()}",
            owner=owner,
            bound_request_id=request_id,
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
        "outcome":outcome.value,
        "lookup_complete":lookup_complete,
        "errors":errors,
    }

    return IdentityLookupResult(
        lookup_result_id=str(uuid.uuid4()),
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
        lookup_evidence_hash=_evidence_hash(evidence),
        verdict_ts=now.isoformat(),
        lookup_era_scope=lookup_era_scope,
        active_era_id=active_era_id,
        errors=tuple(errors),
    )
