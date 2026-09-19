import hashlib
import json
from typing import Mapping, Any
from .models import NormalizerSpec

def normalize_subject(subject:Mapping[str,Any],spec:NormalizerSpec):
    """Apply only equivalences explicitly declared by the bound NormalizerSpec."""
    classes=set(spec.equivalence_classes)
    if "EXACT_STRUCTURAL_IDENTITY" not in classes:
        raise ValueError("EXACT_STRUCTURAL_IDENTITY equivalence class is required")

    # EXACT_STRUCTURAL_IDENTITY V1:
    # identifiers trim surrounding whitespace;
    # content hashes are lowercase;
    # instrument/timeframe tokens are uppercase.
    normalized={
        "feature_id":str(subject.get("feature_id","")).strip(),
        "feature_version":str(subject.get("feature_version","")).strip(),
        "definition_hash":str(subject.get("definition_hash","")).strip().lower(),
        "graph_hash":str(subject.get("graph_hash","")).strip().lower(),
        "instrument":str(subject["instrument"]).strip().upper() if subject.get("instrument") is not None else None,
        "timeframe":str(subject["timeframe"]).strip().upper() if subject.get("timeframe") is not None else None,
    }
    raw=json.dumps(normalized,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return normalized, hashlib.sha256(raw.encode("utf-8")).hexdigest()
