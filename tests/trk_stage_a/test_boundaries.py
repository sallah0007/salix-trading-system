"""Verifier-side Annex checks, status/speculation machines, Q16 fairness, TR-15 isolation, and SIMULATED Gateway/FW/ML/Health/Context
boundary behaviour (G1-G9, OB1/OB2, F1-F6, M1-M4, Q17-Q23). Code tables are PROVISIONAL (D3). Nothing here touches a real Gateway/FW/ML."""
import ast, dataclasses, pathlib
import pytest
from stage_a.errors import Refusal
from stage_a.schema import objects as O, independent as X
from stage_a.schema.encoding import CodeTables, Ref
from stage_a.tracker import chain_status as C, speculation as S
from stage_a.gateway import contracts as G
from stage_a.fw import receiver as FW, lanes as L
from stage_a.ml import receiver as ML
from stage_a.health import evidence as HE
from stage_a.context import edge as CE
from stage_a.coordination.scheduler import ReplayScheduler
from stage_a.storage import keys

ENUMS = {"PROGRAM_CAPABILITY_CLASS": {"TRANSITION": 1}, "REFIT_MODE": {"NONE": 1}, "SPECULATION_MODE": {"OFF": 1, "GATED_ONE_STEP": 2},
         "CURRENTNESS_STATE": {"CURRENT": 1, "CATCHING_UP": 2}, "TRANSITION_STATUS_EVENT": {"ACCEPT": 1},
         "CHAIN_STATUS": {"CURRENT": 1, "CATCHING_UP": 2, "DEGRADED_NOT_CURRENT": 3, "HALTED": 4, "SUPERSEDED": 5},
         "DATA_VINTAGE_MODE": {"ORIGINAL_AS_OBSERVED": 1, "EVENTUAL": 2}, "REASON": {"NONE": 1}}
T = CodeTables(enums=ENUMS, ref_types={"R": 1})
H = bytes(range(32)); I = bytes(range(16)); J = bytes(range(16, 32)); BITS = b"\0" * 7 + b"\1"
def R(n, h=None): return Ref("R", n.encode(), b"v", h)
def code(n, s): return ENUMS[n][s]
def xref(r): return (1, r.target_id, r.target_version, r.target_hash)

# ---------- verifier-side (independent) composition -------------------------------------------------------------------
def row(**kw):
    b = dict(feature_id=I, feature_version="f1", quant_manifest_hash=H, instrument_id=I, timeframe_id=I, materialization_version="m1",
             step_index=3, event_time=10, state_schema_version="s", logical_encoding_version="l", arithmetic_contract_version="a",
             state_tuple=b"x", published_projection_name="p", published_projection_bits=BITS, input_refs_and_hashes=((R("i"), H),),
             fit_generation_ref=R("fit"), step_class_ref=R("sc"), predecessor_row_hash=H, state_origin_ref=None,
             speculation_mode="OFF", gate_dependency_hash=None, materializer_implementation_id=I)
    b.update(kw); return O.PendingRow(**b)
def rowd(r):
    d = dataclasses.asdict(r)
    d["input_refs_and_hashes"] = [(xref(a), h) for a, h in r.input_refs_and_hashes]
    for k in ("fit_generation_ref", "step_class_ref", "state_origin_ref"):
        d[k] = None if getattr(r, k) is None else xref(getattr(r, k))
    d["speculation_mode"] = code("SPECULATION_MODE", r.speculation_mode)
    return d

def test_independent_row_hash_equals_producer():
    for r in (row(), row(predecessor_row_hash=None, state_origin_ref=R("o")), row(speculation_mode="GATED_ONE_STEP", gate_dependency_hash=H),
              row(fit_generation_ref=None, input_refs_and_hashes=((R("a"), H), (R("b", H), J * 2)))):
        assert X.row_hash(rowd(r), ENUMS) == O.row_content_hash(T, r)

def test_independent_row_refuses_what_producer_refuses():
    bad = rowd(row()); bad["state_origin_ref"] = xref(R("o"))
    with pytest.raises(ValueError): X.row_hash(bad, ENUMS)

def test_independent_transition_status_delivered_hashes():
    c = O.CanonicalTransition(H, R("v"), 2, I, 5, 5, None, "CURRENT", "ACCEPT")
    cd = dict(row_content_hash=H, verification_evidence_ref=xref(R("v")), sifp_fencing_epoch=2, canonical_commit_point_id=I,
              canonical_accepted_at=5, available_asof=5, gate_dependency_transition_ref=None,
              currentness_state_at_acceptance=1, status_event=1)
    assert X.transition_hash(cd, ENUMS) == O.transition_hash(T, c)
    s = O.StatusEvent(I, "f1", I, I, "m1", 1, "CURRENT", ("INTERVAL", 2, 9), ("ENUM", "REASON", "NONE"), R("p"), 7, R("e"), 2, True)
    sd = dict(status_event_id=I, feature_version="f1", instrument_id=I, timeframe_id=I, materialization_version="m1", mv_status_sequence=1,
              status_event_type=1, effective_from=("INTERVAL", 2, 9), reason_code=("ENUM", "REASON", 1), predecessor_or_successor_mv_ref=xref(R("p")),
              available_asof=7, evidence_ref=xref(R("e")), sifp_fencing_epoch=2, correction_marked=True)
    assert X.status_event_hash(sd, ENUMS) == O.status_event_hash(T, s)
    d = _delivered()
    dd = dataclasses.asdict(d)
    for k in ("fit_generation_ref", "source_or_causal_policy_ref", "bound_health_resolution_ref", "canonical_transition_ref"):
        dd[k] = None if getattr(d, k) is None else xref(getattr(d, k))
    dd["data_vintage_mode"] = 1; dd["chain_status_at_bind"] = 1
    dd["omissions_exclusions_reason_codes"] = [("ENUM", "REASON", 1), ("REF", xref(R("why")))]
    d2 = dataclasses.replace(d, omissions_exclusions_reason_codes=(("ENUM", "REASON", "NONE"), ("REF", R("why"))))
    assert X.delivered_hash(dd, ENUMS) == O.delivered_hash(T, d2)

def _delivered(**kw):
    b = dict(feature_id=I, feature_version="f1", quant_manifest_hash=H, instrument_id=I, timeframe_id=I, materialization_version="m1",
             step_index=3, event_time=10, logical_encoding_version="l", published_projection_name="p", published_projection_bits=BITS,
             published_projection_hash=H, fit_generation_ref=R("fit"), data_vintage_mode="ORIGINAL_AS_OBSERVED", available_asof=4,
             chain_status_at_bind="CURRENT", source_or_causal_policy_ref=R("pol"), bound_health_resolution_ref=R("hl"),
             bound_health_resolved_at=4, canonical_transition_ref=R("ct"), omissions_exclusions_reason_codes=())
    b.update(kw); return O.DeliveredFeatureEntry(**b)

def test_verifier_module_is_structurally_independent():
    src = pathlib.Path(X.__file__).read_text()
    tree = ast.parse(src)
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods <= {"hashlib"}, mods
    assert "struct" not in src.replace('"""', "").split("import hashlib")[1]

# ---------- status machine (Q22) --------------------------------------------------------------------------------------
MV = (I, "f1", I, I, "m1")
def F(seq, st, asof, corr=False, des=False): return C.StatusFact(MV, seq, st, asof, corr, des)

def test_status_basic_rules():
    a = C.ChainStatusAuthority(); a.append(F(1, C.CATCHING_UP, 1))
    with pytest.raises(Refusal): a.append(F(1, C.CURRENT, 2, des=True))            # sequence must increase
    with pytest.raises(Refusal): a.append(F(2, C.CURRENT, 2))                      # needs designation
    with pytest.raises(Refusal): a.append(F(2, C.CURRENT, 0, des=True))            # asof decreased
    a.append(F(2, C.CURRENT, 2, des=True))
    with pytest.raises(Refusal): a.append(F(3, C.DEGRADED, 3, des=True))           # designation only for CATCHING_UP->CURRENT

def test_halted_terminal_and_correction_monotone():
    a = C.ChainStatusAuthority(); a.append(F(1, C.CURRENT, 1)); a.append(F(2, C.DEGRADED, 2, corr=True))
    with pytest.raises(Refusal): a.append(F(3, C.CURRENT, 3, corr=True))           # CURRENT invalid after correction
    with pytest.raises(Refusal): a.append(F(3, C.CATCHING_UP, 3, corr=False))      # true -> false
    a.append(F(3, C.HALTED, 3, corr=True))
    with pytest.raises(Refusal): a.append(F(4, C.CURRENT, 4))
    with pytest.raises(Refusal): a.append(F(4, C.SUPERSEDED, 4, corr=True))        # HALTED terminal

def test_status_visibility_is_half_open():
    a = C.ChainStatusAuthority(); a.append(F(1, C.CURRENT, 5))
    assert a.status_at(MV, 5) is None and a.status_at(MV, 6).status == C.CURRENT
    with pytest.raises(Refusal): a.append(C.StatusFact(MV, 2, "BOGUS", 6, False))

# ---------- speculation (Q21) -----------------------------------------------------------------------------------------
def test_speculation_depth_rules():
    k = {}
    k["a"] = S.admit(S.StagedCandidate("a", S.CANONICAL_ONLY, 0), k)
    k["b"] = S.admit(S.StagedCandidate("b", S.ONE_HOP, 1, ("a",)), k)
    with pytest.raises(Refusal): S.admit(S.StagedCandidate("c", S.ONE_HOP, 1, ("b",)), k)           # depth>1 closure
    with pytest.raises(Refusal): S.admit(S.StagedCandidate("d", S.ONE_HOP, 0, ("a",)), k)           # understated depth
    with pytest.raises(Refusal): S.admit(S.StagedCandidate("e", S.ONE_HOP, 1, ("zzz",)), k)         # unknown source
    with pytest.raises(Refusal): S.admit(S.StagedCandidate("f", S.CANONICAL_ONLY, 0, ("a",)), k)
    with pytest.raises(Refusal): S.admit(S.StagedCandidate("g", S.CANONICAL_ONLY, 2), k)
    with pytest.raises(Refusal): S.admit(S.StagedCandidate("h", S.ONE_HOP, 1, ("a",), ), {"a": S.StagedCandidate("a", S.CANONICAL_ONLY, 0, (), False)})
    assert S.effective_depth("b", k) == 1 and S.effective_depth("a", k) == 0

# ---------- Q16 fairness ----------------------------------------------------------------------------------------------
def test_replay_storm_does_not_starve_unrelated_head():
    pend = {"storm%02d" % i: list(range(50)) for i in range(20)}; pend["live"] = ["head"]
    batches = ReplayScheduler(max_total=2000, max_batch=5).plan(pend)
    flat = [ns for b in batches for ns, _ in b]
    assert flat.index("live") == 0 and flat[:21] == sorted(set(flat))   # unrelated head served first, deterministic order
    counts = {}
    for ns in flat[:210]:
        counts[ns] = counts.get(ns, 0) + 1
    storm = [v for k, v in counts.items() if k != "live"]
    assert max(storm) - min(storm) <= 1
    with pytest.raises(Refusal): ReplayScheduler(10, 5).plan({"a": list(range(11))})

# ---------- TR-15 isolation -------------------------------------------------------------------------------------------
def test_instrument_isolation_keys_status_and_gateway():
    assert keys.head_key("XAUUSD/f1") != keys.head_key("EURUSD/f1")
    st = C.ChainStatusAuthority(); gw = G.SimulatedGateway(T, st, allow_uncommitted_status=True, watermark=100)
    mvx = (I, "f1", I, I, "m1"); mve = (I, "f1", J, I, "m1")
    st.append(C.StatusFact(mvx, 1, C.CURRENT, 1, False)); st.append(C.StatusFact(mve, 1, C.CURRENT, 1, False))
    gw.publish(_row(instr=I)); gw.publish(_row(instr=J))
    st.append(C.StatusFact(mvx, 2, C.HALTED, 2, True))                                    # XAUUSD halted
    assert gw.resolve("rx", _entry(), I, I, 3, 50, _health(), True).reason.startswith("CHAIN_STATUS_NOT_CURRENT")
    assert isinstance(gw.resolve("re", _entry(), J, I, 3, 50, _health(), True), G.Binding)  # EURUSD unaffected
    r = gw.resolve("rw", _entry(), bytes(16), I, 3, 50, _health())                        # unknown instrument: nothing leaks
    assert isinstance(r, G.NonDeliveryResolution) and r.reason == "REQUIRED_DEPENDENCY_ABSENT"

# ---------- simulated Gateway (G1-G9, OB1/OB2) ------------------------------------------------------------------------
def _entry(opt=False, fid=I, ver="f1"):
    return G.DependencyEntry(fid, ver, G.OPTIONAL if opt else G.REQUIRED, "p", R("sc"), R("tc"), R("vp"), R("hr"), R("abs") if opt else None)
def _health(ok=True, at=4): return G.HealthSnapshot(R("hl"), at, ok)
def _row(instr=I, fid=I, avail=4, visible=4, step=3, vint="ORIGINAL_AS_OBSERVED", ver="f1"):
    return G.PublishedRow(fid, ver, H, instr, I, "m1", step, 10, "l", "p", BITS, H, R("fit"), vint, avail, visible, R("pol"), R("ct"))
def _gw(status=C.CURRENT, mvfid=I, **rowkw):
    st = C.ChainStatusAuthority(); st.append(C.StatusFact((mvfid, rowkw.get("ver", "f1"), I, I, "m1"), 1, status, 1, False))
    gw = G.SimulatedGateway(T, st, allow_uncommitted_status=True, watermark=100); gw.publish(_row(**rowkw)); return gw

def test_g1_equality_at_fence_excluded_and_ob1_positive_control():
    gw = _gw(avail=10)
    assert gw.resolve("a", _entry(), I, I, 3, 10, _health()).reason == "NOT_AVAILABLE_BEFORE_FENCE"
    assert isinstance(_gw(avail=9).resolve("b", _entry(), I, I, 3, 10, _health()), G.Binding)     # OB1: eligible is not refused

def test_g2_late_visibility_is_classified_not_widened():
    assert _gw(avail=4, visible=12).resolve("a", _entry(), I, I, 3, 10, _health()).reason == "LATE_VISIBILITY"

def test_g3_missing_required_structured_nondelivery_and_g9_optional():
    gw = _gw()
    assert gw.resolve("a", _entry(fid=J), I, I, 3, 10, _health()).reason == "REQUIRED_DEPENDENCY_ABSENT"
    o = gw.resolve("b", _entry(opt=True, fid=J), I, I, 3, 10, _health())
    assert isinstance(o, G.AbsenceApplied) and o.absence_handling_applied_ref == R("abs")
    with pytest.raises(Refusal): G.DependencyEntry(I, "f1", G.OPTIONAL, "p", R("a"), R("b"), R("c"), R("d"))        # rule required iff OPTIONAL
    with pytest.raises(Refusal): G.DependencyEntry(I, "f1", G.REQUIRED, "p", R("a"), R("b"), R("c"), R("d"), R("x"))

def test_g4_retry_identical_and_g5_late_dependency_cannot_mutate():
    gw = _gw(avail=9)
    first = gw.resolve("a", _entry(), I, I, 3, 10, _health())
    gw.publish(_row(avail=5, step=3))                                         # later arrival
    assert gw.resolve("a", _entry(), I, I, 3, 10, _health()) is first
    miss = _gw(); n = miss.resolve("b", _entry(fid=J), I, I, 3, 10, _health())
    miss.publish(_row(fid=J)); assert miss.resolve("b", _entry(fid=J), I, I, 3, 10, _health()) is n

def test_g6_bind_time_health_snapshot_immutable_and_hash_covers_it():
    gw = _gw(avail=9); b = gw.resolve("a", _entry(), I, I, 3, 10, _health())
    h2 = dataclasses.replace(b.entry, bound_health_resolution_ref=R("other"))
    assert O.delivered_hash(T, h2) != b.delivered_feature_hash
    assert gw.resolve("a", _entry(), I, I, 3, 10, _health(ok=False)) is b          # later unhealthy snapshot cannot rewrite
    assert _gw(avail=9).resolve("c", _entry(), I, I, 3, 10, _health(ok=False)).reason == "HEALTH_UNACCEPTABLE"

def test_g7_stale_watermark_fails():
    gw = _gw(avail=9); gw.set_watermark(5)
    assert gw.resolve("a", _entry(), I, I, 3, 10, _health()).reason == "STALE_WATERMARK"

def test_g8_generic_dependency_schema_only():
    d = dict(feature_id=I, feature_version="f1", requirement_class="REQUIRED", expected_projection="p", scope_ref=R("a"),
             temporal_ref=R("b"), vintage_ref=R("c"), health_rule_ref=R("d"))
    G.DependencyEntry.from_dict(d)
    with pytest.raises(Refusal): G.DependencyEntry.from_dict(dict(d, garch_lambda=1))

def test_ob2_failed_quant_lane_does_not_block_unrelated_binding():
    st = C.ChainStatusAuthority(); gw = G.SimulatedGateway(T, st, allow_uncommitted_status=True, watermark=100)
    st.append(C.StatusFact((I, "f1", I, I, "m1"), 1, C.HALTED, 1, True)); st.append(C.StatusFact((J, "f1", I, I, "m1"), 1, C.CURRENT, 1, False))
    gw.publish(_row(fid=I, avail=4)); gw.publish(_row(fid=J, avail=4))
    assert isinstance(gw.resolve("bad", _entry(fid=I), I, I, 3, 10, _health()), G.NonDeliveryResolution)
    assert isinstance(gw.resolve("good", _entry(fid=J), I, I, 3, 10, _health()), G.Binding)

def test_correction_after_bind_preserves_old_binding():
    gw = _gw(avail=9); b = gw.resolve("a", _entry(), I, I, 3, 10, _health())
    gw.note_correction_after_bind("a", R("fix"))
    assert gw.outcome("a") is b and gw.later_lineage("a") == (R("fix"),)
    with pytest.raises(Refusal): gw.note_correction_after_bind("nope", R("x"))

def test_catching_up_where_current_required_and_vintage_mismatch():
    gw = _gw(status=C.CATCHING_UP, avail=9)
    assert gw.resolve("a", _entry(), I, I, 3, 10, _health()).reason == "CHAIN_STATUS_NOT_CURRENT:CATCHING_UP"
    assert isinstance(gw.resolve("b", _entry(), I, I, 3, 10, _health(), require_current=False), G.Binding)
    gw2 = _gw(avail=9, vint="EVENTUAL")
    assert gw2.resolve("c", _entry(), I, I, 3, 10, _health(), data_vintage_mode="ORIGINAL_AS_OBSERVED").reason == "DATA_VINTAGE_MODE_MISMATCH"

# ---------- FW receiving (F1-F3 via lanes, §XIII negatives) ------------------------------------------------------------
def _bound(**kw):
    gw = _gw(avail=9, **kw); return gw, gw.resolve("a", _entry(), I, I, 3, 10, _health())

def test_fw_receives_exact_binding_and_cross_consumer_identity():
    gw, b = _bound(); assert FW.receive(b, _entry(), I, I, T, gateway=gw) is b
    ml = ML.build_row("r1", R("gen"), [_entry()], [b], gw, "ORIGINAL_AS_OBSERVED", ("ENUM", "REASON", "NONE"), lambda o: ("ENUM", "REASON", "NONE"))
    assert ml.bindings[0].entry.published_projection_bits == b.entry.published_projection_bits and ml.bindings[0].delivered_feature_hash == b.delivered_feature_hash

def test_fw_fail_closed_negatives():
    gw, b = _bound()
    with pytest.raises(Refusal): FW.receive(b, _entry(ver="f2"), I, I, T)                              # wrong version
    with pytest.raises(Refusal): FW.receive(b, _entry(), J, I, T)                                      # wrong scope
    with pytest.raises(Refusal): FW.receive(dataclasses.replace(b, delivered_feature_hash=bytes(32)), _entry(), I, I, T)   # hash mismatch
    gw2 = _gw(status=C.CATCHING_UP, avail=9); nb = gw2.resolve("a", _entry(), I, I, 3, 10, _health(), require_current=False)
    with pytest.raises(Refusal): FW.receive(nb, _entry(), I, I, T)                                     # CATCHING_UP where CURRENT required
    nd = _gw().resolve("z", _entry(fid=J), I, I, 3, 10, _health())
    with pytest.raises(Refusal): FW.receive(nd, _entry(fid=J), I, I, T)                                # required absent / non-delivery
    with pytest.raises(Refusal): FW.receive(b, _entry(), I, I, T, gateway=_gw(avail=9))                # not the Gateway's stored binding
    with pytest.raises(Refusal): FW.receive("raw value", _entry(), I, I, T)

# ---------- lanes / Plan-B (F1-F3, M1, M3) ----------------------------------------------------------------------------
Q = b"Q" * 16; B1 = b"B" * 16
def test_lanes_and_closure():
    g = {}
    base = L.ConsumerManifest("base", "FW", (B1,)); g["base"] = base
    assert L.classify(base, Q, g) == L.BASELINE                                                        # F1
    assert L.classify(L.ConsumerManifest("m", "FW", (Q,)), Q, g) == L.MODEL_SPECIFIC                   # F2
    assert L.classify(L.ConsumerManifest("c", "FW", (B1, Q), includes_baseline_dependencies=True), Q, g) == L.CONFLUENCE   # F3
    g["tainted"] = L.ConsumerManifest("tainted", "FW", (Q,))
    with pytest.raises(Refusal): L.classify(L.ConsumerManifest("b2", "FW", (B1,), derived_from="tainted"), Q, g)           # M3
    g["retuned"] = L.ConsumerManifest("retuned", "FW", (B1,), post_target_retuning=True)
    with pytest.raises(Refusal): L.classify(L.ConsumerManifest("b3", "FW", (B1,), derived_from="retuned"), Q, g)
    with pytest.raises(Refusal): L.classify(L.ConsumerManifest("b4", "FW", (B1,), derived_from="missing"), Q, g)          # unread ancestry
    with pytest.raises(Refusal): L.classify(L.ConsumerManifest("b5", "FW", (B1,), declared_lane=L.CONFLUENCE), Q, g)
    g["x"] = L.ConsumerManifest("x", "FW", (B1,), derived_from="y"); g["y"] = L.ConsumerManifest("y", "FW", (B1,), derived_from="x")
    with pytest.raises(Refusal): L.classify(g["x"], Q, g)

# ---------- ML (F4-F6, M1, M2, M4 + ML negatives) ---------------------------------------------------------------------
NONE_ = ("ENUM", "REASON", "NONE")
def test_ml_row_negatives_and_explicit_exclusion():
    gw, b = _bound()
    row_ = ML.build_row("r", R("gen"), [_entry()], [b], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_)
    assert row_.included
    with pytest.raises(Refusal): ML.build_row("r", R("gen"), [_entry()], [b], _gw(avail=9), "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_)   # F4 no Gateway rebind
    with pytest.raises(Refusal): ML.build_row("r", R("gen"), [_entry()], [b], gw, "EVENTUAL", NONE_, lambda o: NONE_)                        # EVENTUAL look-ahead/mixed era
    nd = gw.resolve("z", _entry(fid=J), I, I, 3, 10, _health())
    ex = ML.build_row("r", R("gen"), [_entry(fid=J)], [nd], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: ("ENUM", "REASON", "NONE"))
    assert not ex.included and ex.row_exclusion_reason is not None                                                                               # explicit, not silent drop
    with pytest.raises(Refusal): ML.build_row("r", R("gen"), [_entry()], [0.0], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_)          # default/forward fill not representable
    with pytest.raises(Refusal): ML.build_row("r", R("gen"), [_entry(), _entry()], [b, b], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_)
    with pytest.raises(Refusal): ML.build_row("r", R("gen"), [_entry()], [], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_)

def test_ml_optional_absence_requires_exact_rule():
    gw = _gw(); o = gw.resolve("o", _entry(opt=True, fid=J), I, I, 3, 10, _health())
    r = ML.build_row("r", R("gen"), [_entry(opt=True, fid=J)], [o], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda x: NONE_)
    assert r.absence_applied == (o,)
    with pytest.raises(Refusal): ML.build_row("r", R("gen"), [_entry(fid=J)], [o], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda x: NONE_)  # REQUIRED never degrades

def test_ml_generation_checks_and_augmented():
    g = {"fw": L.ConsumerManifest("fw", "FW", (B1,))}
    assert ML.check_generation(L.ConsumerManifest("g", "ML", (B1,)), Q, g, "ML_STANDALONE") == L.BASELINE                 # M2/M4 baseline ok
    with pytest.raises(Refusal): ML.check_generation(L.ConsumerManifest("g", "ML", (B1,), derived_from="fw"), Q, g, "ML_STANDALONE")     # M1
    with pytest.raises(Refusal): ML.check_generation(L.ConsumerManifest("g", "ML", (Q,)), Q, g, "ML_STANDALONE")
    gw, b = _bound()
    ML.AugmentedInput(R("l"), R("u"), R("o"), R("d"), b, R("g"), R("x"), R("s"))                                                                   # F5
    for kw in (dict(uncertainty_ref=None), dict(ood_ref=None), dict(dependency_interval_ref=None), dict(gateway_rebind=None), dict(fw_generation_identity_ref=None), dict(research_exposure_ref=None), dict(support_ref=None)):   # F6
        base = dict(fw_lineage_ref=R("l"), uncertainty_ref=R("u"), ood_ref=R("o"), dependency_interval_ref=R("d"), gateway_rebind=b, fw_generation_identity_ref=R("g"), research_exposure_ref=R("x"), support_ref=R("s")); base.update(kw)
        with pytest.raises(Refusal): ML.AugmentedInput(**base)

# ---------- Health (Q17), Context (TR-12) -----------------------------------------------------------------------------
def test_health_is_evidence_only_and_objects_validate():
    sink = HE.HealthEvidenceSink()
    public = {n for n in dir(sink) if not n.startswith("_")}
    assert public == {"emit", "evidence"}                                                  # no refit/delivery/status methods exist
    gw, b = _bound(); sink.emit(HE.FeatureHealthEvidence("f1", I, I, row_hash=H)); assert gw.outcome("a") is b
    with pytest.raises(Refusal): sink.emit({"refit": True})
    HE.LatencyMetricsV1(R("w"), *([1] * 11))
    with pytest.raises(Refusal): HE.LatencyMetricsV1(R("w"), *([1] * 10), -1)
    with pytest.raises(Refusal): HE.ResourceMetricsV1(R("w"), b"x", BITS, 1, 1, 1, 1)
    m = lambda i: HE.ModelMetric(i, R("p"), R("w"), 1, "UINT64_VALUE", 1)
    assert [x.metric_id for x in HE.canonical_model_metrics([m("b"), m("a")])] == ["a", "b"]
    with pytest.raises(Refusal): HE.canonical_model_metrics([m("a"), m("a")])
    with pytest.raises(Refusal): HE.ModelMetric("a", R("p"), R("w"), 1, "BAD", 1)

def test_direct_paths_do_not_exist_q18_q19_q20():
    root = pathlib.Path(__file__).resolve().parents[2] / "stage_a"
    def imports(p):
        t = ast.parse(p.read_text()); out = set()
        for n in ast.walk(t):
            if isinstance(n, ast.ImportFrom): out.add(("." * n.level) + (n.module or ""))
            if isinstance(n, ast.Import): out |= {a.name for a in n.names}
        return out
    for consumer in ("fw/receiver.py", "ml/receiver.py"):
        bad = [m for m in imports(root / consumer) if "composer" in m or "health" in m or "tracker" in m and "chain_status" not in m]
        assert not bad, (consumer, bad)                                                    # FW/ML never import Composer/Health/Tracker internals
    for p in (root / "composer").rglob("*.py"):
        assert not any(("fw" in m.split(".") or "ml" in m.split(".") or "gateway" in m.split(".")) for m in imports(p)), p
    for p in (root / "health").rglob("*.py"):
        assert not any(("fw" in m.split(".") or "ml" in m.split(".")) for m in imports(p)), p
    for p in (root / "context").rglob("*.py"):
        assert not any(("composer" in m or "materializ" in m) for m in imports(p)), p

def test_context_edge_declared_only():
    assert CE.assert_declared([(I, "c1")], [(I, "c1")]) == ((I, "c1"),)
    with pytest.raises(Refusal): CE.assert_declared([(I, "c1")], [(I, "c2")])

def test_no_status_fact_fails_closed_and_verifier_refusals():
    st = C.ChainStatusAuthority(); gw = G.SimulatedGateway(T, st, allow_uncommitted_status=True, watermark=100); gw.publish(_row(avail=4))
    assert gw.resolve("a", _entry(), I, I, 3, 10, _health()).reason == "NO_STATUS_AUTHORITY_FACT"
    bad = dict(row_content_hash=H, verification_evidence_ref=xref(R("v")), sifp_fencing_epoch=2, canonical_commit_point_id=I,
               canonical_accepted_at=5, available_asof=6, gate_dependency_transition_ref=None, currentness_state_at_acceptance=1, status_event=1)
    with pytest.raises(ValueError): X.transition_hash(bad, ENUMS)
    sd = dict(status_event_id=I, feature_version="f1", instrument_id=I, timeframe_id=I, materialization_version="m1", mv_status_sequence=1,
              status_event_type=1, effective_from=("INTERVAL", 9, 9), reason_code=("ENUM", "REASON", 1), predecessor_or_successor_mv_ref=None,
              available_asof=7, evidence_ref=xref(R("e")), sifp_fencing_epoch=2, correction_marked=False)
    with pytest.raises(ValueError): X.status_event_hash(sd, ENUMS)

def test_priority_classes_live_heads_never_behind_replay_storm():
    pend = {"replay%02d" % i: ("P2_HISTORICAL_REPLAY", list(range(30))) for i in range(10)}
    pend["live_a"] = ("P0_LIVE_HEAD", ["h"]); pend["crit"] = ("P1_LIVE_CRITICAL", ["c", "c2"])
    flat = [x for b in ReplayScheduler(1000, 7).plan_prioritized(pend) for x in b]
    assert [n for n, _ in flat[:4]] == ["live_a", "crit", "crit", "replay00"]
    assert all(n.startswith("replay") for n, _ in flat[3:])
    with pytest.raises(Refusal): ReplayScheduler(10, 2).plan_prioritized({"a": ("P9", [1])})
    with pytest.raises(Refusal): ReplayScheduler(2, 2).plan_prioritized({"a": ("P2_HISTORICAL_REPLAY", [1, 2, 3])})

def test_candidate_code_tables_are_provisional_and_cover_objects():
    from stage_a.schema.candidate_code_tables import candidate_tables
    ct = candidate_tables(); assert ct.provisional
    for n in ("REFIT_MODE", "SPECULATION_MODE", "CURRENTNESS_STATE", "TRANSITION_STATUS_EVENT", "CHAIN_STATUS", "PROGRAM_CAPABILITY_CLASS"):
        assert n in ct.enums and min(ct.enums[n].values()) == 1
    assert ct.enums["CHAIN_STATUS"]["HALTED"] == 4 and "DATA_VINTAGE_MODE" not in ct.enums     # unlisted sets are not invented
    assert len(set(ct.ref_types.values())) == len(ct.ref_types)

def test_d25_candidate_protocol_three_outcomes_and_stale_refusal():
    from stage_a.tracker import epoch_reresolution as E
    assert E.re_resolve(3, 4, "HALTED").outcome == E.ALREADY_FENCED and E.re_resolve(3, 4, "HALTED").protection_effective
    r = E.re_resolve(3, 4, "CURRENT"); assert r.outcome == E.ACTION_REQUIRED and not r.protection_effective
    assert E.re_resolve(3, None, None).outcome == E.UNRESOLVED and not E.re_resolve(3, None, "CURRENT").protection_effective
    assert E.apply(4, 4, "CURRENT", "CURRENT")
    with pytest.raises(Refusal): E.apply(3, 4, "CURRENT", "CURRENT")
    with pytest.raises(Refusal): E.apply(4, 4, "CURRENT", "SUPERSEDED")


# ---------- review R04: semantic enum membership, tag strictness, remapped provisional tables --------------------------
def _sd(**kw):
    d = dict(status_event_id=I, feature_version="f1", instrument_id=I, timeframe_id=I, materialization_version="m1", mv_status_sequence=1,
             status_event_type=1, effective_from=("INTERVAL", 2, 9), reason_code=("ENUM", "REASON", 1), predecessor_or_successor_mv_ref=None,
             available_asof=7, evidence_ref=xref(R("e")), sifp_fencing_epoch=2, correction_marked=False)
    d.update(kw); return d

def test_independent_rejects_unknown_and_malformed_tags():
    base = X.status_event_hash(_sd(), ENUMS)
    for bad in (("BOGUS", (1, b"id", b"v", None)), ("BOGUS", "REASON", 1), ("ENUM", 1), ("ENUM",), ("REF",), (), None, "ENUM", ("REF", xref(R("x")), 1),
                ("ENUM", "NOSET", 1), ("ENUM", "REASON", 99), ("ENUM", "REASON", True), ("ENUM", "REASON", "NONE")):
        with pytest.raises(ValueError): X.status_event_hash(_sd(reason_code=bad), ENUMS)
    dd = _delivered_dict()
    for bad in (("BOGUS", xref(R("w"))), ("ENUM", "REASON", 99), ("REF",)):
        with pytest.raises(ValueError): X.delivered_hash(dict(dd, omissions_exclusions_reason_codes=[bad]), ENUMS)
    assert X.status_event_hash(_sd(reason_code=("REF", xref(R("x")))), ENUMS) != base

def _delivered_dict():
    d = _delivered(); dd = dataclasses.asdict(d)
    for k in ("fit_generation_ref", "source_or_causal_policy_ref", "bound_health_resolution_ref", "canonical_transition_ref"):
        dd[k] = None if getattr(d, k) is None else xref(getattr(d, k))
    dd["data_vintage_mode"] = 1; dd["chain_status_at_bind"] = 1; dd["omissions_exclusions_reason_codes"] = []
    return dd

def test_independent_enum_membership_unknown_codes_and_remapped_tables():
    rd = rowd(row())
    for bad in (0, 3, 99, True, -1, "OFF"):
        with pytest.raises(ValueError): X.row_hash(dict(rd, speculation_mode=bad), ENUMS)
    with pytest.raises(ValueError): X.row_hash(rd, {k: v for k, v in ENUMS.items() if k != "SPECULATION_MODE"})   # set absent: fail closed
    # a provisional REMAPPING (GATED_ONE_STEP -> 17) is honoured from the table; no numbering is adopted by the verifier
    re_enums = dict(ENUMS, SPECULATION_MODE={"OFF": 5, "GATED_ONE_STEP": 17})
    T2 = CodeTables(enums=re_enums, ref_types={"R": 1})
    g = row(speculation_mode="GATED_ONE_STEP", gate_dependency_hash=H); gd = rowd(g); gd["speculation_mode"] = 17
    assert X.row_hash(gd, re_enums) == O.row_content_hash(T2, g)
    o = row(); od = rowd(o); od["speculation_mode"] = 5
    assert X.row_hash(od, re_enums) == O.row_content_hash(T2, o)
    with pytest.raises(ValueError): X.row_hash(dict(gd, gate_dependency_hash=None), re_enums)      # gate presence follows the table
    with pytest.raises(ValueError): X.row_hash(dict(od, gate_dependency_hash=H), re_enums)
    with pytest.raises(ValueError): X.row_hash(dict(gd), ENUMS)                                      # 17 is unknown under the old table
    for name, f in (("CURRENTNESS_STATE", lambda c: X.transition_hash(dict(c, currentness_state_at_acceptance=77), ENUMS)),
                    ("TRANSITION_STATUS_EVENT", lambda c: X.transition_hash(dict(c, status_event=77), ENUMS))):
        c = dict(row_content_hash=H, verification_evidence_ref=xref(R("v")), sifp_fencing_epoch=2, canonical_commit_point_id=I,
                 canonical_accepted_at=5, available_asof=5, gate_dependency_transition_ref=None, currentness_state_at_acceptance=1, status_event=1)
        with pytest.raises(ValueError): f(c)
    with pytest.raises(ValueError): X.status_event_hash(_sd(status_event_type=77), ENUMS)
    dd = _delivered_dict()
    for k in ("data_vintage_mode", "chain_status_at_bind"):
        with pytest.raises(ValueError): X.delivered_hash(dict(dd, **{k: 77}), ENUMS)

# ---------- Q9 (Tracker-owned slice): a new fit generation is a new immutable generation, never a manifest mutation -----------------
def test_q9_new_fit_generation_changes_row_and_delivered_identity_but_not_manifest_hash():
    from tests.trk_stage_a.test_schema_annex import manifest
    Tm = CodeTables(enums={"PROGRAM_CAPABILITY_CLASS": {"TRANSITION": 1, "PROJECTION": 2}, "REFIT_MODE": {"NONE": 1, "SCHEDULED_REFIT": 2}},
                    ref_types={"R": 1, "PROGRAM": 1, "RULE": 1})
    mh = O.manifest_hash(Tm, manifest())
    r1, r2 = row(fit_generation_ref=R("fit", H)), row(fit_generation_ref=R("fit", J * 2))
    assert O.row_content_hash(T, r1) != O.row_content_hash(T, r2)
    d1, d2 = _delivered(fit_generation_ref=R("fit", H)), _delivered(fit_generation_ref=R("fit", J * 2))
    assert O.delivered_hash(T, d1) != O.delivered_hash(T, d2)
    assert O.manifest_hash(Tm, manifest()) == mh                                   # manifest carries no generation ref: nothing to mutate
    assert not any(f.name.startswith("fit_generation") for f in dataclasses.fields(O.QuantManifest))

# ---------- D6 evidence: Composer section 28 TRACKER_SAFE_INTAKE_REPORT field list vs the adapter's report ---------------------------
def test_safe_intake_report_covers_composer_28_field_list():
    import inspect
    from stage_a.tracker import quant_intake_adapter as A
    src = inspect.getsource(A.build_safe_intake_report)
    # flat names in Composer V9 section 28 -> the key (possibly nested) the adapter emits
    mapping = {"SAFE_INTAKE_REPORT_ID": "SAFE_INTAKE_REPORT_ID", "BUILD_OUTPUT_PACKAGE_ID / HASH": "BUILD_OUTPUT_PACKAGE", "REQUEST_ID / CREATION_REQUEST_ID": "CREATION_REQUEST_ID",
               "INTAKE_VERDICT": "INTAKE_VERDICT", "FAILED_DIMENSIONS": "FAILED_DIMENSIONS", "FAILED_DIMENSION_REASON_CODES": "FAILED_DIMENSION_REASON_CODES",
               "IDENTITY_DECISION": "IDENTITY_DECISION", "RESULTING_FEATURE_ID / FEATURE_VERSION / REGISTRY_ENTRY_REF": "REGISTRY_ENTRY_REF",
               "CANONICAL_SURVIVOR_ID": "CANONICAL_SURVIVOR", "FEATURE_VERSION_RELATIONSHIP_REF": "FEATURE_VERSION_RELATIONSHIP_REF",
               "DEPENDENCY_CLOSURE_REF": "DEPENDENCY_CLOSURE_REF", "ANCESTRY_COMPLETENESS": "ANCESTRY_COMPLETENESS",
               "CAUSAL_AVAILABILITY_VERDICT": "CAUSAL_AVAILABILITY_VERDICT", "SOURCE / VINTAGE / PROVENANCE_VERDICT": "SOURCE_VINTAGE_PROVENANCE_VERDICT",
               "OUTCOME_INFORMATION_ACCESS_VERDICT": "OUTCOME_INFORMATION_ACCESS_VERDICT", "LEARNED_OR_FITTED_ANCESTRY_VERDICT": "LEARNED_OR_FITTED_ANCESTRY_VERDICT",
               "COMPLETION_SEMANTICS_VERDICT": "COMPLETION_SEMANTICS_VERDICT", "CURRENTNESS / HEALTH / ELIGIBILITY_INITIAL_STATE": "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE",
               "OMISSIONS / EXCLUSIONS / REASONS": "OMISSIONS_EXCLUSIONS_REASONS", "SAFE_INTAKE_TS": "SAFE_INTAKE_TS", "TRACKER_VERIFIER_ID": "TRACKER_VERIFIER_ID",
               "POLICY_ID / POLICY_VERSION / POLICY_HASH": "POLICY"}
    assert len(mapping) == 22                                                       # 22 bullet lines in section 28 (FINAL_REPORT_HASH is added by build_report)
    for flat, key in mapping.items():
        assert '"%s"' % key in src, (flat, key)
    import tracker_component.report as TR
    assert TR.REPORT_FIELDS[-1] == "FINAL_REPORT_HASH" and len(TR.REPORT_FIELDS) == 23
    # every top-level key the baseline report schema owns is one the adapter emits (the adapter cannot drift from it)
    for k in TR.BODY_FIELDS:
        assert '"%s"' % k in src, k
