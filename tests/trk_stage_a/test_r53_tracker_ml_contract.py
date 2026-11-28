"""R53: Tracker REGISTRY section 14 p337-349 (13 Tracker->ML duties) checked against ACTUAL accepted manifests and ACTUAL accepted rows (real Rig/pipeline + CommittedRowChain + RowAcceptor); resolvers are the real readbacks. SIM identity_fn/eligibility policy are UNADMITTED test stand-ins; nothing here authorizes training."""
import dataclasses, hashlib, json
import pytest
from stage_a.errors import Refusal
from stage_a.ml import tracker_ml_contract as M
from stage_a.tracker import row_acceptance as RA, accepted_manifest as AM
from .test_r53_row_publication import rig
from .test_r53_row_acceptance import acc

def ident(body): return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()     # SIM identity rule (NOT a source rule)
def setup():
    r, fk, fj, path, rows, out, a, p = rig(); hs = [rc.row_hash for _, rc in out]
    for h in hs[:2]: acc(a, h)
    mh = AM.read_accepted_manifest(fj, r.store, fk).manifest_hash; row0 = out[0][0]
    def availability(h):
        j = r.journals.journal(RA.row_namespace(row0)); hit = [json.loads(x.body_json) for x in j.read_from(1) if json.loads(x.body_json)["row_content_hash"] == h] if j.head().seq else []
        return hit[-1]["available_asof"] if hit else None
    res = dict(accepted_hash=lambda fid, ver: mh if (fid, ver) == (fk.feature_id, fk.feature_version) else None, row_availability=availability,
               row_scope=lambda h: (rows.load(h).instrument_id.hex(), rows.load(h).timeframe_id.hex()), row_fit_ref=lambda h: None, eligible=lambda fid, ver, t: True, identity_fn=ident)
    m = M.FeatureViewManifest("fv-1", ((fk.feature_id, fk.feature_version, mh),), (("SRC/close", "ab" * 32),), "ORIGINAL_AS_OBSERVED", "tgt-1", "h-1", ("LBL/outcome",),
        (("train", 0, 100), ("validation", 100, 150), ("test", 150, 200)), (("w1", 0, 90),), (), (("standard-scaler", "scaler-1", "w1"),), 10_000, ((row0.instrument_id.hex(), row0.timeframe_id.hex()),),
        tuple((fk.feature_id, h) for h in hs[:2]), (), "")
    m = dataclasses.replace(m, replay_identity=ident(M._body(m))); st = M.FeatureViewStore({"ml-writer"}); st.register("ml-writer", m); return m, res, st, fk, hs, rows
def ev(m, res, st, **o): d = dict(res, store=st); d.update(o); return M.evaluate(m, **d)
def status(rep, p): return rep["duties"][p][1]

def test_all_thirteen_duties_pass_on_actual_objects_and_authorize_nothing():
    m, res, st, fk, hs, rows = setup(); rep = ev(m, res, st); assert [d[0] for d in M.DUTIES] == ["p%d" % i for i in range(337, 350)] and len(M.DUTIES) == 13
    assert rep["satisfied"] and all(v[1] == M.PASS for v in rep["duties"].values()) and "NOTHING" in rep["authorizes"]

def test_each_duty_fails_closed_on_its_own_defect_and_held_without_its_resolver():
    m, res, st, fk, hs, rows = setup(); R = dataclasses.replace; E = lambda mm, **o: ev(mm, res, st, **o)
    assert status(E(R(m, features=((fk.feature_id, fk.feature_version, "00" * 32),)), ), "p338") == M.FAIL                             # hash differs from the ACCEPTED manifest
    assert status(E(R(m, features=(("nope", "1", "aa"),))), "p338") == M.HELD                                                          # unresolved feature: HELD, not absent-is-fine
    assert status(E(R(m, sources=())), "p339") == M.FAIL and status(E(R(m, data_vintage_mode="")), "p339") == M.FAIL
    assert status(E(R(m, target_id="")), "p340") == M.FAIL and status(E(R(m, horizon_id="")), "p340") == M.FAIL
    assert status(E(R(m, label_sources=("SRC/close",))), "p341") == M.FAIL and status(E(R(m, label_sources=())), "p341") == M.FAIL        # label == feature source / none
    assert status(E(R(m, splits=(("train", 0, 100), ("validation", 90, 150), ("test", 150, 200)))), "p342") == M.FAIL                      # overlap
    assert status(E(R(m, splits=(("train", 0, 100), ("validation", 100, 150)))), "p342") == M.FAIL                                         # missing split
    assert status(E(R(m, fitting_windows=(("w1", 0, 120),))), "p343") == M.FAIL                                                           # silent holdout exposure
    assert status(E(R(m, fitting_windows=(("w1", 0, 120),), holdout_exposure=(("w1", "validation"),))), "p343") == M.PASS                  # RECORDED exposure is lineage, not silence
    assert status(E(R(m, holdout_exposure=(("w1", "validation"),))), "p343") == M.FAIL                                                    # an entry with no actual overlap
    assert status(E(R(m, transforms=(("standard-scaler", "scaler-1", "nowin"),))), "p344") == M.FAIL and status(E(R(m, transforms=())), "p344") == M.FAIL
    assert status(E(R(m, as_of_t=1)), "p345") == M.FAIL                                                                                   # rows accepted AFTER T
    assert status(E(R(m, rows=((fk.feature_id, hs[2]),))), "p345") == M.HELD                                                              # an UNACCEPTED row has no availability: HELD
    assert status(E(R(m, scope=(("00" * 16, "00" * 16),))), "p346") == M.FAIL
    assert status(E(m, eligible=lambda *a: False), "p347") == M.FAIL and status(E(m, eligible=lambda *a: (_ for _ in ()).throw(RuntimeError())), "p347") == M.FAIL
    assert status(E(m, eligible=lambda *a: 1), "p347") == M.FAIL and status(E(m, eligible=lambda *a: "yes"), "p347") == M.FAIL                    # only exactly True is eligible
    assert status(E(m, row_fit_ref=lambda h: "fit-gen-1"), "p348") == M.FAIL and status(E(R(m, learned_lineage=("fit-gen-1",)), row_fit_ref=lambda h: "fit-gen-1"), "p348") == M.PASS
    assert status(E(R(m, replay_identity="0" * 64)), "p349") == M.FAIL
    for p, kw in (("p338", "accepted_hash"), ("p345", "row_availability"), ("p346", "row_scope"), ("p347", "eligible"), ("p349", "identity_fn"), ("p348", "row_fit_ref")):
        rep = E(m, **{kw: None}); assert status(rep, p) == M.HELD and not rep["satisfied"], p                                                # no resolver/policy/hash rule => HELD, never PASS
    assert status(ev(m, res, None), "p337") == M.HELD

def test_manifest_is_immutable_write_once_needs_a_grant_and_the_reader_refuses_the_unrestricted_library():
    m, res, st, fk, hs, rows = setup()
    with pytest.raises(Refusal) as e: st.register("ml-writer", dataclasses.replace(m, target_id="other"))
    assert e.value.code == "FEATURE_VIEW_MANIFEST_IMMUTABLE" and st.get("fv-1") == m
    with pytest.raises(Refusal) as e: st.register("intruder", m)
    assert e.value.code == "ML_CALLER_NOT_GRANTED"
    with pytest.raises(Refusal) as e: M.FeatureViewStore().register("x", m)
    assert e.value.code == "ML_PRINCIPAL_GRANTS_UNBOUND_HELD"
    rd = M.FeatureViewReader(st, "fv-1", lambda fid, h: rows.load(h)); assert rd.read(fk.feature_id, hs[0]).step_index == 0
    for bad in ((fk.feature_id, hs[2]), ("other-feature", hs[0])):
        with pytest.raises(Refusal) as e: rd.read(*bad)
        assert e.value.code == "FEATURE_LIBRARY_ACCESS_OUTSIDE_VIEW"
    with pytest.raises(Refusal) as e: M.FeatureViewReader(st, "nope", None)
    assert e.value.code == "FEATURE_VIEW_NOT_REGISTERED"
