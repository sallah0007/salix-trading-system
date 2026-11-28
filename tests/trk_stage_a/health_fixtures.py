"""Shared fixture: a HealthImpactSupplier over ONE governed ConsumerManifest (test labels, not principals)."""
from stage_a.fw import lanes as LN
from stage_a.tracker.health_wiring import make_supplier as HS

def ml_supplier(entry, dsid="D1", failed=(), deps=None, kind="ML", closure=None, unread=()):
    m = LN.ConsumerManifest(dsid, kind, tuple(closure if closure is not None else (entry.feature_id,)))
    return HS({dsid: m}, deps if deps is not None else {entry.feature_id: ()}, lambda: failed, unread)

