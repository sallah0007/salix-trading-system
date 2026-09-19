from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional, Tuple

from .models import FeatureIdentity
from .lifecycle import KNOWN_LIFECYCLES, lifecycle_currentness


class TransitionClass(str, Enum):
    PROMOTION = "PROMOTION"
    DEMOTION = "DEMOTION"
    SUPERSESSION = "SUPERSESSION"
    QUARANTINE = "QUARANTINE"
    RECOVERY = "RECOVERY"
    ROLLBACK = "ROLLBACK"
    RETIREMENT = "RETIREMENT"
    OTHER_GOVERNED = "OTHER_GOVERNED"


@dataclass(frozen=True)
class CreationProvenanceRecord:
    creation_record_id: str
    segment_id: str
    object_id: str
    object_version: str
    era_id: str
    initial_state: str
    creation_reason_ref: str
    created_ts: str
    created_by: str
    authority_ref: str
    evidence_ref: Optional[str] = None


@dataclass(frozen=True)
class GovernedStateTransitionRecord:
    transition_id: str
    segment_id: str
    object_id: str
    object_version: str
    era_id: str
    from_state: str
    to_state: str
    transition_class: TransitionClass
    reason_class: str
    reason_ref: str
    evidence_ref: Optional[str]
    changed_ts: str
    changed_by: str
    authority_ref: str
    record_version: str
    prior_transition_id: str


@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    identity: Optional[FeatureIdentity]
    transition: Optional[GovernedStateTransitionRecord]
    errors: Tuple[str, ...]


def identity_object_key(identity: FeatureIdentity) -> tuple[str, str, str]:
    return (identity.feature_id, identity.feature_version, identity.era_id)


def creation_object_key(record: CreationProvenanceRecord) -> tuple[str, str, str]:
    return (record.object_id, record.object_version, record.era_id)


def transition_object_key(record: GovernedStateTransitionRecord) -> tuple[str, str, str]:
    return (record.object_id, record.object_version, record.era_id)


def _required(value: Optional[str], code: str, errors: list[str]) -> None:
    if value is None or not str(value).strip():
        errors.append(code)


def transition_authority_state(
    *,
    store,
    object_id: str,
    object_version: str,
    era_id: str,
    from_state: str,
    to_state: str,
    transition_id: str,
    transition_class: TransitionClass,
    reason_class: str,
    reason_ref: str,
    changed_ts: str,
    changed_by: str,
    authority_ref: str,
    record_version: str = "1",
    evidence_ref: Optional[str] = None,
    prior_transition_id: Optional[str] = None,
) -> TransitionResult:
    """Atomically mutate a tracked Type-1 identity state and append its history record.

    This is the governed path. Type-1 remains an in-memory reference implementation:
    callers can still bypass it through raw store mutation. stale_state_sweep detects
    divergence for tracked objects; Type-2 storage/permissions must prevent the bypass.
    """
    errors: list[str] = []
    for value, code in (
        (object_id, "OBJECT_ID_REQUIRED"),
        (object_version, "OBJECT_VERSION_REQUIRED"),
        (era_id, "ERA_ID_REQUIRED"),
        (from_state, "FROM_STATE_REQUIRED"),
        (to_state, "TO_STATE_REQUIRED"),
        (transition_id, "TRANSITION_ID_REQUIRED"),
        (reason_class, "REASON_CLASS_REQUIRED"),
        (reason_ref, "REASON_REF_REQUIRED"),
        (changed_ts, "CHANGED_TS_REQUIRED"),
        (changed_by, "CHANGED_BY_REQUIRED"),
        (authority_ref, "AUTHORITY_REF_REQUIRED"),
        (record_version, "RECORD_VERSION_REQUIRED"),
    ):
        _required(value, code, errors)

    if not isinstance(transition_class, TransitionClass):
        errors.append("TRANSITION_CLASS_INVALID")
    if from_state == to_state:
        errors.append("NO_OP_TRANSITION_PROHIBITED")
    if str(to_state).upper() not in KNOWN_LIFECYCLES:
        errors.append("UNKNOWN_TO_STATE")
    if transition_class == TransitionClass.OTHER_GOVERNED and not str(reason_ref or "").strip():
        errors.append("OTHER_GOVERNED_GOVERNED_REASON_REF_REQUIRED")

    with store._transition_lock:
        key = (object_id, object_version, era_id)
        matches = [(i, r) for i, r in enumerate(store.records) if identity_object_key(r) == key]
        if len(matches) != 1:
            errors.append("TRACKED_OBJECT_NOT_UNIQUE_OR_NOT_FOUND")
            return TransitionResult(False, None, None, tuple(sorted(set(errors))))

        index, current = matches[0]
        if current.lifecycle_state != from_state:
            errors.append("FROM_STATE_MISMATCH")

        creation = store.creation_for_key(key)
        if creation is None:
            errors.append("CREATION_PROVENANCE_REQUIRED")

        prior = store.latest_transition_for_key(key)
        expected_prior = prior.transition_id if prior is not None else (
            creation.creation_record_id if creation is not None else None
        )
        if prior_transition_id is not None and prior_transition_id != expected_prior:
            errors.append("PRIOR_TRANSITION_ID_MISMATCH")
        if expected_prior is None:
            errors.append("PRIOR_TRANSITION_ID_UNRESOLVED")

        if any(t.transition_id == transition_id for t in store.transitions):
            errors.append("DUPLICATE_TRANSITION_ID")

        if errors:
            return TransitionResult(False, None, None, tuple(sorted(set(errors))))

        transition = GovernedStateTransitionRecord(
            transition_id=transition_id,
            segment_id="TRACKER",
            object_id=object_id,
            object_version=object_version,
            era_id=era_id,
            from_state=from_state,
            to_state=to_state,
            transition_class=transition_class,
            reason_class=reason_class,
            reason_ref=reason_ref,
            evidence_ref=evidence_ref,
            changed_ts=changed_ts,
            changed_by=changed_by,
            authority_ref=authority_ref,
            record_version=record_version,
            prior_transition_id=expected_prior,
        )

        new_is_current = lifecycle_currentness(to_state)
        updated = replace(current, lifecycle_state=to_state, is_current=new_is_current)

        # Atomic in this reference store: validation occurs before either mutation,
        # and both object-state replacement and history append happen under one lock.
        store.records[index] = updated
        store.transitions.append(transition)
        return TransitionResult(True, updated, transition, ())
