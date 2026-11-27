"""ML six-join candidate interface (A04 ML joins; Build Plan mapping/dependency disposition ML section; MLCore 28/31). Generic and source-backed: it checks that each of the six joins is PRESENT, well-shaped and - where an ML-owned registry instance
is supplied - EQUAL to that instance. Joins 4 and 5 are checked against the actual `GenerationRegistry` (manifest components / lifecycle ledger MANIFEST_ID, HASH, epoch). Joins 1, 2, 3, 6 name instances this repository does not have
(dataset manifest registry, Tracker catalog snapshot, bind-time Health service, exposure ledger): they are checked for shape (and, for 2, membership in a SUPPLIED catalog snapshot, for 3 the single EVIDENCE_REF rule, for 6 AVAILABLE_ASOF strictly before the fence)
and are otherwise PRESENT_UNVERIFIED. The writer principal / grant for ML dataset-manifest construction is NOT in source (E-06 principals do not include it): this module appoints nobody, and its result is never qualified. A SIM manifest class
never counts as a REAL one."""
from dataclasses import dataclass
from ..errors import Refusal
from .generation_lifecycle import MIN_COMPONENTS

JOINS = ("J1_DATASET_MANIFEST", "J2_INCLUDED_FEATURES", "J3_BIND_TIME_HEALTH", "J4_GENERATION_COMPONENTS", "J5_LIFECYCLE_LEDGER", "J6_RESEARCH_FAMILY_EXPOSURE")
VERIFIED_AGAINST_REGISTRY, PRESENT_UNVERIFIED, MISSING, MISMATCH = "VERIFIED_AGAINST_ML_REGISTRY", "PRESENT_UNVERIFIED_INSTANCE_UNBOUND", "MISSING", "MISMATCH"
def _s(x): return isinstance(x, str) and bool(x)
def _i(x): return type(x) is int and x >= 0

@dataclass(frozen=True)
class JoinReport:
    statuses: tuple            # ((join, status, detail), ...)
    complete: bool             # every join is VERIFIED or PRESENT_UNVERIFIED (none MISSING/MISMATCH); NOT acceptance
    correlation: tuple = ()    # ((check, status, detail), ...): J4/J5 (and an optional issued request snapshot) must name the SAME generation; field-shape checks alone are not integrated joins
    qualified: bool = False    # never True here: writer principal, instances and acceptance are unbound
    writer_principal: str = "UNBOUND_NOT_IN_SOURCE"

def check_six_joins(joins, registry, *, fence, catalog_snapshot=None, request_snapshot=None) -> JoinReport:
    if not isinstance(joins, dict): raise Refusal(type(joins).__name__, code="ML_JOINS_NOT_A_RECORD")
    if not _i(fence): raise Refusal("fence", code="ML_JOINS_FENCE_INVALID")
    out = []
    def add(j, st, d=""): out.append((j, st, d))
    j = joins.get("J1_DATASET_MANIFEST")
    if not (isinstance(j, dict) and set(j) == {"binding_id", "dataset_manifest_id", "dataset_manifest_hash"} and all(_s(v) for v in j.values())): add(JOINS[0], MISSING if j is None else MISMATCH, "shape")
    else: add(JOINS[0], PRESENT_UNVERIFIED, "dataset manifest registry instance unbound")
    j = joins.get("J2_INCLUDED_FEATURES"); keys = ("feature_id", "feature_version", "definition_hash", "formula_hash", "graph_hash", "closure_ref")
    if not (isinstance(j, list) and j and all(isinstance(f, dict) and set(f) == set(keys) and all(_s(f[k]) for k in keys) for f in j)): add(JOINS[1], MISSING if j is None else MISMATCH, "shape")
    elif catalog_snapshot is None: add(JOINS[1], PRESENT_UNVERIFIED, "catalog snapshot instance unbound")
    else:
        bad = [f["feature_id"] + "/" + f["feature_version"] for f in j if catalog_snapshot.get((f["feature_id"], f["feature_version"])) != (f["definition_hash"], f["formula_hash"], f["graph_hash"])]
        add(JOINS[1], MISMATCH if bad else VERIFIED_AGAINST_REGISTRY, ",".join(bad) if bad else "equal to the SUPPLIED catalog snapshot (the snapshot itself is unadmitted)")
    j = joins.get("J3_BIND_TIME_HEALTH")
    if isinstance(j, dict) and ("ML_LOCAL_STATE" in j or "EVIDENCE_REFS" in j): add(JOINS[2], MISMATCH, "competing/plural/local-state field refused: one canonical EVIDENCE_REF only")
    elif not (isinstance(j, dict) and set(j) == {"EVIDENCE_REF"} and _s(j["EVIDENCE_REF"])): add(JOINS[2], MISSING if j is None else MISMATCH, "shape")
    else: add(JOINS[2], PRESENT_UNVERIFIED, "bind-time Health snapshot service instance unbound")
    j = joins.get("J4_GENERATION_COMPONENTS"); m = registry.manifest_of(j.get("manifest_id")) if isinstance(j, dict) and _s(j.get("manifest_id")) else None
    if j is None: add(JOINS[3], MISSING)
    elif m is None or not isinstance(j.get("components"), dict) or j.get("manifest_hash") != m.manifest_hash: add(JOINS[3], MISMATCH, "manifest unknown or hash differs")
    else:
        got = dict(m.components); miss = [n for n in MIN_COMPONENTS if n not in j["components"]]
        add(JOINS[3], MISMATCH if (miss or j["components"] != got) else VERIFIED_AGAINST_REGISTRY, ("missing:" + ",".join(miss)) if miss else ("component set/hashes differ" if j["components"] != got else ""))
    j = joins.get("J5_LIFECYCLE_LEDGER"); m = registry.manifest_of(j.get("manifest_id")) if isinstance(j, dict) and _s(j.get("manifest_id")) else None
    if j is None: add(JOINS[4], MISSING)
    elif m is None or j.get("manifest_hash") != m.manifest_hash or not _i(j.get("epoch")) or j["epoch"] > registry.epoch or not any(e.manifest_id == m.manifest_id and e.epoch <= j["epoch"] for e in registry.ledger()): add(JOINS[4], MISMATCH, "id/hash/epoch triple not in the ledger")
    else: add(JOINS[4], VERIFIED_AGAINST_REGISTRY, "epoch %d <= ledger epoch %d" % (j["epoch"], registry.epoch))
    j = joins.get("J6_RESEARCH_FAMILY_EXPOSURE"); keys = ("family_ref", "ledger_ref", "ledger_version", "ledger_hash", "consulted_available_asof")
    if not (isinstance(j, dict) and set(j) == set(keys) and all(_s(j[k]) for k in keys[:4]) and _i(j["consulted_available_asof"])): add(JOINS[5], MISSING if j is None else MISMATCH, "shape")
    elif j["consulted_available_asof"] >= fence: add(JOINS[5], MISMATCH, "consulted ledger AVAILABLE_ASOF not strictly before the fence")
    else: add(JOINS[5], PRESENT_UNVERIFIED, "exposure ledger instance unbound")
    extra = sorted(set(joins) - set(JOINS))
    if extra: raise Refusal(",".join(map(str, extra)), code="ML_JOINS_UNKNOWN_JOIN")
    corr = []
    j4, j5 = joins.get("J4_GENERATION_COMPONENTS"), joins.get("J5_LIFECYCLE_LEDGER")
    if isinstance(j4, dict) and isinstance(j5, dict):
        same = (j4.get("manifest_id"), j4.get("manifest_hash")) == (j5.get("manifest_id"), j5.get("manifest_hash"))
        corr.append(("J4_J5_SAME_GENERATION", VERIFIED_AGAINST_REGISTRY if same else MISMATCH, "" if same else "J4 components and J5 ledger name different manifest id/hash"))
    else: corr.append(("J4_J5_SAME_GENERATION", MISSING, "J4 or J5 absent"))
    if request_snapshot is not None:
        sn = registry.issued_snapshot(getattr(request_snapshot, "request_id", None))
        ok = sn is not None and sn == request_snapshot and isinstance(j4, dict) and (sn.manifest_id, sn.manifest_hash) == (j4.get("manifest_id"), j4.get("manifest_hash"))
        corr.append(("REQUEST_SNAPSHOT_SAME_GENERATION", VERIFIED_AGAINST_REGISTRY if ok else MISMATCH, "" if ok else "snapshot not issued by this registry, altered, or for a different manifest than J4"))
    else: corr.append(("REQUEST_SNAPSHOT_SAME_GENERATION", PRESENT_UNVERIFIED, "no request snapshot supplied"))
    corr.append(("J1_J2_J3_J6_TO_GENERATION", PRESENT_UNVERIFIED, "no source-defined key links the dataset manifest / feature set / Health / exposure ledger to a generation; not correlated, not invented"))
    return JoinReport(tuple(out), not any(s in (MISSING, MISMATCH) for _, s, _ in list(out) + corr), tuple(corr))
