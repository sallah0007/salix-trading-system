"""R25 bounded re-verification trigger runner: Core.due_for_reverification -> (request recorded) -> reverify_manifest (REAL materializer + independent verifier) -> Core Health evidence.
One call = one bounded pass over the supplied subjects at the supplied `now`. NOT a daemon, scheduler service or host timer (no background execution is claimed; host/scheduling qualification is separate and unbound).
Source-owned values (cadence, max_age, appointed verifier, thresholds) are NOT defined here: the caller supplies `now`/`max_age`. A subject without a supplied (manifest, declared, store) binding is reported UNBOUND and is never verified or marked healthy."""
from dataclasses import dataclass
from ..errors import Refusal
from ..identifiers import Scope, FeatureKey
from .reverification import reverify_pinned

@dataclass(frozen=True)
class PassItem:
    subject: str
    trigger: str
    outcome: str            # VERIFIED | UNBOUND | REFUSED | KEY_MISMATCH | SKIPPED_BOUND_EXCEEDED
    detail: str = ""        # verifier status (PASS/FAIL/INSUFFICIENT_EVIDENCE) or refusal code
    evidence: str = ""      # PINNED_NEW | PINNED_EXISTING (VERIFIED items only)

def run_reverification_pass(core, bindings: dict, subjects, *, now: int, max_age: int, max_items: int = 16):
    """bindings: {feature_key: (manifest, declared_hashes, store)}. Returns [PassItem]. Only subjects that Core itself reports due are touched (unrelated healthy baselines are left unchanged)."""
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 1: raise Refusal("max_items", code="SCHEDULER_BOUND_INVALID")
    out = []
    for n, (subject, trigger) in enumerate(core.due_for_reverification(list(subjects), now, {k: b[0].feature_version for k, b in bindings.items()})):
        if n >= max_items: out.append(PassItem(subject, trigger, "SKIPPED_BOUND_EXCEEDED")); continue
        b = bindings.get(subject)
        if b is None: out.append(PassItem(subject, trigger, "UNBOUND")); continue
        manifest, declared, store = b
        if FeatureKey(Scope(manifest.instrument, manifest.timeframe), manifest.feature_id, manifest.feature_version).key() != subject:
            out.append(PassItem(subject, trigger, "KEY_MISMATCH")); continue
        try:
            core.request_reverification(subject, trigger)
            res, pin = reverify_pinned(core, manifest=manifest, declared=declared, store=store, now=now, max_age=max_age)      # verifies the EXISTING pinned record; builds+pins once only if none exists
            out.append(PassItem(subject, trigger, "VERIFIED", res.status, pin))
        except Refusal as e: out.append(PassItem(subject, trigger, "REFUSED", getattr(e, "code", "") or str(e)))
    return out
