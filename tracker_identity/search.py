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
)
from .normalizer import normalize_subject
from .store import CanonicalIdentityStore


def _evidence_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _subject_key(n: Mapping[str, Any]) -> tuple:
    return (
        n["feature_id"],
        n["feature_version"],
        n["definition_hash"],
        n["graph_hash"],
        n["instrument"],
        n["timeframe"],
    )


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
    now = now or datetime.now(timezone.utc)

    errors = list(search_policy.completeness_errors())
    errors.extend(normalizer.completeness_errors())

    normalized, subject_hash = normalize_subject(subject, normalizer)
    for required in ("feature_id", "feature_version", "definition_hash", "graph_hash"):
        if not normalized[required]:
            errors.append(f"LOOKUP_SUBJECT_{required.upper()}_REQUIRED")

    searched_records = []
    if not errors:
        for scope in search_policy.searched_scopes:
            searched_records.extend(store.list_scope(scope))

    exact = [r for r in searched_records if r.canonical_key == _subject_key(normalized)]
    near = [
        r for r in searched_records
        if normalized["feature_id"]
        and r.feature_id == normalized["feature_id"]
        and r.canonical_key != _subject_key(normalized)
    ]

    if len(exact) > 1:
        errors.append("AMBIGUOUS_EXACT_CANONICAL_IDENTITY")

    lookup_complete = not errors

    if errors:
        outcome = LookupOutcome.INCOMPLETE_LOOKUP
        exact_match = None
        near_matches = ()
        absent_token = None
        collision = "UNRESOLVED"
    elif len(exact) == 1:
        outcome = LookupOutcome.EXACT_CANONICAL_IDENTITY
        exact_match = exact[0]
        near_matches = ()
        absent_token = None
        collision = "CLEAR"
    elif near:
        outcome = LookupOutcome.NEAR_MATCH
        exact_match = None
        near_matches = tuple(near)
        absent_token = None
        collision = "REVIEW_REQUIRED"
    else:
        # Empty store is valid. Completeness is about governed enumerable scope,
        # not the number of identities present.
        outcome = LookupOutcome.ABSENT
        exact_match = None
        near_matches = ()
        absent_token = AbsentClaimToken(
            claim_id=f"type1-{uuid.uuid4()}",
            owner=owner,
            bound_request_id=request_id,
        )
        collision = "CLEAR"

    evidence = {
        "request_id": request_id,
        "normalized_subject": normalized,
        "searched_scopes": list(search_policy.searched_scopes),
        "scope_exclusions": dict(search_policy.scope_exclusions),
        "search_policy_id": search_policy.policy_id,
        "search_policy_version": search_policy.version,
        "search_policy_hash": search_policy.policy_hash,
        "normalizer_id": normalizer.normalizer_id,
        "normalizer_version": normalizer.version,
        "normalizer_hash": normalizer.normalizer_hash,
        "scanned_identity_keys": [
            list(r.canonical_key)
            for r in sorted(
                searched_records,
                key=lambda x: (
                    x.feature_id, x.feature_version, x.definition_hash,
                    x.graph_hash, x.instrument or "", x.timeframe or ""
                ),
            )
        ],
        "outcome": outcome.value,
        "lookup_complete": lookup_complete,
        "errors": errors,
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
        errors=tuple(errors),
    )
