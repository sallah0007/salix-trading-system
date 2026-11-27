"""R28: Contract V0.38 section X.1 closure object, candidate behaviour (provider/completeness witness stays held)."""
import dataclasses, pytest
from stage_a.ml import closure as CL
from stage_a.errors import Refusal

def N(i, t="FEATURE"): return CL.ClosureNode(i, t, "v1", "src:" + i)
def E(p, c, cls="FEATURE_DEPENDENCY", cc=True): return CL.ClosureEdge(p, c, cls, "ev:" + p + c, cc)
def rec(nodes=("S", "A", "B"), edges=None, **k):
    d = dict(closure_id="C1", subject_id="S", subject_type="ML_GENERATION", subject_version_or_hash="h", policy_id="P", policy_version="1", policy_hash="ph",
             nodes=tuple(N(n) for n in nodes), edges=tuple(edges if edges is not None else (E("A", "S"), E("B", "A"))), unresolved_edges=(), unknown_edge_types=(), missing_required_edges=(),
             closure_complete=True, fw_taint_present=False, fw_taint_source_ids=(), ml_fw_augmented_ancestry_present=False, admission_input_verdict="PASS", research_exposure_flags=(), computed_ts=5,
             resolver_id="R", resolver_version="1", resolver_hash="rh", final_closure_hash="fh"); d.update(k); return CL.ClosureRecord(**d)
def codeof(f, *a):
    try: f(*a)
    except Refusal as e: return e.code

def test_clean_union_closure_is_a_candidate_pass_never_qualified():
    v = CL.derive(rec()); assert v.verdict == "PASS" and v.reached == ("A", "B") and v.qualified is False and v.witness_status == CL.WITNESS_UNADMITTED
def test_transitive_ancestry_over_many_classes_is_walked_not_a_linear_chain():
    r = rec(nodes=("S", "M", "G", "D", "X"), edges=(E("M", "S", "LEARNED_DERIVED_MODEL_EDGE"), E("G", "M", "MODEL_GENERATION_INPUT_EDGE"), E("D", "G", "DATASET_SOURCE_EDGE"), E("X", "G", "CROSS_INSTRUMENT_EDGE")))
    assert CL.derive(r).reached == ("D", "G", "M", "X")
def test_neutral_shared_fact_and_unrelated_baseline_are_positive_controls():
    # B is consumed by FW elsewhere (a FW-side node exists in the set) but is not a taint source and no FW_PREDICTIVE_EDGE reaches S: no taint
    r = rec(nodes=("S", "A", "FWNODE", "OTHER"), edges=(E("A", "S"), E("A", "FWNODE", "FW_PREDICTIVE_EDGE")))
    assert CL.derive(r).verdict == "PASS"
def test_fw_predictive_edge_or_declared_taint_source_fails_closed():
    assert "FW_TAINT_REACHED" in CL.derive(rec(edges=(E("A", "S"), E("B", "A", "FW_PREDICTIVE_EDGE")))).reasons
    assert "FW_TAINT_REACHED" in CL.derive(rec(fw_taint_present=True, fw_taint_source_ids=("B",))).reasons
    v = CL.derive(rec(edges=(E("A", "S"), E("B", "A", "FW_PREDICTIVE_EDGE")), fw_taint_present=False)); assert "FW_TAINT_UNDECLARED" in v.reasons and "ASSERTED_PASS_CONTRADICTED_BY_DERIVATION" in v.reasons
def test_self_asserted_complete_true_does_not_override_missing_unknown_unresolved():
    for k in (dict(missing_required_edges=("X->S",)), dict(unresolved_edges=("Y",)), dict(unknown_edge_types=("Z",)), dict(closure_complete=False)):
        v = CL.derive(rec(**k)); assert v.verdict == "FAIL_CLOSED", k
def test_unknown_class_on_required_content_path_and_endpoint_missing_fail_closed():
    assert "UNKNOWN_EDGE_TYPE_ON_REQUIRED_PATH" in CL.derive(rec(edges=(E("A", "S", "UNKNOWN"),))).reasons
    assert "EDGE_CLASS_OUTSIDE_VOCABULARY" in CL.derive(rec(edges=(E("A", "S", "MY_NEW_CLASS"),))).reasons
    assert "EDGE_ENDPOINT_NOT_IN_NODE_SET" in CL.derive(rec(edges=(E("GHOST", "S"),))).reasons
    assert "SUBJECT_NOT_IN_NODE_SET" in CL.derive(rec(nodes=("A",), edges=())).reasons
def test_administrative_edge_gives_no_ancestry_but_cannot_claim_content():
    assert CL.derive(rec(edges=(E("A", "S", "ADMINISTRATIVE_NON_CONTENT_EDGE", False),))).reached == ()
    assert "ADMINISTRATIVE_EDGE_CLAIMS_CONTENT" in CL.derive(rec(edges=(E("A", "S", "ADMINISTRATIVE_NON_CONTENT_EDGE", True),))).reasons
def test_unrelated_unknown_edge_off_the_required_path_does_not_poison_the_baseline():
    r = rec(nodes=("S", "A", "Q", "R"), edges=(E("A", "S"), E("R", "Q", "UNKNOWN")))        # Q/R are not ancestors of S
    assert CL.derive(r).verdict == "PASS"
def test_malformed_or_absent_mandatory_fields_are_refused_not_judged():
    assert codeof(CL.derive, rec(closure_id="")) == "CLOSURE_MANDATORY_FIELD_MISSING"
    assert codeof(CL.derive, dataclasses.replace(rec(), closure_complete="yes")) == "CLOSURE_MANDATORY_BOOLEAN_MISSING"
    assert codeof(CL.derive, dataclasses.replace(rec(), edges=[E("A", "S")])) == "CLOSURE_MANDATORY_LIST_MISSING"
    assert codeof(CL.derive, rec(admission_input_verdict="OK")) == "CLOSURE_VERDICT_VOCABULARY"
    assert codeof(CL.derive, rec(fw_taint_present=True)) == "CLOSURE_TAINT_SOURCES_MANDATORY"
    assert codeof(CL.derive, rec(nodes=("S", "S"))) == "CLOSURE_NODE_DUPLICATE"
    assert codeof(CL.derive, "not a record") == "CLOSURE_NOT_A_CLOSURE_RECORD"

def test_ml_standalone_callpath_uses_the_derived_closure_and_never_qualifies():
    from stage_a.fw.lanes import ConsumerManifest as M
    from stage_a.ml import receiver as R
    Q = b"q"; g = {"m": M("m", "ML", (b"a",))}
    r = rec(subject_id="m", nodes=("m", "A"), edges=(E("A", "m"),))
    chk = R.check_standalone_with_closure(g["m"], Q, g, "ML_STANDALONE", r); assert chk.closure_verdict.verdict == "PASS" and chk.reached == ("A",)             # positive control
    with pytest.raises(Refusal) as e: R.require_standalone_qualified(chk)
    assert e.value.code == "UNION_CLOSURE_COMPLETENESS_UNPROVEN"                                                                                                  # witness unadmitted: still held
    bad = rec(subject_id="m", nodes=("m", "A"), edges=(E("A", "m"),), missing_required_edges=("X",))
    with pytest.raises(Refusal) as e: R.check_standalone_with_closure(g["m"], Q, g, "ML_STANDALONE", bad)
    assert e.value.code == "ML_STANDALONE_CLOSURE_FAIL_CLOSED"
    with pytest.raises(Refusal) as e: R.check_standalone_with_closure(g["m"], Q, g, "ML_STANDALONE", rec(subject_id="other", nodes=("other",), edges=()))
    assert e.value.code == "CLOSURE_SUBJECT_NOT_THIS_MANIFEST"
