"""R53: the Tracker-side ML requirements of the Tracker REGISTRY section 14 (native Registry doc 1eZThdektQNUc5uCNOM96K_rquZYOBoPMonjI3kX4CHo, paragraphs 337-349: the THIRTEEN duties; p350 no unrestricted Feature Library access; p351 ML training is NOT authorized by this architecture;
p352 the dedicated Tracker->ML contract freeze is pending - not an authoring-permission withdrawal). Source-present duties are checked here against ACTUAL Tracker objects through SUPPLIED resolvers; governed INSTANCES (a manifest byte codec / hash rule, split vocabulary, eligibility policy) are HELD and never invented.
  p337 immutable manifest         `FeatureViewStore.register`: write-once by id; a different content under the same id refuses; no grant => HELD (no writer principal appointed)
  p338 exact feature ids/versions/hashes   each (feature_id, version, quant_manifest_hash) must equal the ACCEPTED manifest read back by `accepted_hash(id, ver)`; unresolved => HELD
  p339 source/dependency identities + data vintage   non-empty (ref, hash) pairs and a vintage mode; every declared source must be named by some feature's lineage when `lineage_of` is supplied
  p340 target/horizon identity    non-empty target id and horizon id
  p341 label/outcome separation   label sources are disjoint from the feature sources and feature ids
  p342 train/validation/test separation   three named half-open [start,end) intervals, pairwise DISJOINT (no ordering is asserted: none is source-defined)
  p343 fitting windows + holdout exposure lineage   every fitting window must be disjoint from validation and test, else the overlap must be recorded as an explicit exposure entry (never silent)
  p344 scaler/transform/imputer identities + fitting lineage   every transform names a declared fitting window
  p345 causal availability   every row's ACCEPTED available_asof (read back via `row_availability`) is <= as_of_T; unresolved => HELD
  p346 instrument/timeframe scope   the rows' scopes (via `row_scope`) must be within the declared scope
  p347 eligibility-as-of-T   a supplied `eligible(feature_id, version, as_of)` must return exactly True for every feature; absent => HELD (no policy defined)
  p348 learned-feature lineage   a row carrying a fit generation must have that exact ref in the manifest's learned lineage
  p349 replayable dataset identity   `identity_fn(manifest-without-identity)` must equal the declared replay identity; absent fn => HELD (no hash rule is defined)
Results per duty are PASS / FAIL / HELD; `satisfied` is True ONLY when all thirteen PASS. Satisfaction authorizes nothing (not training, not a gate); p350 is enforced by `FeatureViewReader` (undeclared feature => refuse). CANDIDATE, SIMULATION."""
import json
from dataclasses import dataclass
from ..errors import Refusal

PASS, FAIL, HELD = "PASS", "FAIL", "HELD"
DUTIES = (("p337", "IMMUTABLE_MANIFEST"), ("p338", "EXACT_FEATURE_IDS_VERSIONS_HASHES"), ("p339", "SOURCE_IDENTITIES_AND_VINTAGE"), ("p340", "TARGET_HORIZON_IDENTITY"), ("p341", "LABEL_OUTCOME_SEPARATION"), ("p342", "TRAIN_VALIDATION_TEST_SEPARATION"),
          ("p343", "FITTING_WINDOWS_HOLDOUT_EXPOSURE"), ("p344", "TRANSFORM_IDENTITIES_FITTING_LINEAGE"), ("p345", "CAUSAL_AVAILABILITY"), ("p346", "INSTRUMENT_TIMEFRAME_SCOPE"), ("p347", "ELIGIBILITY_AS_OF_T"), ("p348", "LEARNED_FEATURE_LINEAGE"), ("p349", "REPLAYABLE_DATASET_IDENTITY"))
def _s(x): return isinstance(x, str) and bool(x)

@dataclass(frozen=True)
class FeatureViewManifest:
    manifest_id: str; features: tuple          # ((feature_id, feature_version, quant_manifest_hash_hex), ...)
    sources: tuple; data_vintage_mode: str     # ((ref, hash), ...)
    target_id: str; horizon_id: str; label_sources: tuple
    splits: tuple                              # (("train", start, end), ("validation", ...), ("test", ...))
    fitting_windows: tuple                     # ((name, start, end), ...)
    holdout_exposure: tuple                    # ((window_name, split_name), ...) explicitly recorded overlaps
    transforms: tuple                          # ((kind, identity, fit_window_name), ...)
    as_of_t: int; scope: tuple                 # ((instrument_id_hex, timeframe_id_hex), ...)
    rows: tuple                                # ((feature_id, row_content_hash), ...) rows the view reads
    learned_lineage: tuple                     # (fit_generation_ref_str, ...)
    replay_identity: str

def _body(m): d = dict(m.__dict__); d.pop("replay_identity"); return d

class FeatureViewStore:
    def __init__(self, grants=None):
        self._m = {}; self._grants = None if grants is None else frozenset(grants)
        if self._grants is not None and not (self._grants and all(_s(g) for g in self._grants)): raise Refusal("grants", code="ML_PRINCIPAL_GRANTS_INVALID")
    def register(self, caller, m):
        if self._grants is None: raise Refusal("grants", code="ML_PRINCIPAL_GRANTS_UNBOUND_HELD")
        if caller not in self._grants: raise Refusal("caller", code="ML_CALLER_NOT_GRANTED")
        if not (isinstance(m, FeatureViewManifest) and _s(m.manifest_id)): raise Refusal("manifest", code="FEATURE_VIEW_MANIFEST_MALFORMED")
        old = self._m.get(m.manifest_id)
        if old is not None and old != m: raise Refusal(m.manifest_id, code="FEATURE_VIEW_MANIFEST_IMMUTABLE")
        self._m[m.manifest_id] = m; return m
    def get(self, mid): return self._m.get(mid)

def _ivs(m):
    """Return {name: (start, end)} or None when malformed."""
    out = {}
    for t in m.splits:
        if not (isinstance(t, tuple) and len(t) == 3 and _s(t[0]) and all(type(x) is int for x in t[1:]) and t[1] < t[2]) or t[0] in out: return None
        out[t[0]] = (t[1], t[2])
    return out if set(out) == {"train", "validation", "test"} else None
def _wins(m):
    out = {}
    for t in m.fitting_windows:
        if not (isinstance(t, tuple) and len(t) == 3 and _s(t[0]) and all(type(x) is int for x in t[1:]) and t[1] < t[2]) or t[0] in out: return None
        out[t[0]] = (t[1], t[2])
    return out
def _overlap(a, b): return a[0] < b[1] and b[0] < a[1]

def evaluate(m, *, accepted_hash=None, row_availability=None, row_scope=None, row_fit_ref=None, eligible=None, identity_fn=None, store=None):
    """Per-duty result dict {pNNN: (name, status, detail)} plus `satisfied`. Every resolver is SUPPLIED; None/unresolvable => HELD, never PASS."""
    r = {}
    def put(p, status, detail=""): r[p] = (dict(DUTIES)[p], status, detail)
    # p337
    if store is None: put("p337", HELD, "no FeatureViewStore supplied")
    else: put("p337", PASS if store.get(m.manifest_id) == m else FAIL, "registered write-once manifest equals this one")
    # p338
    ok = bool(m.features) and all(isinstance(f, tuple) and len(f) == 3 and all(_s(x) for x in f) for f in m.features)
    if not ok: put("p338", FAIL, "malformed or empty feature list")
    elif accepted_hash is None: put("p338", HELD, "accepted-manifest resolver not supplied")
    else:
        got = [accepted_hash(f[0], f[1]) for f in m.features]
        put("p338", HELD if any(g is None for g in got) else (PASS if all(g == f[2] for g, f in zip(got, m.features)) else FAIL), "each triple vs the ACCEPTED manifest read back")
    # p339
    ok = bool(m.sources) and all(isinstance(s, tuple) and len(s) == 2 and all(_s(x) for x in s) for s in m.sources) and _s(m.data_vintage_mode); put("p339", PASS if ok else FAIL, "sources (ref, hash) + vintage mode present")
    # p340
    put("p340", PASS if _s(m.target_id) and _s(m.horizon_id) else FAIL, "target and horizon identity")
    # p341
    fsrc = {s[0] for s in m.sources if isinstance(s, tuple) and s} | {f[0] for f in m.features if isinstance(f, tuple) and f}
    ok = bool(m.label_sources) and all(_s(x) for x in m.label_sources); put("p341", PASS if ok and not (fsrc & set(m.label_sources)) else FAIL, "label sources disjoint from feature sources/ids")
    # p342
    iv = _ivs(m)
    if iv is None: put("p342", FAIL, "splits must be exactly train/validation/test half-open intervals")
    else:
        names = sorted(iv); put("p342", FAIL if any(_overlap(iv[a], iv[b]) for i, a in enumerate(names) for b in names[i + 1:]) else PASS, "pairwise disjoint")
    # p343
    w = _wins(m)
    if iv is None or w is None: put("p343", FAIL, "fitting windows/splits malformed")
    else:
        rec = {x for x in m.holdout_exposure if isinstance(x, tuple)}
        bad = [(n, s) for n, win in w.items() for s in ("validation", "test") if _overlap(win, iv[s]) and (n, s) not in rec]
        stale = [x for x in rec if x[0] not in w or x[1] not in ("validation", "test") or not _overlap(w[x[0]], iv[x[1]])]
        put("p343", FAIL if bad or stale or not w else PASS, "unrecorded overlap=%s; exposure entries not matching an overlap=%s" % (bad, stale))
    # p344
    ok = w is not None and bool(m.transforms) and all(isinstance(t, tuple) and len(t) == 3 and all(_s(x) for x in t) and t[2] in w for t in m.transforms); put("p344", PASS if ok else FAIL, "each transform names a declared fitting window")
    # p345 / p346 / p348 over the ACTUAL rows
    rows = [x for x in m.rows if isinstance(x, tuple) and len(x) == 2]
    if len(rows) != len(m.rows) or not rows: put("p345", FAIL, "no rows"); put("p346", FAIL, "no rows"); put("p348", FAIL, "no rows")
    else:
        for p, fn, check in (("p345", row_availability, lambda v: type(v) is int and v <= m.as_of_t), ("p346", row_scope, lambda v: v in set(m.scope)), ("p348", row_fit_ref, lambda v: v is None or v in set(m.learned_lineage))):
            if fn is None: put(p, HELD, "resolver not supplied"); continue
            vals = [fn(x[1]) for x in rows]
            if p != "p348" and any(v is None for v in vals): put(p, HELD, "a row could not be resolved"); continue
            put(p, PASS if all(check(v) for v in vals) else FAIL, "over %d actual rows" % len(rows))
    if type(m.as_of_t) is not int: put("p345", FAIL, "as_of_T not an int")
    # p347
    if eligible is None: put("p347", HELD, "eligibility policy not supplied (none is defined)")
    else:
        try: ev = [eligible(f[0], f[1], m.as_of_t) for f in m.features]
        except Exception: ev = [None]
        put("p347", PASS if ev and all(v is True for v in ev) else FAIL, "each feature eligible as of T")
    # p349
    if identity_fn is None: put("p349", HELD, "no hash rule is defined; identity_fn not supplied")
    else:
        try: got = identity_fn(_body(m))
        except Exception: got = None
        put("p349", PASS if _s(got) and got == m.replay_identity else FAIL, "identity recomputed from the manifest body")
    return {"duties": r, "satisfied": all(v[1] == PASS for v in r.values()) and len(r) == 13, "authorizes": "NOTHING (p351: ML training is not authorized by this architecture)"}

class FeatureViewReader:
    """p350: no unrestricted Feature Library access - reads go through a registered manifest and only for the features/rows it declares."""
    def __init__(self, store, manifest_id, fetch):
        m = store.get(manifest_id)
        if m is None: raise Refusal(manifest_id, code="FEATURE_VIEW_NOT_REGISTERED")
        self._m, self._fetch = m, fetch
    def read(self, feature_id, row_hash):
        if (feature_id, row_hash) not in set(self._m.rows): raise Refusal(feature_id, code="FEATURE_LIBRARY_ACCESS_OUTSIDE_VIEW")
        return self._fetch(feature_id, row_hash)
