from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Tuple

from .content_identity import CONTENT_KEY_ALGORITHM_ID
from .models import NormalizerSpec, SearchPolicy
from .store import CanonicalIdentityStore
from .lifecycle import CURRENT_LIFECYCLES, NON_CURRENT_LIFECYCLES, KNOWN_LIFECYCLES

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
        normalized_expected_state=expected_state.upper()
        if normalized_expected_state not in KNOWN_LIFECYCLES:
            defects.append(f"UNKNOWN_LIFECYCLE_STATE_IN_HISTORY:{current.feature_id}:{current.feature_version}:{expected_state}")
            expected_current=False
        else:
            expected_current=normalized_expected_state in CURRENT_LIFECYCLES
        if current.is_current!=expected_current:
            defects.append(
                f"CURRENTNESS_HISTORY_MISMATCH:{current.feature_id}:{current.feature_version}:"
                f"{current.is_current}!={expected_current}"
            )

    return defects


def _content_key_defects(store, catalogue=None):
    """Independently verify every projected content key against its definition.

    A stored key is never evidence on its own. Where the authoritative
    definition is available the key is RECOMPUTED through the single canonical
    derivation and compared subkey by subkey. A corrupted composite, a
    corrupted individual subkey, or an unrecognised algorithm id is a defect.
    """
    defects=[]
    for r in store.all():
        if r.content_key_algorithm_id and r.content_key_algorithm_id!=CONTENT_KEY_ALGORITHM_ID:
            defects.append(f"CONTENT_KEY_ALGORITHM_UNRECOGNISED:{r.feature_id}:{r.content_key_algorithm_id}")
        projected=[x for x in (r.content_key_composite,*r.content_subkeys) if x]
        if projected and not r.has_content_key:
            defects.append(f"CONTENT_KEY_PARTIALLY_PROJECTED:{r.feature_id}:{r.feature_version}")
        if catalogue is None:
            continue
        definition=catalogue.find(r.feature_id,r.feature_version)
        if definition is None:
            continue
        key,key_errors=definition.content_identity_key()
        if key_errors:
            if r.has_content_key:
                defects.append(f"CONTENT_KEY_NOT_RECONSTRUCTABLE:{r.feature_id}:{r.feature_version}")
            continue
        if not r.has_content_key:
            # No blanket validation exemption: a reconstructable key that was
            # never projected is a defect whatever the scope.
            defects.append(f"CONTENT_KEY_MISSING_BUT_RECONSTRUCTABLE:{r.feature_id}:{r.feature_version}")
            continue
        if r.content_key_composite!=key.composite:
            defects.append(f"CONTENT_KEY_COMPOSITE_MISMATCH:{r.feature_id}:{r.feature_version}")
        for label,stored,expected in (
            ("DEFINITION",r.content_key_definition,key.definition_semantics),
            ("CAUSAL_TIME",r.content_key_causal_time,key.causal_time),
            ("PROVENANCE",r.content_key_provenance,key.provenance_source),
            ("SCOPE",r.content_key_scope,key.scope_eligibility),
            ("FITTED",r.content_key_fitted,key.fitted_learned_state),
        ):
            if stored!=expected:
                defects.append(f"CONTENT_SUBKEY_MISMATCH:{label}:{r.feature_id}:{r.feature_version}")
    return defects

def stale_state_sweep(
    *,
    store: CanonicalIdentityStore,
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
    catalogue=None,
) -> StaleSweepResult:
    defects = []
    records = store.all()

    defects.extend("SEARCH_POLICY:" + x for x in search_policy.completeness_errors())
    defects.extend("NORMALIZER:" + x for x in normalizer.completeness_errors())
    defects.extend(_transition_history_defects(store))
    defects.extend(_content_key_defects(store,catalogue))

    known_ids = {r.feature_id for r in records}
    current_by_feature = defaultdict(list)
    current_aliases = defaultdict(list)

    for r in records:
        if r.era_id != store.active_era_id:
            defects.append(f"CROSS_ERA_ROW_IN_ACTIVE_STORE:{r.feature_id}:{r.era_id}->{store.active_era_id}")

        normalized_lifecycle=r.lifecycle_state.upper()
        if normalized_lifecycle not in KNOWN_LIFECYCLES:
            defects.append(f"UNKNOWN_LIFECYCLE_STATE:{r.feature_id}:{r.feature_version}:{r.lifecycle_state}")

        if r.scope == "validation" and normalized_lifecycle not in CURRENT_LIFECYCLES:
            defects.append(f"VALIDATION_SCOPE_NONCURRENT_LIFECYCLE:{r.feature_id}:{r.feature_version}:{r.lifecycle_state}")
        if r.scope == "validation" and not r.is_current:
            defects.append(f"VALIDATION_SCOPE_NONCURRENT_IDENTITY:{r.feature_id}:{r.feature_version}")

        if r.is_current:
            current_by_feature[r.feature_id].append(r)

        if r.is_current and normalized_lifecycle in NON_CURRENT_LIFECYCLES:
            defects.append(f"NONCURRENT_LIFECYCLE_MARKED_CURRENT:{r.feature_id}:{r.feature_version}")

        if (not r.is_current) and normalized_lifecycle in CURRENT_LIFECYCLES:
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
