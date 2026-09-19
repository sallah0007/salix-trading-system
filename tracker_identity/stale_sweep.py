from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Tuple

from .models import NormalizerSpec, SearchPolicy
from .store import CanonicalIdentityStore


NON_CURRENT_LIFECYCLES = {
    "DEPRECATED",
    "SUPERSEDED",
    "RETIRED",
    "REJECTED_INVALID",
    "QUARANTINED",
}
LIVE_SCOPES = {"current_active", "active_on_demand"}
TEST_MARKERS = ("test", "fixture", "tmp", "temp", "migration")


@dataclass(frozen=True)
class StaleSweepResult:
    clean: bool
    defects: Tuple[str, ...]


def _key_from_identity(r):
    return (r.feature_id, r.feature_version, r.era_id)


def _key_from_history(r):
    return (r.object_id, r.object_version, r.era_id)


def _transition_history_defects(store: CanonicalIdentityStore):
    defects=[]
    creation_by_key=defaultdict(list)
    transitions_by_key=defaultdict(list)

    creation_ids=Counter()
    for c in store.all_creation_records():
        key=_key_from_history(c)
        creation_by_key[key].append(c)
        creation_ids[c.creation_record_id]+=1
        for value, name in (
            (c.creation_record_id,"CREATION_RECORD_ID"),
            (c.segment_id,"SEGMENT_ID"),
            (c.object_id,"OBJECT_ID"),
            (c.object_version,"OBJECT_VERSION"),
            (c.era_id,"ERA_ID"),
            (c.initial_state,"INITIAL_STATE"),
            (c.creation_reason_ref,"CREATION_REASON_REF"),
            (c.created_ts,"CREATED_TS"),
            (c.created_by,"CREATED_BY"),
            (c.authority_ref,"AUTHORITY_REF"),
        ):
            if not str(value or "").strip():
                defects.append(f"CREATION_{name}_REQUIRED:{key}")

    for cid,count in creation_ids.items():
        if count>1:
            defects.append(f"DUPLICATE_CREATION_RECORD_ID:{cid}")

    transition_ids=Counter()
    for t in store.all_transitions():
        key=_key_from_history(t)
        transitions_by_key[key].append(t)
        transition_ids[t.transition_id]+=1
        for value,name in (
            (t.transition_id,"TRANSITION_ID"),
            (t.segment_id,"SEGMENT_ID"),
            (t.object_id,"OBJECT_ID"),
            (t.object_version,"OBJECT_VERSION"),
            (t.era_id,"ERA_ID"),
            (t.from_state,"FROM_STATE"),
            (t.to_state,"TO_STATE"),
            (t.reason_class,"REASON_CLASS"),
            (t.reason_ref,"REASON_REF"),
            (t.changed_ts,"CHANGED_TS"),
            (t.changed_by,"CHANGED_BY"),
            (t.authority_ref,"AUTHORITY_REF"),
            (t.record_version,"RECORD_VERSION"),
            (t.prior_transition_id,"PRIOR_TRANSITION_ID"),
        ):
            if not str(value or "").strip():
                defects.append(f"TRANSITION_{name}_REQUIRED:{t.transition_id or key}")

    for tid,count in transition_ids.items():
        if count>1:
            defects.append(f"DUPLICATE_TRANSITION_ID:{tid}")

    records_by_key=defaultdict(list)
    for r in store.all():
        records_by_key[_key_from_identity(r)].append(r)

    tracked_keys=set(creation_by_key)|set(transitions_by_key)
    for key in tracked_keys:
        creations=creation_by_key.get(key,[])
        transitions=transitions_by_key.get(key,[])
        records=records_by_key.get(key,[])

        if len(creations)!=1:
            defects.append(f"CREATION_PROVENANCE_CARDINALITY:{key}:{len(creations)}")
            continue
        creation=creations[0]
        if len(records)!=1:
            defects.append(f"TRACKED_OBJECT_CARDINALITY:{key}:{len(records)}")
            continue

        current=records[0]
        cursor=creation.creation_record_id
        expected_state=creation.initial_state
        remaining={t.transition_id:t for t in transitions}
        visited=set()

        while True:
            children=[t for t in transitions if t.prior_transition_id==cursor and t.transition_id not in visited]
            if len(children)>1:
                defects.append(f"TRANSITION_HISTORY_FORK:{key}:{cursor}")
                break
            if not children:
                break
            t=children[0]
            if t.from_state!=expected_state:
                defects.append(f"TRANSITION_FROM_STATE_CHAIN_MISMATCH:{t.transition_id}:{t.from_state}!={expected_state}")
            expected_state=t.to_state
            visited.add(t.transition_id)
            cursor=t.transition_id

        if set(remaining)-visited:
            defects.append(f"TRANSITION_HISTORY_ORPHAN_OR_CYCLE:{key}")

        if current.lifecycle_state!=expected_state:
            defects.append(
                f"STATE_HISTORY_MISMATCH:{current.feature_id}:{current.feature_version}:"
                f"{current.lifecycle_state}!={expected_state}"
            )
        expected_current=expected_state.upper()=="CURRENT"
        if current.is_current!=expected_current:
            defects.append(
                f"CURRENTNESS_HISTORY_MISMATCH:{current.feature_id}:{current.feature_version}:"
                f"{current.is_current}!={expected_current}"
            )

    return defects


def stale_state_sweep(
    *,
    store: CanonicalIdentityStore,
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
) -> StaleSweepResult:
    defects = []
    records = store.all()

    defects.extend("SEARCH_POLICY:" + x for x in search_policy.completeness_errors())
    defects.extend("NORMALIZER:" + x for x in normalizer.completeness_errors())
    defects.extend(_transition_history_defects(store))

    known_ids = {r.feature_id for r in records}
    current_by_feature = defaultdict(list)
    current_aliases = defaultdict(list)

    for r in records:
        if r.era_id != store.active_era_id:
            defects.append(f"CROSS_ERA_ROW_IN_ACTIVE_STORE:{r.feature_id}:{r.era_id}->{store.active_era_id}")

        if r.scope == "validation" and r.lifecycle_state.upper() != "CURRENT":
            defects.append(f"VALIDATION_SCOPE_NONCURRENT_LIFECYCLE:{r.feature_id}:{r.feature_version}:{r.lifecycle_state}")
        if r.scope == "validation" and not r.is_current:
            defects.append(f"VALIDATION_SCOPE_NONCURRENT_IDENTITY:{r.feature_id}:{r.feature_version}")

        if r.is_current:
            current_by_feature[r.feature_id].append(r)

        if r.is_current and r.lifecycle_state.upper() in NON_CURRENT_LIFECYCLES:
            defects.append(f"NONCURRENT_LIFECYCLE_MARKED_CURRENT:{r.feature_id}:{r.feature_version}")

        if (not r.is_current) and r.lifecycle_state.upper() == "CURRENT":
            defects.append(f"CURRENT_LIFECYCLE_MARKED_NONCURRENT:{r.feature_id}:{r.feature_version}")

        if r.canonical_survivor and r.canonical_survivor not in known_ids:
            defects.append(f"ORPHAN_CANONICAL_SURVIVOR:{r.feature_id}->{r.canonical_survivor}")

        for dep in r.dependencies:
            if dep not in known_ids:
                defects.append(f"DANGLING_DEPENDENCY:{r.feature_id}->{dep}")

        if r.is_current:
            for alias in r.aliases:
                current_aliases[alias].append(r.feature_id)

        if r.is_current and r.scope in LIVE_SCOPES:
            identity_text = "|".join((r.feature_id, *r.aliases)).lower()
            if any(marker in identity_text for marker in TEST_MARKERS):
                defects.append(f"TEST_OR_TEMP_IDENTITY_IN_LIVE_SCOPE:{r.feature_id}:{r.feature_version}")

    for feature_id, current_records in current_by_feature.items():
        if len(current_records) > 1:
            defects.append(f"MULTIPLE_CURRENT_VERSIONS:{feature_id}")

    for alias, feature_ids in current_aliases.items():
        unique_ids = sorted(set(feature_ids))
        if len(unique_ids) > 1:
            defects.append(f"CURRENT_ALIAS_COLLISION:{alias}:{','.join(unique_ids)}")

    return StaleSweepResult(clean=not defects, defects=tuple(sorted(set(defects))))
