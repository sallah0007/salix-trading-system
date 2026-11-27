"""R25 bounded re-verification trigger runner: Core.due_for_reverification -> (request recorded) -> reverify_manifest (REAL materializer + independent verifier) -> Core Health evidence.
One call = one bounded pass over the supplied subjects at the supplied `now`. NOT a daemon, scheduler service or host timer (no background execution is claimed; host/scheduling qualification is separate and unbound).
Source-owned values (cadence, max_age, appointed verifier, thresholds) are NOT defined here: the caller supplies `now`/`max_age`. A subject without a supplied (manifest, declared, store) binding is reported UNBOUND and is never verified or marked healthy."""
from dataclasses import dataclass
from ..errors import Refusal
from ..identifiers import Scope, FeatureKey
from .reverification import reverify_pinned, reverify_accepted

@dataclass(frozen=True)
class AcceptedBinding:
    """A subject whose maintenance verifies the ACCEPTED record as found (journal + store + FeatureKey); no manifest or declared hashes are supplied by the caller."""
    journal: object
    store: object
    feature_key: object

@dataclass(frozen=True)
class PassItem:
    subject: str
    trigger: str
    outcome: str            # VERIFIED | UNBOUND | REFUSED | KEY_MISMATCH | SKIPPED_BOUND_EXCEEDED
    detail: str = ""        # verifier status (PASS/FAIL/INSUFFICIENT_EVIDENCE) or refusal code
    evidence: str = ""      # PINNED_NEW | PINNED_EXISTING (VERIFIED items only)

def _one(core, bindings, subject, trigger, now, max_age):
    b = bindings.get(subject)
    if b is None: return PassItem(subject, trigger, "UNBOUND")
    if isinstance(b, AcceptedBinding):
        if b.feature_key.key() != subject: return PassItem(subject, trigger, "KEY_MISMATCH")
        try:
            core.request_reverification(subject, trigger)
            res, st = reverify_accepted(core, journal=b.journal, store=b.store, feature_key=b.feature_key, now=now, max_age=max_age)
            return PassItem(subject, trigger, "VERIFIED", res.status, st)
        except Refusal as e: return PassItem(subject, trigger, "REFUSED", getattr(e, "code", "") or str(e))
    manifest, declared, store = b
    if FeatureKey(Scope(manifest.instrument, manifest.timeframe), manifest.feature_id, manifest.feature_version).key() != subject: return PassItem(subject, trigger, "KEY_MISMATCH")
    try:
        core.request_reverification(subject, trigger)
        res, pin = reverify_pinned(core, manifest=manifest, declared=declared, store=store, now=now, max_age=max_age)      # verifies the EXISTING pinned record; builds+pins once only if none exists
        return PassItem(subject, trigger, "VERIFIED", res.status, pin)
    except Refusal as e: return PassItem(subject, trigger, "REFUSED", getattr(e, "code", "") or str(e))

SLOT_NAMES = ("max_age", "max_items", "max_cost")
def check_slots(slots: dict) -> dict:
    """Governed policy INPUT SLOTS (cadence/age/burst/resource). Each must carry a value and a non-empty `source_ref`; the VALUES are not defined here and the ref is not verified (presence only, UNADMITTED). A missing slot refuses: no default is invented."""
    if not isinstance(slots, dict): raise Refusal("slots", code="POLICY_SLOTS_INVALID")
    out = {}
    for n in SLOT_NAMES:
        v = slots.get(n)
        if not (isinstance(v, dict) and set(v) == {"value", "source_ref"} and type(v["value"]) is int and v["value"] >= (1 if n != "max_cost" else 0) and isinstance(v["source_ref"], str) and v["source_ref"]): raise Refusal(n, code="POLICY_SLOT_UNBOUND:" + n)
        out[n] = v
    if set(slots) - set(SLOT_NAMES): raise Refusal(",".join(sorted(set(slots) - set(SLOT_NAMES))), code="POLICY_SLOT_UNKNOWN")
    return out

def run_triggered_pass(core, bindings: dict, subjects, events, *, slots: dict, costs: dict, now: int, pass_id: str):
    """Bounded EVENT-TRIGGER pass (candidate; not a daemon/host timer): work = Core-due subjects UNION externally supplied (subject, trigger) events, COALESCED to one item per subject (a burst of events for one subject runs once; Core's own due trigger wins, then the
    lexicographically smallest event trigger - deterministic, no priority policy invented). Burst bound = max_items; resource bound = max_cost against SUPPLIED per-subject costs (a subject without a supplied cost is SKIPPED_COST_UNKNOWN, never assumed free).
    Everything not run is reported and journaled (pass record carries the slot refs). Qualification of the host, cadence and the slot VALUES stay unbound."""
    sl = check_slots(slots); work = {}
    for sub, trig in core.due_for_reverification(list(subjects), now, {k: (b.feature_key.feature_version if isinstance(b, AcceptedBinding) else b[0].feature_version) for k, b in bindings.items()}): work[sub] = trig
    for sub, trig in sorted(events):
        if sub not in work or (work[sub] is None): work[sub] = trig
    out = []; spent = 0
    for n, sub in enumerate(sorted(work)):
        if n >= sl["max_items"]["value"]: out.append(PassItem(sub, work[sub], "SKIPPED_BOUND_EXCEEDED")); continue
        c = costs.get(sub)
        if not (type(c) is int and c >= 0): out.append(PassItem(sub, work[sub], "SKIPPED_COST_UNKNOWN")); continue
        if spent + c > sl["max_cost"]["value"]: out.append(PassItem(sub, work[sub], "SKIPPED_RESOURCE_EXCEEDED")); continue
        spent += c; out.append(_one(core, bindings, sub, work[sub], now, sl["max_age"]["value"]))
    core.record_reverify_pass(pass_id, now, sl["max_items"]["value"], [[i.subject, i.trigger, i.outcome, i.detail, i.evidence] for i in out] + [["__slots__", "", "SLOT_REFS", ",".join("%s=%s" % (k, sl[k]["source_ref"]) for k in SLOT_NAMES), ""]])
    return out

def run_reverification_pass(core, bindings: dict, subjects, *, now: int, max_age: int, max_items: int = 16, pass_id: str = None):
    """bindings: {feature_key: (manifest, declared_hashes, store)}. Returns [PassItem]. Only subjects that Core itself reports due are touched (unrelated healthy baselines are left unchanged)."""
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 1: raise Refusal("max_items", code="SCHEDULER_BOUND_INVALID")
    out = []
    for n, (subject, trigger) in enumerate(core.due_for_reverification(list(subjects), now, {k: (b.feature_key.feature_version if isinstance(b, AcceptedBinding) else b[0].feature_version) for k, b in bindings.items()})):
        if n >= max_items: out.append(PassItem(subject, trigger, "SKIPPED_BOUND_EXCEEDED")); continue
        out.append(_one(core, bindings, subject, trigger, now, max_age))
    if pass_id is not None: core.record_reverify_pass(pass_id, now, max_items, [[i.subject, i.trigger, i.outcome, i.detail, i.evidence] for i in out])      # optional durable record of what was and was NOT done
    return out
