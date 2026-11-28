"""R49 composition point: builds the Health impact supplier over the governed FW/ML ConsumerManifest registry with the fw.lanes closure probes (Tracker layer may import both; Health may not)."""
from ..fw import lanes as LN
from ..health.impact_supplier import HealthImpactSupplier


def make_supplier(consumers, feature_deps, failed_subjects_fn, unread_features=()):
    return HealthImpactSupplier(consumers, feature_deps, failed_subjects_fn, LN.closure_contains_target, LN.closure_features, unread_features)
