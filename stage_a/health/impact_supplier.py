"""R49: ONE Health carried-upstream impact SUPPLIER on the delivery caller (ML and FW), derived from the EXISTING lineage surfaces (fw.lanes ConsumerManifest closure probes injected by tracker/health_wiring, health.blast_radius), not from caller
assertions. Relations used (candidate, named): the consumer is identified by its governed ConsumerManifest (manifest_id, kind FW|ML); the consumed entry must be a dependency of THAT consumer's closure;
requiredness is DERIVED from the entry's requirement_class (a caller can neither pass nor demote it). HELD (not invented): the source of the failed subjects (`failed_subjects_fn`), the feature lineage
graph instance, and the consequence for an UNDETERMINED NON-REQUIRED use (no source rule: it is only named). QUALIFIED stays false; nothing here is a live Health claim."""
from ..errors import Refusal
from ..gateway.contracts import REQUIRED
from . import blast_radius as BR

_RANK = {BR.UNAFFECTED: 0, BR.UNDETERMINED: 1, BR.AFFECTED: 2}


class HealthImpactSupplier:
    def __init__(self, consumers, feature_deps, failed_subjects_fn, closure_contains_target, closure_features, unread_features=()):
        if not isinstance(consumers, dict) or not callable(failed_subjects_fn) or not callable(closure_contains_target) or not callable(closure_features):
            raise Refusal("supplier", code="HEALTH_SUPPLIER_PORTS_REQUIRED")
        self._c, self._deps, self._failed, self._unread = dict(consumers), feature_deps, failed_subjects_fn, tuple(unread_features)
        self._cct, self._cf = closure_contains_target, closure_features      # INJECTED (health never imports fw/ml: Q18-Q20 boundary test)

    def decide(self, consumer_manifest_id, kind, entry):
        """Returns (use, impact): use in BLOCK_PROVEN_DEPENDENCY / ALLOW_PROVEN_INDEPENDENT / REFUSE_UNPROVEN_INDEPENDENCE / NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE /
        REFUSE_CONSUMER_UNBOUND / REFUSE_ENTRY_NOT_IN_CONSUMER_CLOSURE / REFUSE_HEALTH_UNREADABLE (impact is None for the last three)."""
        required = getattr(entry, "requirement_class", None) == REQUIRED
        m = self._c.get(consumer_manifest_id)
        if m is None or getattr(m, "manifest_id", None) != consumer_manifest_id or getattr(m, "kind", None) != kind:
            return ("REFUSE_CONSUMER_UNBOUND" if required else "NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE"), None
        try:
            feats = self._cf(m, self._c)
        except Refusal:
            return ("REFUSE_UNPROVEN_INDEPENDENCE" if required else "NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE"), BR.CarriedUpstreamImpact(consumer_manifest_id, BR.UNDETERMINED, b"", (), "CONSUMER_CLOSURE_UNREAD")
        if entry.feature_id not in feats:
            return "REFUSE_ENTRY_NOT_IN_CONSUMER_CLOSURE", None
        try:
            failed = list(self._failed())
        except Exception:
            return "REFUSE_HEALTH_UNREADABLE", None
        worst = BR.CarriedUpstreamImpact(consumer_manifest_id, BR.UNAFFECTED, b"", (), "NO_FAILED_SUBJECT_KNOWN")
        for f in failed:
            imp = BR.blast_radius(f, {consumer_manifest_id: m, **{k: v for k, v in self._c.items() if k != consumer_manifest_id}}, self._deps, self._cct, self._cf, self._unread)[consumer_manifest_id]
            if _RANK[imp.verdict] > _RANK[worst.verdict]:
                worst = imp
        return BR.consumer_use(worst, required), worst
