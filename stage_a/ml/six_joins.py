"""ML six-join candidate interface (A04 ML joins; Build Plan mapping/dependency disposition ML section; MLCore 28/31). Generic and source-backed: it checks that each of the six joins is PRESENT, well-shaped and - where an ML-owned registry instance
is supplied - EQUAL to that instance. Joins 4 and 5 are checked against the actual `GenerationRegistry` (manifest components / lifecycle ledger MANIFEST_ID, HASH, epoch). R46: when `consumed_features` (the consumer's ACTUAL included bindings + declared-applicable absences, exact id+version) is supplied, J2 must list every one of them: catalog membership of OTHER features proves nothing about THIS consumption; J2 entries beyond the consumed set are not refused (a dataset may list more; whether that is permitted is source-held).
Joins 1, 2, 3, 6 name instances this repository does not have
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

def check_six_joins(joins, registry, *, fence, catalog_snapshot=None, request_snapshot=None, dataset_manifests=None, binding_to_manifest=None, consumer_binding_id=None, family_map=None, hypothesis_family_id=None, consumed_features=None) -> JoinReport:
    """ML Integration Binding Addendum V1 s6: the dataset manifest does NOT carry a forward consumer-binding field (NOT_YET_NATIVE), so J1 is a REVERSE reference. R34: the relation is an EXPLICIT SUPPLIED resolver `binding_to_manifest` {binding_id: [manifest_id, ...]} (CONSUMER_BINDING.MANIFEST_OR_DATASET_BINDING_ID -> exact manifest); no identity equality between a binding id and a manifest id is assumed (the key may be indirect). J1 verifies only if the supplied `consumer_binding_id` equals J1.binding_id, the resolver maps it to EXACTLY ONE manifest id, that id is J1.dataset_manifest_id, and the SUPPLIED index `dataset_manifests` {manifest_id: hash} holds J1's hash for it. Absent, ambiguous or foreign relation -> not verified / MISMATCH. The J1 -> bind-time Health relation is NOT checked here. s4: a SUPPLIED `family_map` {hypothesis_family_id: research_family_id} must resolve `hypothesis_family_id` to exactly J6.family_ref. All supplied indexes are unadmitted."""
    if not isinstance(joins, dict): raise Refusal(type(joins).__name__, code="ML_JOINS_NOT_A_RECORD")
    if not _i(fence): raise Refusal("fence", code="ML_JOINS_FENCE_INVALID")
    out = []
    def add(j, st, d=""): out.append((j, st, d))
    j = joins.get("J1_DATASET_MANIFEST")
    if not (isinstance(j, dict) and set(j) == {"binding_id", "dataset_manifest_id", "dataset_manifest_hash"} and all(_s(v) for v in j.values())): add(JOINS[0], MISSING if j is None else MISMATCH, "shape")
    elif consumer_binding_id is not None and consumer_binding_id != j["binding_id"]: add(JOINS[0], MISMATCH, "J1 binding id differs from the consumer binding's MANIFEST_OR_DATASET_BINDING_ID")
    elif binding_to_manifest is not None and (consumer_binding_id is None or len(binding_to_manifest.get(consumer_binding_id, [])) != 1 or binding_to_manifest[consumer_binding_id][0] != j["dataset_manifest_id"]): add(JOINS[0], MISMATCH, "the supplied reverse relation does not resolve the consumer binding to exactly this dataset manifest (absent, ambiguous or foreign)")
    elif dataset_manifests is not None and dataset_manifests.get(j["dataset_manifest_id"]) != j["dataset_manifest_hash"]: add(JOINS[0], MISMATCH, "dataset manifest unknown in, or hash differs from, the SUPPLIED index")
    elif consumer_binding_id is not None and binding_to_manifest is not None and dataset_manifests is not None: add(JOINS[0], VERIFIED_AGAINST_REGISTRY, "reverse relation resolved the supplied consumer binding to exactly this manifest, hash equal in the SUPPLIED index (relation and index unadmitted; J1->Health not checked)")
    else: add(JOINS[0], PRESENT_UNVERIFIED, "reverse relation, dataset manifest index and/or consumer binding unbound")
    j = joins.get("J2_INCLUDED_FEATURES"); keys = ("feature_id", "feature_version", "definition_hash", "formula_hash", "graph_hash", "closure_ref")
    if not (isinstance(j, list) and j and all(isinstance(f, dict) and set(f) == set(keys) and all(_s(f[k]) for k in keys) for f in j)): add(JOINS[1], MISSING if j is None else MISMATCH, "shape")
    elif consumed_features is not None and (lambda miss: miss)(sorted(set(consumed_features) - {(f["feature_id"], f["feature_version"]) for f in j})):
        add(JOINS[1], MISMATCH, "J2 does not list the feature(s) this consumer ACTUALLY consumed (exact id+version): " + ",".join("%s/%s" % k for k in sorted(set(consumed_features) - {(f["feature_id"], f["feature_version"]) for f in j})))
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
    elif family_map is not None and (hypothesis_family_id is None or family_map.get(hypothesis_family_id) != j["family_ref"]): add(JOINS[5], MISMATCH, "hypothesis family does not resolve to exactly this research family in the SUPPLIED map")
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
