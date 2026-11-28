"""R53 per-row publication: ROW_ACCEPTED (real verifier-evidenced acceptance) -> derived SIM_STATUS_FACT -> StatusProjection -> Gateway. SIMULATION only; mapping/codec/clock/commit-point/profile UNADMITTED."""
import json, copy
import pytest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.schema.encoding import Ref
from stage_a.tracker import row_acceptance as RA, row_publication as RP
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from tests.trk_stage_a.test_r37_sim_publication_path import build, gw
from tests.trk_stage_a.test_boundaries import _entry, _health, I as BI
from tests.trk_stage_a.test_r53_row_acceptance import T, FX, CP, Time, kw, acc, evidence_for, SCHEMA, enc, dec, step_fn, H
from tests.trk_stage_a.test_r53_row_acceptance import R as _R
def R(n): return _R("SOURCE_OR_CAUSAL_POLICY_REF", n)

def rig():
    r, fk, fj, path, body = build(); fixed = dict(FX, feature_id=bytes(range(16, 32)), feature_version=fk.feature_version, quant_manifest_hash=bytes.fromhex(body["manifest_hash"]), instrument_id=BI, timeframe_id=BI, materialization_version="m1")
    rows = RS.PendingRowStore(r.store, T); ch = RS.CommittedRowChain(StateRowBuilder(SCHEMA, T, enc, dec, fixed), rows); out, ph = [], None
    for i, x in enumerate([1.0, 2.0, 4.0]):
        row, rc = ch.step(step_fn, ph, {"x": x}, **kw(i, origin=ph is None)); out.append((row, rc)); ph = rc.row_hash
    a = RA.RowAcceptor(r.journals, rows, T, Time(), CP()); return r, fk, fj, path, rows, out, a, RP.RowPublication(path, r.journals, rows, T, r.store)
def pub(p, fk, h, **o):
    d = dict(sequence=1, visible_at=500, published_projection_hash=H, data_vintage_mode="SIM_VINTAGE", source_or_causal_policy_ref=R("pol")); d.update(o); return p.publish(fk, h, "SIM_CUR", **d)
def codeof(f, *a, **k):
    with pytest.raises(Refusal) as e: f(*a, **k)
    return e.value.code

def test_accepted_row_publishes_derived_fields_and_delivers_through_the_gateway():
    r, fk, fj, path, rows, out, a, p = rig(); h0 = out[0][1].row_hash; rec = acc(a, h0); side = pub(p, fk, h0)
    b = json.loads(side.body_json); w = b["row"]
    assert w["available_asof"] == json.loads(rec.body_json)["available_asof"] and w["step_index"] == 0 and w["event_time"] == 1000 and b["origin"]["row_accepted_hash"] == rec.record_hash and b["origin"]["row_content_hash"] == h0
    assert w["canonical_transition_ref"][3] == json.loads(rec.body_json)["transition_hash"]                                    # the recomputed typed transition hash, not supplied
    proj = path.status_projection(); assert proj.authoritative and proj.simulation; g = gw(proj); assert path.feed(g) == 1
    assert pub(p, fk, h0) == side and len(path._sj.read_from(1)) == 1                                                            # replay: same record, nothing appended

def test_unaccepted_row_wrong_feature_binding_and_wrong_token_write_nothing():
    r, fk, fj, path, rows, out, a, p = rig(); h0, h1 = out[0][1].row_hash, out[1][1].row_hash; n = path._sj.head()
    assert codeof(pub, p, fk, h0) == "ROW_NOT_ACCEPTED"; acc(a, h0)
    import dataclasses; other = dataclasses.replace(fk, feature_version="99"); assert codeof(pub, p, other, h0) == "NO_ACCEPTED_RECORD"
    assert codeof(p.publish, fk, h0, "PUBLISHABLE", sequence=1, visible_at=5, published_projection_hash=H, data_vintage_mode="v", source_or_causal_policy_ref=R("pol")) == "SIM_PUBLICATION_INPUT_INVALID"   # never read as CURRENT
    assert path._sj.head() == n
    pub(p, fk, h0)
    assert codeof(p.publish, fk, h0, "SIM_OUT", sequence=2, visible_at=5, published_projection_hash=H, data_vintage_mode="v", source_or_causal_policy_ref=R("pol")) == "ROW_PUBLICATION_REPLAY_DIFFERS"

def test_row_bound_to_a_different_manifest_hash_is_refused():
    r, fk, fj, path, rows, out, a, p = rig()
    fixed = dict(FX, feature_id=bytes(range(16, 32)), feature_version=fk.feature_version, quant_manifest_hash=b"\x09" * 32, instrument_id=BI, timeframe_id=BI, materialization_version="m2")
    row, rc = RS.CommittedRowChain(StateRowBuilder(SCHEMA, T, enc, dec, fixed), rows).step(step_fn, None, {"x": 1.0}, **kw(0, origin=True)); acc(a, rc.row_hash)
    assert codeof(pub, p, fk, rc.row_hash) == "ROW_FEATURE_BINDING_MISMATCH" and path._sj.read_from(1) == []

def test_a_tampered_acceptance_record_is_refused_by_the_recomputed_transition_hash():
    r, fk, fj, path, rows, out, a, p = rig(); h0 = out[0][1].row_hash; rec = acc(a, h0); j = r.journals.journal(RA.row_namespace(out[0][0])); bad = json.loads(rec.body_json); bad["canonical_accepted_at"] += 1; bad["available_asof"] += 1
    j.append(j.head(), RA.KIND, dict(bad, row_content_hash=h0))                                                                  # a later forged duplicate for the SAME row (head record wins)
    assert codeof(pub, p, fk, h0) == "ROW_ACCEPTED_TRANSITION_HASH_MISMATCH" and path._sj.read_from(1) == []

def test_a_forged_record_that_is_internally_invalid_is_refused_typed():
    r, fk, fj, path, rows, out, a, p = rig(); h0 = out[0][1].row_hash; rec = acc(a, h0); j = r.journals.journal(RA.row_namespace(out[0][0])); bad = json.loads(rec.body_json); bad["canonical_accepted_at"] += 1
    j.append(j.head(), RA.KIND, bad); assert codeof(pub, p, fk, h0) == "ROW_ACCEPTED_TRANSITION_HASH_MISMATCH"                   # as-of != accepted-at is not a valid transition

def test_row_carrying_another_feature_version_than_the_accepted_one_is_refused():
    r, fk, fj, path, rows, out, a, p = rig()
    fixed = dict(FX, feature_id=bytes(range(16, 32)), feature_version="other-version", quant_manifest_hash=out[0][0].quant_manifest_hash, instrument_id=BI, timeframe_id=BI, materialization_version="m3")
    row, rc = RS.CommittedRowChain(StateRowBuilder(SCHEMA, T, enc, dec, fixed), rows).step(step_fn, None, {"x": 1.0}, **kw(0, origin=True)); acc(a, rc.row_hash)
    assert codeof(pub, p, fk, rc.row_hash) == "ROW_FEATURE_BINDING_MISMATCH" and path._sj.read_from(1) == []


# ---- R53 side-HEAD pinning: concurrent publishers (public ports; one-shot wrapper on the real path.commit) ------------------------------------------
from stage_a.errors import UnknownCommit
def two(rig_=None):
    r, fk, fj, path, rows, out, a, p1 = rig(); p2 = RP.RowPublication(path, r.journals, rows, T, r.store); return r, fk, path, rows, out, a, p1, p2
def race(path, hook):
    real = path.commit; state = {"armed": True}
    def wrapped(*a, **k):
        if state["armed"]: state["armed"] = False; hook()                                  # a concurrent publisher lands AFTER p1's preflight and BEFORE p1's real commit
        return real(*a, **k)
    path.commit = wrapped
def kws(**o):
    d = dict(sequence=1, visible_at=500, published_projection_hash=H, data_vintage_mode="SIM_VINTAGE", source_or_causal_policy_ref=R("pol")); d.update(o); return d
def n_side(path): return len(path._sj.read_from(1)) if path._sj.head().seq else 0

def test_concurrent_exact_replay_is_ONE_effect_returns_the_genuine_winner_and_the_cold_projection_is_authoritative():
    r, fk, path, rows, out, a, p1, p2 = two(); h0 = out[0][1].row_hash; acc(a, h0); won = {}
    race(path, lambda: won.setdefault("rec", p2.publish(fk, h0, "SIM_CUR", **kws())))
    rec = p1.publish(fk, h0, "SIM_CUR", **kws()); assert rec == won["rec"] and n_side(path) == 1
    assert [json.loads(x.body_json)["seq"] for x in path._sj.read_from(1)] == [1] and path.status_projection().authoritative                    # cold projection: no SEQUENCE_NOT_INCREASING

def test_a_different_row_taking_the_same_sequence_concurrently_is_refused_and_leaves_one_effect():
    r, fk, path, rows, out, a, p1, p2 = two(); h0, h1 = out[0][1].row_hash, out[1][1].row_hash; acc(a, h0); acc(a, h1)
    race(path, lambda: p2.publish(fk, h1, "SIM_CUR", **kws()))
    assert codeof(p1.publish, fk, h0, "SIM_CUR", **kws()) == "ROW_PUBLICATION_SEQUENCE_NOT_INCREASING" and n_side(path) == 1 and path.status_projection().authoritative
    assert codeof(p1.publish, fk, h0, "SIM_CUR", **kws(sequence=2)) == "ROW_PUBLICATION_ASOF_DECREASED" and n_side(path) == 1 and path.status_projection().authoritative   # the older accepted row cannot follow a newer one for the same MV (cold projection would refuse)

def test_an_unrelated_scope_does_not_conflict_with_a_concurrent_publication():
    r, fk, path, rows, out, a, p1, p2 = two(); h0 = out[0][1].row_hash; acc(a, h0)
    fixed = dict(FX, feature_id=bytes(range(16, 32)), feature_version=fk.feature_version, quant_manifest_hash=out[0][0].quant_manifest_hash, instrument_id=BI, timeframe_id=BI, materialization_version="m9")
    row, rc = RS.CommittedRowChain(StateRowBuilder(SCHEMA, T, enc, dec, fixed), rows).step(step_fn, None, {"x": 1.0}, **kw(0, origin=True)); acc(a, rc.row_hash)
    race(path, lambda: p2.publish(fk, rc.row_hash, "SIM_CUR", **kws()))
    p1.publish(fk, h0, "SIM_CUR", **kws()); assert n_side(path) == 2 and path.status_projection().authoritative                                  # different materialization version: both sequence 1 are lawful

def test_unknown_landed_is_found_as_the_replay_and_unknown_absent_is_retried():
    for landed in (True, False):
        r, fk, path, rows, out, a, p1, p2 = two(); h0 = out[0][1].row_hash; acc(a, h0); sj = path._sj; real = sj.append; st = {"n": 0}
        def append(*x, **y):
            st["n"] += 1
            if st["n"] == 1:
                if landed: real(*x, **y)
                raise UnknownCommit("ack lost" if landed else "dropped")
            return real(*x, **y)
        sj.append = append; rec = p1.publish(fk, h0, "SIM_CUR", **kws()); assert n_side(path) == 1 and path.status_projection().authoritative and json.loads(rec.body_json)["origin"]["row_content_hash"] == h0, landed

def test_the_stale_preflight_control_a_sequential_exact_replay_is_one_effect():
    r, fk, path, rows, out, a, p1, p2 = two(); h0 = out[0][1].row_hash; acc(a, h0); x = p1.publish(fk, h0, "SIM_CUR", **kws()); assert p2.publish(fk, h0, "SIM_CUR", **kws()) == x and n_side(path) == 1
