"""R53: the Tracker-side ML requirements of the Tracker REGISTRY section 14 (native Registry doc 1eZThdektQNUc5uCNOM96K_rquZYOBoPMonjI3kX4CHo, paragraphs 337-349: the THIRTEEN duties; p350 no unrestricted Feature Library access; p351 ML training is NOT authorized by this architecture;
p352 the dedicated Tracker->ML contract freeze is pending - not an authoring-permission withdrawal). Source-present duties are checked here against ACTUAL Tracker objects through SUPPLIED resolvers; governed INSTANCES (a manifest byte codec / hash rule, split vocabulary, eligibility policy) are HELD and never invented.
  p337 immutable manifest         `FeatureViewStore.register`: write-once by id; a different content under the same id refuses; no grant => HELD (no writer principal appointed)
  p338 exact feature ids/versions/hashes   each triple must equal the ACCEPTED manifest read back by `accepted_hash(id, ver)`; AND every row's feature must be declared and its ACTUAL owner (supplied subject-bound `row_owner(row_hash) -> (feature_id, version, hash)`) must be that declared triple; undeclared row feature => FAIL, unresolved => HELD
  p339 source/dependency identities + data vintage   shape alone is NOT a pass: PASS needs the supplied `lineage_of(feature_id, version)` relation and every source of each feature's actual lineage to be declared; absent => HELD
  p340 target/horizon identity    presence alone is HELD; PASS needs the supplied `target_known(target_id, horizon_id)` registry relation
  p341 label/outcome separation   disjoint from declared sources/ids (FAIL if not); PASS needs the features' ACTUAL lineage (`lineage_of`) to be disjoint too; else HELD
  p342 train/validation/test separation   CANDIDATE representation: three named half-open [start,end) intervals, pairwise DISJOINT (FAIL if not); PASS also needs the supplied governed `split_policy(splits) is True`, else HELD (no ordering/vocabulary is source-defined)
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
def _freeze(x):
    """Recursively detach a load-bearing value into immutable shapes: list/tuple -> tuple; str/int/bool/None unchanged. Anything else (dict, set, bytearray, objects...) is an UNSUPPORTED mutable/opaque shape and refuses: no silent aliasing of caller containers."""
    if isinstance(x, (list, tuple)): return tuple(_freeze(i) for i in x)
    if x is None or type(x) in (str, int, bool): return x
    raise Refusal(type(x).__name__, code="FEATURE_VIEW_UNSUPPORTED_SHAPE")

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
    def __post_init__(self):
        for k, v in list(self.__dict__.items()): object.__setattr__(self, k, _freeze(v))          # detached at CONSTRUCTION: a caller's list can no longer alias the stored manifest

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

def evaluate(m, *, accepted_hash=None, row_availability=None, row_scope=None, row_fit_ref=None, eligible=None, identity_fn=None, store=None, row_owner=None, lineage_of=None, target_known=None, split_policy=None):
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
        st = HELD if any(g is None for g in got) else (PASS if all(g == f[2] for g, f in zip(got, m.features)) else FAIL); why = "each triple vs the ACCEPTED manifest read back"
        declared = {f[0] for f in m.features}; rr = [x for x in m.rows if isinstance(x, tuple) and len(x) == 2]
        if any(x[0] not in declared for x in rr): st, why = FAIL, "a row names a feature that is not declared in features"                                           # internal: no resolver needed
        elif st == PASS:
            if row_owner is None: st, why = HELD, "row ownership resolver (subject-bound feature symbol/version/hash of the ACTUAL row) not supplied"
            else:
                try: own = [row_owner(x[1]) for x in rr]
                except Exception: own = [None]
                if not rr or any(o is None for o in own): st, why = HELD, "a row's owner could not be read back"
                elif any(not (isinstance(o, tuple) and len(o) == 3 and o in set(m.features) and o[0] == x[0]) for o, x in zip(own, rr)): st, why = FAIL, "a row's actual owner is not the declared feature/version/hash it is listed under"
                else: why += "; every row's ACTUAL owner is a declared (feature, version, hash)"
        put("p338", st, why)
    # p339
    ok = bool(m.sources) and all(isinstance(s, tuple) and len(s) == 2 and all(_s(x) for x in s) for s in m.sources) and _s(m.data_vintage_mode); lin = {}
    if not ok: put("p339", FAIL, "sources (ref, hash) / vintage mode malformed or empty")
    elif lineage_of is None: put("p339", HELD, "shape only: the features' actual source lineage relation (lineage_of) is not supplied, so declared sources are not tied to the features")
    else:
        try: lin = {f[:2]: lineage_of(f[0], f[1]) for f in m.features if isinstance(f, tuple) and len(f) == 3}
        except Exception: lin = {None: None}
        if not lin or any(v is None for v in lin.values()): put("p339", HELD, "a feature's source lineage could not be read back")
        else: put("p339", PASS if all(set(v) <= {x[0] for x in m.sources} for v in lin.values()) else FAIL, "every source in each feature's ACTUAL lineage is a declared source")
    # p340
    if not (_s(m.target_id) and _s(m.horizon_id)): put("p340", FAIL, "target/horizon id missing")
    elif target_known is None: put("p340", HELD, "presence only: no target/horizon identity registry supplied")
    else:
        try: tk = target_known(m.target_id, m.horizon_id)
        except Exception: tk = None
        put("p340", HELD if tk is None else (PASS if tk is True else FAIL), "target/horizon resolved against the supplied registry")
    # p341
    fsrc = {s[0] for s in m.sources if isinstance(s, tuple) and s} | {f[0] for f in m.features if isinstance(f, tuple) and f}
    ok = bool(m.label_sources) and all(_s(x) for x in m.label_sources)
    if not ok or (fsrc & set(m.label_sources)): put("p341", FAIL, "label sources missing or overlap the declared feature sources/ids")
    elif lineage_of is None or not lin or any(v is None for v in lin.values()): put("p341", HELD, "declared-only disjointness holds; the features' actual lineage (lineage_of) is not supplied")
    else: put("p341", PASS if not ({x for v in lin.values() for x in v} & set(m.label_sources)) else FAIL, "label sources disjoint from the ACTUAL lineage of every feature")
    # p342
    iv = _ivs(m)
    if iv is None: put("p342", FAIL, "splits must be exactly train/validation/test half-open intervals")
    else:
        names = sorted(iv); dis = not any(_overlap(iv[a], iv[b]) for i, a in enumerate(names) for b in names[i + 1:])
        if not dis: put("p342", FAIL, "intervals overlap")
        else:
            try: sp = None if split_policy is None else split_policy(m.splits)
            except Exception: sp = False
            put("p342", HELD if sp is None else (PASS if sp is True else FAIL), "CANDIDATE half-open interval representation, disjoint; the governed split vocabulary/representation (split_policy) %s" % ("is not supplied" if sp is None else "was applied"))
    # p343
    w = _wins(m)
    if iv is None or w is None: put("p343", FAIL, "fitting windows/splits malformed")
    else:
        rec = {x for x in m.holdout_exposure if isinstance(x, tuple)}
        bad = [(n, s) for n, win in w.items() for s in ("validation", "test") if _overlap(win, iv[s]) and (n, s) not in rec]
        stale = [x for x in rec if x[0] not in w or x[1] not in ("validation", "test") or not _overlap(w[x[0]], iv[x[1]])]
        put("p343", FAIL if bad or stale or not w else (PASS if r.get("p342", (0, 0))[1] == PASS else HELD), "unrecorded overlap=%s; exposure entries not matching an overlap=%s; PASS also needs the p342 representation bound" % (bad, stale))
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
    """p350: no unrestricted Feature Library access. A read is refused BEFORE any fetch unless (feature, row) is declared in the registered manifest AND the feature is one of its declared features; `row_owner` (SUPPLIED, subject-bound; None => every read HELD/refused)
    must then confirm the fetched/actual row's owner is that declared (feature, version, hash) - the symbolic-id vs row-byte-id mapping is the resolver's, never guessed here."""
    def __init__(self, store, manifest_id, fetch, row_owner=None):
        m = store.get(manifest_id)
        if m is None: raise Refusal(manifest_id, code="FEATURE_VIEW_NOT_REGISTERED")
        self._m, self._fetch, self._owner = m, fetch, row_owner
    def read(self, feature_id, row_hash):
        if (feature_id, row_hash) not in set(self._m.rows) or feature_id not in {f[0] for f in self._m.features}: raise Refusal(feature_id, code="FEATURE_LIBRARY_ACCESS_OUTSIDE_VIEW")        # before any fetch
        if self._owner is None: raise Refusal(feature_id, code="FEATURE_VIEW_ROW_OWNER_RESOLVER_HELD")
        own = self._owner(row_hash)
        if not (isinstance(own, tuple) and len(own) == 3 and own in set(self._m.features) and own[0] == feature_id): raise Refusal(feature_id, code="FEATURE_VIEW_ROW_NOT_OWNED_BY_DECLARED_FEATURE")
        return self._fetch(feature_id, row_hash)
