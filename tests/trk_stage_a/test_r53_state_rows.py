"""R53 generic state-tuple / PendingRow production. All profiles, step functions and the byte codec here are SIM / UNADMITTED test fixtures:
no operational qualification and no normative payload (D13 byte layout is NOT admitted; the codec below is test-only)."""
import struct, math
import pytest
from stage_a.errors import Refusal
from stage_a.schema.encoding import CodeTables, Ref
from stage_a.schema import objects as O
from stage_a.tracker.materialization.state_rows import StateRowBuilder, build_state, StateTuple
from stage_a.composer.expression.typed_shapes import validate_state_schema

T = CodeTables(enums={"SPECULATION_MODE": {"NONE": 1, "GATED_ONE_STEP": 2}}, ref_types={"RULE": 1, "ROW": 2})
I = bytes(range(16)); H = bytes(range(32))
def R(n): return Ref("RULE", n.encode(), b"v1", None)
SCHEMA = [dict(COMPONENT_NAME="acc", COMPONENT_TYPE="BINARY64_SCALAR", SHAPE_RANK=0, SHAPE_DIMENSIONS=[], PUBLISHED=True),
          dict(COMPONENT_NAME="vec", COMPONENT_TYPE="FIXED_VECTOR_BINARY64", SHAPE_RANK=1, SHAPE_DIMENSIONS=[2], PUBLISHED=False)]
FIXED = dict(feature_id=I, feature_version="f1", quant_manifest_hash=H, instrument_id=I, timeframe_id=I, materialization_version="m1",
             state_schema_version="s1", logical_encoding_version="l1", arithmetic_contract_version="a1", fit_generation_ref=None,
             step_class_ref=R("sc"), speculation_mode="NONE", materializer_implementation_id=I)

def enc(st):                       # SIM codec (UNADMITTED): schema-order big-endian doubles, no framing
    d = st.as_dict(); return struct.pack(">d", d["acc"].data) + b"".join(struct.pack(">d", x) for x in d["vec"].data)
def dec(b):
    if len(b) != 24: raise Refusal("len", code="SIM_BAD_LEN")
    v = struct.unpack(">3d", b); return {"acc": v[0], "vec": [v[1], v[2]]}
def builder(**kw):
    a = dict(components=SCHEMA, tables=T, encode=enc, decode=dec, fixed=FIXED); a.update(kw); return StateRowBuilder(**a)
def step_fn(prior, inputs):        # SIM declared program: acc += x ; vec = [acc, acc*2]
    acc = (0.0 if prior is None else prior["acc"].data) + inputs["x"]
    return {"acc": acc, "vec": [acc, acc * 2]}
def kw(i, origin=False):
    return dict(step_index=i, event_time=1000 + i, input_refs_and_hashes=((Ref("ROW", b"in%d" % i), H),), **({"state_origin_ref": R("o")} if origin else {}))

def chain(b, xs):
    rows, prev = [], None
    for i, x in enumerate(xs):
        prev = b.step(step_fn, prev, {"x": x}, **kw(i, origin=prev is None)); rows.append(prev)
    return rows

def test_per_step_positive_values_and_chain():
    b = builder(); rows = chain(b, [1.0, 2.0, 4.0])
    assert [b.decode_row_state(r).as_dict()["acc"].data for r in rows] == [1.0, 3.0, 7.0]
    assert [r.step_index for r in rows] == [0, 1, 2]
    assert rows[1].predecessor_row_hash == O.row_content_hash(T, rows[0]) and rows[1].state_origin_ref is None
    assert rows[0].predecessor_row_hash is None and rows[0].state_origin_ref == R("o")
    assert struct.unpack(">d", rows[2].published_projection_bits)[0] == 7.0 and rows[2].published_projection_name == "acc"
    assert len({O.row_content_hash(T, r) for r in rows}) == 3

def test_restart_from_tuple_equals_uninterrupted_run():
    b = builder(); full = chain(b, [1.0, 2.0, 4.0, 8.0])
    restarted = builder()                                   # new builder, only the committed row survives
    nxt = restarted.step(step_fn, full[1], {"x": 4.0}, **kw(2)); nxt2 = restarted.step(step_fn, nxt, {"x": 8.0}, **kw(3))
    assert O.row_content_hash(T, nxt2) == O.row_content_hash(T, full[3])

def test_restart_never_from_projection():
    b = builder(); rows = chain(b, [1.0, 2.0])
    lie = O.PendingRow(**{**rows[1].__dict__, "published_projection_bits": struct.pack(">d", 99.0)})   # tuple says 3.0, projection says 99
    with pytest.raises(Refusal) as e: b.step(step_fn, lie, {"x": 1.0}, **kw(2))
    assert e.value.code == "PRIOR_PROJECTION_DISAGREES_WITH_TUPLE"

@pytest.mark.parametrize("bad", [
    {"acc": 1.0},                                        # missing component
    {"acc": 1.0, "vec": [1.0, 2.0], "extra": 3.0},      # foreign component
    {"acc": 1.0, "vec": [1.0]},                          # wrong shape
    {"acc": 1.0, "vec": [[1.0, 2.0]]},                   # wrong rank
    {"acc": float("nan"), "vec": [1.0, 2.0]},            # non-finite
    {"acc": 1.0, "vec": [float("inf"), 2.0]},
    {"acc": 1, "vec": [1.0, 2.0]},                       # int is not binary64
])
def test_wrong_shape_name_nonfinite_refused(bad):
    with pytest.raises(Refusal): builder().step(lambda p, i: bad, None, {"x": 1.0}, **kw(0, True))

def test_component_order_is_schema_order_not_dict_order():
    b = builder(); st = build_state(b._schema, {"vec": [5.0, 6.0], "acc": 4.0})
    assert [n for n, _ in st.items] == ["acc", "vec"] and enc(st) == struct.pack(">3d", 4.0, 5.0, 6.0)
    rev = validate_state_schema(list(reversed(SCHEMA)))          # different schema order => different tuple bytes
    assert enc(build_state(rev, {"vec": [5.0, 6.0], "acc": 4.0})).hex() != "" and [n for n, _ in build_state(rev, {"acc": 4.0, "vec": [5.0, 6.0]}).items] == ["vec", "acc"]

def test_foreign_profile_predecessor_refused():
    b = builder(); rows = chain(b, [1.0])
    for k, v in (("feature_version", "f2"), ("state_schema_version", "s2"), ("instrument_id", bytes(16)), ("materialization_version", "m2")):
        other = O.PendingRow(**{**rows[0].__dict__, k: v})
        with pytest.raises(Refusal) as e: b.step(step_fn, other, {"x": 1.0}, **kw(1))
        assert e.value.code == "PRIOR_ROW_FOREIGN_PROFILE"

def test_step_index_must_follow_predecessor_and_origin_xor_predecessor():
    b = builder(); rows = chain(b, [1.0])
    with pytest.raises(Refusal) as e: b.step(step_fn, rows[0], {"x": 1.0}, **kw(5))
    assert e.value.code == "STEP_INDEX_NOT_PREDECESSOR_PLUS_ONE"
    with pytest.raises(Refusal): b.step(step_fn, rows[0], {"x": 1.0}, **kw(1, origin=True))      # predecessor AND origin
    with pytest.raises(Refusal): b.step(step_fn, None, {"x": 1.0}, **kw(0))                       # neither

def test_codec_must_be_supplied_and_roundtrip():
    with pytest.raises(Refusal) as e: builder(encode=None)
    assert e.value.code == "STATE_TUPLE_CODEC_NOT_SUPPLIED"
    with pytest.raises(Refusal) as e: builder(encode=lambda st: bytearray(enc(st))).step(step_fn, None, {"x": 1.0}, **kw(0, True))
    assert e.value.code == "STATE_TUPLE_ENCODER_RETURN"
    lossy = lambda st: struct.pack(">d", st.as_dict()["acc"].data) + b"\0" * 16
    with pytest.raises(Refusal) as e: builder(encode=lossy).step(step_fn, None, {"x": 1.0}, **kw(0, True))
    assert e.value.code == "STATE_TUPLE_CODEC_NOT_ROUNDTRIP"

def test_non_canonical_prior_bytes_refused():
    b = builder(); rows = chain(b, [1.0])
    neg0 = rows[0].state_tuple[:8] + struct.pack(">d", -0.0) + rows[0].state_tuple[16:]      # -0.0 in an UNPUBLISHED component: projection still agrees
    bad = O.PendingRow(**{**rows[0].__dict__, "state_tuple": neg0})
    with pytest.raises(Refusal) as e: b.step(step_fn, bad, {"x": 1.0}, **kw(1))
    assert e.value.code == "PRIOR_STATE_NOT_CANONICAL"

def test_nondeterministic_encoder_refused():
    n = [0]
    def drift(st):                                  # same state, different bytes each call; decoder ignores the last byte
        n[0] += 1; return enc(st) + bytes([n[0] % 251])
    lenient = lambda b: dec(b[:24])
    with pytest.raises(Refusal) as e: builder(encode=drift, decode=lenient).step(step_fn, None, {"x": 1.0}, **kw(0, True))
    assert e.value.code == "STATE_TUPLE_CODEC_NOT_ROUNDTRIP"

def test_projection_rule_not_invented():
    two = [dict(SCHEMA[0]), dict(SCHEMA[1], PUBLISHED=True)]
    with pytest.raises(Refusal) as e: builder(components=two).step(step_fn, None, {"x": 1.0}, **kw(0, True))
    assert e.value.code == "PROJECTION_RULE_NOT_SUPPLIED"

def test_fixed_field_set_exact_and_step_fn_required():
    with pytest.raises(Refusal): builder(fixed={k: v for k, v in FIXED.items() if k != "feature_id"})
    with pytest.raises(Refusal): builder(fixed={**FIXED, "extra": 1})
    with pytest.raises(Refusal) as e: builder().step(None, None, {}, **kw(0, True))
    assert e.value.code == "STEP_FUNCTION_NOT_SUPPLIED"

def test_state_tuple_immutable_and_equality_by_value():
    b = builder(); s1 = build_state(b._schema, {"acc": 1.0, "vec": [1.0, 2.0]}); s2 = build_state(b._schema, {"acc": 1.0, "vec": [1.0, 2.0]})
    assert s1 == s2 and s1 != build_state(b._schema, {"acc": 2.0, "vec": [1.0, 2.0]})
    with pytest.raises(Refusal): s1.items = ()

def _xref(r): return (T.ref_types[r.ref_type], r.target_id, r.target_version, r.target_hash)
def _rowd(r):
    d = dict(r.__dict__); d["input_refs_and_hashes"] = tuple((_xref(a), h) for a, h in r.input_refs_and_hashes)
    for k in ("fit_generation_ref", "step_class_ref", "state_origin_ref"):
        d[k] = None if getattr(r, k) is None else _xref(getattr(r, k))
    d["speculation_mode"] = T.enums["SPECULATION_MODE"][r.speculation_mode]; return d

def test_independent_verifier_hash_equals_producer_for_every_built_row():
    from stage_a.schema import independent as X
    rows = chain(builder(), [1.0, 2.0, 4.0])
    for r in rows: assert X.row_hash(_rowd(r), T.enums) == O.row_content_hash(T, r)
    assert X.row_hash(_rowd(rows[2]), T.enums) != X.row_hash(_rowd(rows[1]), T.enums)
