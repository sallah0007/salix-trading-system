import hashlib, json
from typing import Mapping, Any
from .models import NormalizerSpec

def normalize_subject(subject:Mapping[str,Any],spec:NormalizerSpec):
    normalized={
        "feature_id":str(subject.get("feature_id","")).strip(),
        "feature_version":str(subject.get("feature_version","")).strip(),
        "definition_hash":str(subject.get("definition_hash","")).strip().lower(),
        "graph_hash":str(subject.get("graph_hash","")).strip().lower(),
        "instrument":str(subject["instrument"]).strip().upper() if subject.get("instrument") is not None else None,
        "timeframe":str(subject["timeframe"]).strip().upper() if subject.get("timeframe") is not None else None,
    }
    raw=json.dumps(normalized,sort_keys=True,separators=(",",":"))
    return normalized, hashlib.sha256(raw.encode()).hexdigest()
