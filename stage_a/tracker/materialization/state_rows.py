"""GENERIC state-tuple + PendingRow production (R53). SOURCE (cited by role, not copied): Parent V1.2 generic model-profile / generic state contract
(fixed-shape scalar/vector/matrix components in canonical component order; restart ONLY from the exact prior committed tuple, never from a projection)
and Typed Annex V1.2 STATE_COMPONENTS / PENDING_ROW fields.
This is MECHANICS only. Everything the profile owns is SUPPLIED by the caller and nothing is defaulted or invented:
 - the state schema instance (validated by typed_shapes.validate_state_schema, reused),
 - the declared step function (the profile's math; tests pass SIM functions labelled unadmitted),
 - the STATE_TUPLE byte encoder/decoder (D13 byte layout is NOT admitted: refused when unbound; a round trip is enforced),
 - the CodeTables used for the row hash (candidate tables stay provisional) and every identity/version field.
NOT built here: model math, initialization rule, opcodes/grammar, commit-point id rule, clock, ceilings VALUES (caller supplies)."""
import copy, math, struct
from dataclasses import replace
from ...errors import Refusal
from ...composer.expression.typed_shapes import Typed, validate_state_schema, TYPES
from ...schema import objects as O

_FIXED = ("feature_id", "feature_version", "quant_manifest_hash", "instrument_id", "timeframe_id", "materialization_version",
          "state_schema_version", "logical_encoding_version", "arithmetic_contract_version", "fit_generation_ref", "step_class_ref",
          "speculation_mode", "materializer_implementation_id")

class StateTuple:
    """Values in the SUPPLIED schema's canonical component order (immutable)."""
    __slots__ = ("_items",)
    def __init__(self, items):
        object.__setattr__(self, "_items", tuple(items))
    def __setattr__(self, k, v): raise Refusal(k, code="STATE_TUPLE_IMMUTABLE")
    def __delattr__(self, k): raise Refusal(k, code="STATE_TUPLE_IMMUTABLE")
    @property
    def items(self): return self._items
    def as_dict(self): return {n: t for n, t in self._items}
    def _k(self): return tuple((n, t.kind, t.dims, t.data) for n, t in self._items)
    def __eq__(self, o): return isinstance(o, StateTuple) and self._k() == o._k()
    __hash__ = None

def build_state(schema, values):
    """schema: validate_state_schema() output. values: dict name -> raw float / list / nested list / Typed. Exact name set; each value rebuilt through Typed (finite, -0 -> +0, exact dims)."""
    names = [c["COMPONENT_NAME"] for c in schema]
    if not isinstance(values, dict) or set(values) != set(names) or len(values) != len(names):
        raise Refusal("%s" % sorted(map(str, values)) if isinstance(values, dict) else "values", code="STATE_VALUE_NAME_SET")
    out = []
    for c in schema:
        v = values[c["COMPONENT_NAME"]]
        if isinstance(v, Typed):
            if v.kind != c["COMPONENT_TYPE"] or v.dims != tuple(c["SHAPE_DIMENSIONS"]): raise Refusal(c["COMPONENT_NAME"], code="STATE_VALUE_SHAPE_MISMATCH")
            v = v.data
        out.append((c["COMPONENT_NAME"], Typed(c["COMPONENT_TYPE"], tuple(c["SHAPE_DIMENSIONS"]), v)))
    return StateTuple(out)

def projection_of(schema, state):
    """The ONLY projection this layer can derive without a profile rule: exactly one PUBLISHED component and it is a BINARY64_SCALAR. Anything else is undetermined -> refused."""
    pub = [c for c in schema if c["PUBLISHED"]]
    if len(pub) != 1 or pub[0]["COMPONENT_TYPE"] != "BINARY64_SCALAR": raise Refusal("%d published" % len(pub), code="PROJECTION_RULE_NOT_SUPPLIED")
    return pub[0]["COMPONENT_NAME"], struct.pack(">d", state.as_dict()[pub[0]["COMPONENT_NAME"]].data)

class StateRowBuilder:
    def __init__(self, components, tables, encode, decode, fixed, ceilings=None):
        self._schema = validate_state_schema(copy.deepcopy(components), ceilings)      # R53: detach from caller-owned (mutable, nested) profile data
        if not callable(encode) or not callable(decode): raise Refusal("encoder/decoder", code="STATE_TUPLE_CODEC_NOT_SUPPLIED")
        if not isinstance(fixed, dict) or set(fixed) != set(_FIXED): raise Refusal(sorted(fixed) if isinstance(fixed, dict) else "fixed", code="ROW_FIXED_FIELD_SET")
        self._t, self._enc, self._dec, self._fixed = copy.deepcopy(tables), encode, decode, copy.deepcopy(dict(fixed))

    def _encode(self, state):
        b = self._enc(state)
        if type(b) is not bytes: raise Refusal(type(b).__name__, code="STATE_TUPLE_ENCODER_RETURN")
        if build_state(self._schema, self._dec(b)) != state or self._enc(build_state(self._schema, self._dec(b))) != b:
            raise Refusal("round trip", code="STATE_TUPLE_CODEC_NOT_ROUNDTRIP")
        return b

    def decode_row_state(self, row):
        """Restart source: the exact prior committed tuple bytes of a row of THIS profile. The projection must agree with it (never the other way round)."""
        if not isinstance(row, O.PendingRow): raise Refusal(type(row).__name__, code="PRIOR_ROW_NOT_PENDING_ROW")
        for k in _FIXED:
            if getattr(row, k) != self._fixed[k]: raise Refusal(k, code="PRIOR_ROW_FOREIGN_PROFILE")
        st = build_state(self._schema, self._dec(row.state_tuple))
        if self._encode(st) != row.state_tuple: raise Refusal("bytes", code="PRIOR_STATE_NOT_CANONICAL")
        name, bits = projection_of(self._schema, st)
        if row.published_projection_name != name or row.published_projection_bits != bits: raise Refusal(name, code="PRIOR_PROJECTION_DISAGREES_WITH_TUPLE")
        return st

    def row_for(self, state, *, step_index, event_time, input_refs_and_hashes, predecessor=None, state_origin_ref=None, gate_dependency_hash=None):
        if type(step_index) is not int or step_index < 0 or type(event_time) is not int: raise Refusal("index/time", code="ROW_INDEX_OR_TIME_TYPE")
        if not isinstance(state, StateTuple): raise Refusal("state", code="STATE_NOT_STATE_TUPLE")
        pred_hash = None
        if predecessor is not None:
            self.decode_row_state(predecessor)
            if step_index != predecessor.step_index + 1: raise Refusal(str(step_index), code="STEP_INDEX_NOT_PREDECESSOR_PLUS_ONE")
            pred_hash = O.row_content_hash(self._t, predecessor)
        name, bits = projection_of(self._schema, state)
        row = O.PendingRow(**self._fixed, step_index=step_index, event_time=event_time, state_tuple=self._encode(state),
                           published_projection_name=name, published_projection_bits=bits, input_refs_and_hashes=tuple(input_refs_and_hashes),
                           predecessor_row_hash=pred_hash, state_origin_ref=state_origin_ref, gate_dependency_hash=gate_dependency_hash)
        O.row_content_bytes(self._t, row)                                # origin/gate/inputs presence rules
        return row

    def step(self, step_fn, predecessor, inputs, **row_kw):
        """Run the DECLARED (supplied) step function from the exact prior committed tuple (None only for an origin row) and produce the next row."""
        if not callable(step_fn): raise Refusal("step_fn", code="STEP_FUNCTION_NOT_SUPPLIED")
        prior = None if predecessor is None else self.decode_row_state(predecessor)
        new = build_state(self._schema, step_fn(None if prior is None else prior.as_dict(), inputs))
        return self.row_for(new, predecessor=predecessor, **row_kw)
