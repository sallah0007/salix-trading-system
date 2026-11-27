"""Typed objects and hash coverage from the frozen Annex (field names and orders as written there).
Producer-side composition: table-driven. The independent verifier re-implements composition separately."""
import hashlib
from dataclasses import dataclass, field, fields
from typing import Optional, Tuple
from ..errors import Refusal
from . import encoding as E
from .encoding import Ref, CodeTables

def sha256(b): return hashlib.sha256(b).digest()

# ---- keyed-list canonical ordering: ascending canonical bytes of the key; duplicates refused ------------------
def sort_keyed(pairs, what):
    """pairs = [(key_bytes, element)]; returns elements ascending by key bytes. Duplicate key -> Refusal."""
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise Refusal(what, code="DUPLICATE_KEY")
    return [e for _, e in sorted(pairs, key=lambda p: p[0])]

@dataclass(frozen=True)
class ProgramCapability:
    program_ref: Ref
    capability_class: str
    opcode_set_used: Tuple[int, ...]
    resource_ceiling_ref: Ref

@dataclass(frozen=True)
class QuantManifest:
    quant_manifest_schema_version: str; feature_id: bytes; feature_version: str
    model_profile_id: str; model_profile_version: str; state_schema_version: str; parameter_schema_version: str
    arithmetic_contract_version: str; logical_encoding_version: str; shared_evaluator_operator_set_version: str
    refit_mode: str; refit_rule_ref: Optional[Ref]; parameter_generation_source_ref: Optional[Ref]
    initialization_rule_set_ref: Ref; step_class_set_ref: Ref; step_classifier_ref: Ref
    input_dependencies: Tuple[Tuple[str, Ref], ...]
    transition_program_refs: Tuple[Tuple[str, Ref], ...]
    projection_program_refs: Tuple[Tuple[str, Ref], ...]
    invariant_program_refs: Tuple[Tuple[str, Ref], ...]
    published_projection_set_ref: Ref; verification_rule_set_ref: Ref; golden_vector_set_ref: Ref
    health_profile_ref: Ref; health_metric_program_refs: Tuple[Tuple[str, Ref], ...]
    program_capability_declarations: Tuple[ProgramCapability, ...]
    resource_ceiling_ref: Ref; data_vintage_policy_ref: Ref

def _validate_manifest(m: QuantManifest):
    if m.shared_evaluator_operator_set_version != "SQE_OPSET_V1_1":
        raise Refusal(m.shared_evaluator_operator_set_version, code="OPSET_NOT_SQE_OPSET_V1_1")
    scheduled = m.refit_mode == "SCHEDULED_REFIT"
    if scheduled != (m.refit_rule_ref is not None) or scheduled != (m.parameter_generation_source_ref is not None):
        raise Refusal("refit refs required iff SCHEDULED_REFIT", code="REFIT_REF_PRESENCE")
    for name in ("input_dependencies", "transition_program_refs", "projection_program_refs", "invariant_program_refs"):
        if not getattr(m, name):
            raise Refusal(name, code="REQUIRED_LIST_EMPTY")
    if not m.program_capability_declarations:
        raise Refusal("capability declarations", code="REQUIRED_LIST_EMPTY")
    for pc in m.program_capability_declarations:
        if list(pc.opcode_set_used) != sorted(set(pc.opcode_set_used)) or not pc.opcode_set_used:
            raise Refusal("opcode set must be ascending, unique, non-empty", code="OPCODE_SET_NOT_CANONICAL")

def manifest_bytes(t: CodeTables, m: QuantManifest) -> bytes:
    _validate_manifest(m)
    R = lambda r: E.ref(t, r)
    def keyed(lst_, keyname):
        pairs = [(E.version_id(k), E.version_id(k) + R(r)) for k, r in lst_]
        return E.lst(sort_keyed(pairs, keyname))
    caps = sort_keyed([(R(pc.program_ref), R(pc.program_ref) + E.enum(t, "PROGRAM_CAPABILITY_CLASS", pc.capability_class)
                        + E.lst([E.u16(c) for c in pc.opcode_set_used]) + R(pc.resource_ceiling_ref))
                       for pc in m.program_capability_declarations], "PROGRAM_CAPABILITY_DECLARATIONS")
    return b"".join([
        E.version_id(m.quant_manifest_schema_version), E.id128(m.feature_id), E.version_id(m.feature_version),
        E.version_id(m.model_profile_id), E.version_id(m.model_profile_version), E.version_id(m.state_schema_version),
        E.version_id(m.parameter_schema_version), E.version_id(m.arithmetic_contract_version),
        E.version_id(m.logical_encoding_version), E.version_id(m.shared_evaluator_operator_set_version),
        E.enum(t, "REFIT_MODE", m.refit_mode),
        E.optional(None if m.refit_rule_ref is None else R(m.refit_rule_ref)),
        E.optional(None if m.parameter_generation_source_ref is None else R(m.parameter_generation_source_ref)),
        R(m.initialization_rule_set_ref), R(m.step_class_set_ref), R(m.step_classifier_ref),
        keyed(m.input_dependencies, "INPUT_BINDING_NAME"), keyed(m.transition_program_refs, "STEP_CLASS_ID"),
        keyed(m.projection_program_refs, "PROJECTION_NAME"), keyed(m.invariant_program_refs, "INVARIANT_ID"),
        R(m.published_projection_set_ref), R(m.verification_rule_set_ref), R(m.golden_vector_set_ref),
        R(m.health_profile_ref), keyed(m.health_metric_program_refs, "METRIC_ID"),
        E.lst(caps), R(m.resource_ceiling_ref), R(m.data_vintage_policy_ref)])

def manifest_hash(t, m): return sha256(manifest_bytes(t, m))

@dataclass(frozen=True)
class PendingRow:
    feature_id: bytes; feature_version: str; quant_manifest_hash: bytes; instrument_id: bytes; timeframe_id: bytes
    materialization_version: str; step_index: int; event_time: int; state_schema_version: str
    logical_encoding_version: str; arithmetic_contract_version: str; state_tuple: bytes
    published_projection_name: str; published_projection_bits: bytes
    input_refs_and_hashes: Tuple[Tuple[Ref, bytes], ...]; fit_generation_ref: Optional[Ref]; step_class_ref: Ref
    predecessor_row_hash: Optional[bytes]; state_origin_ref: Optional[Ref]; speculation_mode: str
    gate_dependency_hash: Optional[bytes]; materializer_implementation_id: bytes

def _validate_row(r: PendingRow):
    if (r.predecessor_row_hash is None) == (r.state_origin_ref is None):
        raise Refusal("STATE_ORIGIN_REF required iff PREDECESSOR_ROW_HASH absent (and not otherwise)", code="ORIGIN_PRESENCE")
    if (r.speculation_mode == "GATED_ONE_STEP") != (r.gate_dependency_hash is not None):
        raise Refusal("GATE_DEPENDENCY_HASH required iff gated", code="GATE_PRESENCE")
    if not r.input_refs_and_hashes:
        raise Refusal("INPUT_REFS_AND_HASHES [1..N]", code="REQUIRED_LIST_EMPTY")

def row_content_bytes(t: CodeTables, r: PendingRow) -> bytes:
    _validate_row(r)
    inp = E.lst([E.ref(t, rf) + E.hash256(h) for rf, h in r.input_refs_and_hashes])   # declared order
    return b"".join([
        E.id128(r.feature_id), E.version_id(r.feature_version), E.hash256(r.quant_manifest_hash),
        E.id128(r.instrument_id), E.id128(r.timeframe_id), E.version_id(r.materialization_version),
        E.u64(r.step_index), E.timestamp_utc(r.event_time), E.version_id(r.state_schema_version),
        E.version_id(r.logical_encoding_version), E.version_id(r.arithmetic_contract_version),
        E.byte_string(r.state_tuple), E.version_id(r.published_projection_name),
        E.binary64_bits(r.published_projection_bits), inp,
        E.optional(None if r.fit_generation_ref is None else E.ref(t, r.fit_generation_ref)),
        E.ref(t, r.step_class_ref),
        E.optional(None if r.predecessor_row_hash is None else E.hash256(r.predecessor_row_hash)),
        E.optional(None if r.state_origin_ref is None else E.ref(t, r.state_origin_ref)),
        E.enum(t, "SPECULATION_MODE", r.speculation_mode),
        E.optional(None if r.gate_dependency_hash is None else E.hash256(r.gate_dependency_hash)),
        E.id128(r.materializer_implementation_id)])

def row_content_hash(t, r): return sha256(row_content_bytes(t, r))

@dataclass(frozen=True)
class CanonicalTransition:
    row_content_hash: bytes; verification_evidence_ref: Ref; sifp_fencing_epoch: int; canonical_commit_point_id: bytes
    canonical_accepted_at: int; available_asof: int; gate_dependency_transition_ref: Optional[Ref]
    currentness_state_at_acceptance: str; status_event: str

def transition_bytes(t: CodeTables, c: CanonicalTransition) -> bytes:
    if c.available_asof != c.canonical_accepted_at:
        raise Refusal("AVAILABLE_ASOF must equal CANONICAL_ACCEPTED_AT", code="ASOF_NOT_ACCEPTANCE_TIME")
    return b"".join([E.hash256(c.row_content_hash), E.ref(t, c.verification_evidence_ref), E.u64(c.sifp_fencing_epoch),
                     E.id128(c.canonical_commit_point_id), E.timestamp_utc(c.canonical_accepted_at),
                     E.timestamp_utc(c.available_asof),
                     E.optional(None if c.gate_dependency_transition_ref is None else E.ref(t, c.gate_dependency_transition_ref)),
                     E.enum(t, "CURRENTNESS_STATE", c.currentness_state_at_acceptance),
                     E.enum(t, "TRANSITION_STATUS_EVENT", c.status_event)])
def transition_hash(t, c): return sha256(transition_bytes(t, c))

@dataclass(frozen=True)
class StatusEvent:
    status_event_id: bytes; feature_version: str; instrument_id: bytes; timeframe_id: bytes; materialization_version: str
    mv_status_sequence: int; status_event_type: str
    effective_from: Tuple  # ("STEP", n) | ("INTERVAL", start, end_exclusive)
    reason_code: tuple; predecessor_or_successor_mv_ref: Optional[Ref]; available_asof: int; evidence_ref: Ref
    sifp_fencing_epoch: int; correction_marked: bool

def _effective(e):
    if e[0] == "STEP":
        return E.u8(1) + E.u64(e[1])
    if e[0] == "INTERVAL":
        if e[2] <= e[1]:
            raise Refusal("interval end must exceed start", code="BAD_INTERVAL")
        return E.u8(2) + E.u64(e[1]) + E.u64(e[2])
    raise Refusal(repr(e[0]), code="BAD_TAGGED_UNION")

def status_event_bytes(t: CodeTables, s: StatusEvent) -> bytes:
    return b"".join([E.id128(s.status_event_id), E.version_id(s.feature_version), E.id128(s.instrument_id),
                     E.id128(s.timeframe_id), E.version_id(s.materialization_version), E.u64(s.mv_status_sequence),
                     E.enum(t, "CHAIN_STATUS", s.status_event_type), _effective(s.effective_from),
                     E.tagged_enum_or_ref(t, s.reason_code),
                     E.optional(None if s.predecessor_or_successor_mv_ref is None else E.ref(t, s.predecessor_or_successor_mv_ref)),
                     E.timestamp_utc(s.available_asof), E.ref(t, s.evidence_ref), E.u64(s.sifp_fencing_epoch),
                     E.boolean(s.correction_marked)])
def status_event_hash(t, s): return sha256(status_event_bytes(t, s))

@dataclass(frozen=True)
class DeliveredFeatureEntry:
    feature_id: bytes; feature_version: str; quant_manifest_hash: bytes; instrument_id: bytes; timeframe_id: bytes
    materialization_version: str; step_index: int; event_time: int; logical_encoding_version: str
    published_projection_name: str; published_projection_bits: bytes; published_projection_hash: bytes
    fit_generation_ref: Optional[Ref]; data_vintage_mode: str; available_asof: int; chain_status_at_bind: str
    source_or_causal_policy_ref: Ref; bound_health_resolution_ref: Ref; bound_health_resolved_at: int
    canonical_transition_ref: Ref; omissions_exclusions_reason_codes: Tuple[tuple, ...]

def delivered_bytes(t: CodeTables, d: DeliveredFeatureEntry) -> bytes:
    return b"".join([E.id128(d.feature_id), E.version_id(d.feature_version), E.hash256(d.quant_manifest_hash),
                     E.id128(d.instrument_id), E.id128(d.timeframe_id), E.version_id(d.materialization_version),
                     E.u64(d.step_index), E.timestamp_utc(d.event_time), E.version_id(d.logical_encoding_version),
                     E.version_id(d.published_projection_name), E.binary64_bits(d.published_projection_bits),
                     E.hash256(d.published_projection_hash),
                     E.optional(None if d.fit_generation_ref is None else E.ref(t, d.fit_generation_ref)),
                     E.enum(t, "DATA_VINTAGE_MODE", d.data_vintage_mode), E.timestamp_utc(d.available_asof),
                     E.enum(t, "CHAIN_STATUS", d.chain_status_at_bind), E.ref(t, d.source_or_causal_policy_ref),
                     E.ref(t, d.bound_health_resolution_ref), E.timestamp_utc(d.bound_health_resolved_at),
                     E.ref(t, d.canonical_transition_ref),
                     E.lst([E.tagged_enum_or_ref(t, x) for x in d.omissions_exclusions_reason_codes])])
def delivered_hash(t, d): return sha256(delivered_bytes(t, d))
