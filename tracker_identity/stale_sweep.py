from __future__ import annotations

from collections import defaultdict
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

    known_ids = {r.feature_id for r in records}
    current_by_feature = defaultdict(list)
    current_aliases = defaultdict(list)

    for r in records:
        if r.era_id != store.active_era_id:
            defects.append(f"CROSS_ERA_ROW_IN_ACTIVE_STORE:{r.feature_id}:{r.era_id}->{store.active_era_id}")

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
