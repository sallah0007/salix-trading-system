"""R53 independent row-step verification. Profile, reference step, codec, inputs are SIM / UNADMITTED test instances: no profile math or byte layout is claimed."""
import struct
import pytest
from stage_a.schema import objects as O, independent as X
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.verification import row_step_verifier as V
from stage_a.tracker.verification.verification_result import PASS, FAIL, INSUFFICIENT_EVIDENCE
from tests.trk_stage_a.test_r53_row_acceptance import rig, T, SCHEMA
from tests.trk_stage_a.test_r53_state_rows import H

XS = {"in0": 1.0, "in1": 2.0, "in2": 4.0}
def ref_step(prior, inputs):                              # independently written reference of the SIM declared program (acc += x; vec = [acc, 2*acc])
    acc = (0.0 if prior is None else prior["acc"]) + inputs["x"]; return {"acc": acc, "vec": [acc, acc * 2.0]}
def i_enc(st): return struct.pack(">3d", st["acc"], *st["vec"])
def i_dec(b):
    if len(b) != 24: raise ValueError("len")
    v = struct.unpack(">3d", b); return {"acc": v[0], "vec": [v[1], v[2]]}
def resolver(declared):
    return {"declared": [(r, h, XS[r.target_id.decode()]) for r, h in declared]}
def rh(row): return X.row_hash(RS.independent_dict(T, row), T.enums).hex()
def verify(row, pred, **kw):
    a = dict(row=row, predecessor=pred, schema=SCHEMA, reference_step=ref_step, decode=i_dec, encode=i_enc, resolve_inputs=resolver, input_symbols={"x": 0}, recompute_row_hash=rh, expect_row_hash=O.row_content_hash(T, row).hex())
    a.update(kw); return V.verify_row_step(**a)
def chain(): return [r for r, _ in rig()[3]]

def test_genuine_origin_and_successors_pass_with_complete_profile():
    rows = chain()
    for i, r in enumerate(rows):
        res = verify(r, None if i == 0 else rows[i - 1]); assert res.status == PASS and V.ROW_STEP_PROFILE <= {n for n, _ in res.checks}
        res.require_pass(V.SCOPE_ROW_STEP)
    assert dict(res.subject)["input_binding_limit"] == V.INPUT_VALUE_HASH_LIMIT

def test_wrong_successor_state_is_the_declared_program_failure_not_a_hash_failure():
    bad_step = lambda p, i: {"acc": (0.0 if p is None else p["acc"]) + 2 * i["x"], "vec": [0.0, 0.0]}   # a materializer that ran a DIFFERENT program
    s, js, store, out, _ = rig()
    # rebuild the chain with the wrong program through the real builder; its OWN hashes are all self-consistent
    from stage_a.tracker.materialization.state_rows import StateRowBuilder
    from tests.trk_stage_a.test_r53_row_acceptance import FX, kw
    from tests.trk_stage_a.test_r53_state_rows import enc, dec
    b = StateRowBuilder(SCHEMA, T, enc, dec, FX); r0 = b.step(bad_step, None, {"x": 1.0}, **kw(0, True))
    assert rh(r0) == O.row_content_hash(T, r0).hex()                                   # producer == independent hash: byte equality alone would pass this row
    res = verify(r0, None); assert res.status == FAIL and dict(res.checks)["successor_state_equals_reference"] is False and dict(res.checks)["row_hash_recomputed"] is True

def test_each_linkage_and_input_negative():
    rows = chain()
    assert verify(rows[1], None).status == FAIL                                        # successor presented without its predecessor
    assert verify(rows[2], rows[0]).status == FAIL                                     # wrong predecessor (step/hash gap)
    assert verify(rows[0], rows[0]).status == FAIL                                     # origin presented with a predecessor
    assert verify(rows[1], rows[0], expect_row_hash="ab" * 32).status == FAIL          # row hash not the claimed one
    foreign = O.PendingRow(**{**rows[1].__dict__, "feature_version": "other"}); assert verify(foreign, rows[0], expect_row_hash=rh(foreign)).status == FAIL
    wrong_in = lambda d: {"declared": [(r, h, 9.0) for r, h in d]}
    assert verify(rows[1], rows[0], resolve_inputs=wrong_in).status == FAIL            # actual inputs differ from what the row consumed
    echo_other = lambda d: {"declared": [(d[0][0], bytes(32), 2.0)]}
    assert verify(rows[1], rows[0], resolve_inputs=echo_other).status == FAIL          # input hash not the declared one
    assert verify(rows[1], rows[0], resolve_inputs=lambda d: None).status == INSUFFICIENT_EVIDENCE      # unreadable inputs are never PASS

def test_projection_and_state_tamper_and_noncanonical_predecessor():
    rows = chain()
    p = O.PendingRow(**{**rows[1].__dict__, "published_projection_bits": struct.pack(">d", 99.0)}); assert verify(p, rows[0], expect_row_hash=rh(p)).status == FAIL
    t = O.PendingRow(**{**rows[1].__dict__, "state_tuple": rows[1].state_tuple[:-1] + b"\x01"}); assert verify(t, rows[0], expect_row_hash=rh(t)).status == FAIL
    neg = O.PendingRow(**{**rows[0].__dict__, "state_tuple": rows[0].state_tuple[:8] + struct.pack(">d", -0.0) + rows[0].state_tuple[16:]})
    assert verify(rows[1], neg, expect_row_hash=O.row_content_hash(T, rows[1]).hex()).status == FAIL

def test_bad_schema_and_port_failures_fail_closed():
    rows = chain(); two = [dict(SCHEMA[0]), dict(SCHEMA[1], PUBLISHED=True)]
    assert verify(rows[0], None, schema=two).status == FAIL                            # projection rule undetermined
    assert verify(rows[0], None, schema=[]).status == FAIL
    assert verify(rows[0], None, schema=[dict(SCHEMA[0]), dict(SCHEMA[0])]).status == FAIL
    boom = lambda p, i: (_ for _ in ()).throw(RuntimeError("x"))
    assert verify(rows[0], None, reference_step=boom).status == FAIL
    nan = lambda p, i: {"acc": float("nan"), "vec": [1.0, 2.0]}
    assert verify(rows[0], None, reference_step=nan).status == FAIL

def test_failed_result_cannot_be_used_as_pass():
    rows = chain(); res = verify(rows[1], None)
    with pytest.raises(Exception): res.require_pass(V.SCOPE_ROW_STEP)

def _forge(row, **kw): return O.PendingRow(**{**row.__dict__, **kw})
def test_single_defect_isolation_step_index_predecessor_hash_and_noncanonical_predecessor():
    rows = chain()
    si = _forge(rows[1], step_index=5); res = verify(si, rows[0], expect_row_hash=rh(si))                  # ONLY the step index is wrong
    assert res.status == FAIL and dict(res.checks)["predecessor_linkage"] is False
    ph = _forge(rows[1], predecessor_row_hash=H); res = verify(ph, rows[0], expect_row_hash=rh(ph))        # ONLY the predecessor hash points elsewhere
    assert res.status == FAIL and dict(res.checks)["predecessor_linkage"] is False
    neg = _forge(rows[0], state_tuple=rows[0].state_tuple[:8] + struct.pack(">d", -0.0) + rows[0].state_tuple[16:])
    r1 = _forge(rows[1], predecessor_row_hash=bytes.fromhex(rh(neg)))                                       # successor correctly linked to the non-canonical predecessor
    res = verify(r1, neg, expect_row_hash=rh(r1)); assert res.status == FAIL and dict(res.checks)["predecessor_state_canonical"] is False

# ---- root findings: contradictory input carriers; schema mutated by a supplied callback ---------------------------------------------------------------
import copy
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from tests.trk_stage_a.test_r53_row_acceptance import FX, kw
from tests.trk_stage_a.test_r53_state_rows import _dyn_enc, _dyn_dec

def _built(schema, x, vec_len):
    b = StateRowBuilder(schema, T, _dyn_enc, _dyn_dec, FX)
    return b.step(lambda p, i: {"acc": i["x"], "vec": [i["x"]] * vec_len}, None, {"x": x}, **kw(0, True))
def _enc_d(st): return struct.pack(">%dd" % (1 + len(st["vec"])), st["acc"], *st["vec"])
def _dec_d(b): v = struct.unpack(">%dd" % (len(b) // 8), b); return {"acc": v[0], "vec": list(v[1:])}
def _ref_d(n): return lambda prior, inp: {"acc": inp["x"], "vec": [inp["x"]] * n}

def test_contradictory_input_value_carriers_cannot_pass_values_come_from_the_reread_payload():
    r = _built(SCHEMA, 9.0, 2)                                                           # the row consumed x=9.0 ...
    stored = {"in0": 1.0}                                                                # ... but the actual stored input payload is 1.0
    res = lambda d: {"declared": [(rf, h, stored[rf.target_id.decode()]) for rf, h in d], "values": {"x": 9.0}}     # a second, contradicting carrier
    out = verify(r, None, resolve_inputs=res, reference_step=_ref_d(2), decode=_dec_d, encode=_enc_d, input_symbols={"x": 0})
    assert out.status == FAIL and dict(out.checks)["successor_state_equals_reference"] is False
    ok = _built(SCHEMA, 1.0, 2); assert verify(ok, None, resolve_inputs=res, reference_step=_ref_d(2), decode=_dec_d, encode=_enc_d, input_symbols={"x": 0}).status == PASS     # genuine control

def test_symbol_mapping_is_supplied_never_guessed():
    r = chain()[0]
    held = verify(r, None, input_symbols=None); assert held.status == INSUFFICIENT_EVIDENCE and "input_symbol_mapping_not_supplied_held" in " ".join(held.reasons)
    for bad in ({}, {"x": 5}, {"x": True}, {"x": False}, {"x": -1}, {1: 0}, "x", {"x": 0.0}):
        assert verify(r, None, input_symbols=bad).status == FAIL, bad

def test_schema_cannot_be_changed_by_a_supplied_callback_after_validation():
    declared = copy.deepcopy(SCHEMA)                                                     # vector length 2 (private copy: the callback mutates it)
    s3 = copy.deepcopy(SCHEMA); s3[1]["SHAPE_DIMENSIONS"] = [3]; s3[1]["SHAPE_RANK"] = 1
    r3 = _built(s3, 1.0, 3)                                                              # a genuine, self-consistent row of the LENGTH-3 profile
    def evil_rh(row):
        declared[1]["SHAPE_DIMENSIONS"][0] = 3                                           # public alias of the ORIGINAL schema argument, changed mid-verification
        return X.row_hash(RS.independent_dict(T, row), T.enums).hex()
    res = verify(r3, None, schema=declared, recompute_row_hash=evil_rh, reference_step=_ref_d(3), decode=_dec_d, encode=_enc_d, resolve_inputs=lambda d: {"declared": [(rf, h, 1.0) for rf, h in d]})
    assert res.status == FAIL and dict(res.checks)["successor_state_equals_reference"] is False
    declared2 = copy.deepcopy(SCHEMA)                                                    # control: untouched length-2 declaration verifies a genuine length-2 row
    r2 = _built(SCHEMA, 1.0, 2); assert verify(r2, None, schema=declared2, reference_step=_ref_d(2), decode=_dec_d, encode=_enc_d, resolve_inputs=lambda d: {"declared": [(rf, h, 1.0) for rf, h in d]}).status == PASS
    # explicit NEW schema (length 3, new version) is a separate declaration and verifies the length-3 row on its own terms
    assert verify(r3, None, schema=s3, reference_step=_ref_d(3), decode=_dec_d, encode=_enc_d, resolve_inputs=lambda d: {"declared": [(rf, h, 1.0) for rf, h in d]}).status == PASS
