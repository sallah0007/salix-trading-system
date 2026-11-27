"""Master Health Extension V3 B0 envelope / anti-replay / silence / recovery (pure validators; no Health service exists in this repository)."""
import pytest
from stage_a.errors import Refusal
from stage_a.health import envelope as HV

SV = {"hv1"}
def env(**kw):
    e = {k: "x" for k in HV.REQUIRED}
    e.update(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "EURUSD"}, EXPECTATION_STATE="EXPECTED", EFFECTIVE_FROM_BASIS="OBSERVED",
             EFFECTIVE_FROM=10, EFFECTIVE_TO="OPEN", PRODUCER_SEQUENCE=5, HEALTH_ENVELOPE_SCHEMA_VERSION="hv1", LAST_VERIFIED_GOOD_AT=3)
    e.update(kw); return e

def test_envelope_required_fields_each_refused_when_missing():
    HV.check_envelope(env(), SV)
    for k in HV.REQUIRED:
        with pytest.raises(Refusal): HV.check_envelope(env(**{k: None}), SV)
    for k in HV.WHERE_APPLICABLE:
        HV.check_envelope(env(**{k: None}), SV)                                    # applicable-only fields are optional

def test_envelope_semantic_refusals():
    for bad in (dict(EVIDENCE_REFS=["a"]), dict(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE"}), dict(SUBJECT_IDENTITY={"INSTRUMENT_ID": "X"}),
                dict(SUBJECT_IDENTITY="EURUSD"), dict(EXPECTATION_STATE="MAYBE"), dict(EFFECTIVE_FROM_BASIS="GUESSED"), dict(EFFECTIVE_TO=9),
                dict(EFFECTIVE_TO="CLOSED"), dict(PRODUCER_SEQUENCE=-1), dict(PRODUCER_SEQUENCE=True), dict(HEALTH_ENVELOPE_SCHEMA_VERSION="hv9"),
                dict(EFFECTIVE_FROM_BASIS="UNKNOWN", LAST_VERIFIED_GOOD_AT=None)):
        with pytest.raises(Refusal): HV.check_envelope(env(**bad), SV)
    HV.check_envelope(env(EFFECTIVE_TO=10), SV)                                    # an interval may be zero-length at its start
    HV.check_envelope(env(EFFECTIVE_FROM_BASIS="UNKNOWN", LAST_VERIFIED_GOOD_AT=2), SV)

def test_anti_replay_strictly_increasing_per_producer_subject_and_integrity_first():
    a = HV.AntiReplay(); a.admit(env(PRODUCER_SEQUENCE=5), True)
    for seq in (5, 4, 0):
        with pytest.raises(Refusal): a.admit(env(PRODUCER_SEQUENCE=seq), True)       # replay / stale HEALTHY cannot restore
    a.admit(env(PRODUCER_SEQUENCE=6), True)
    with pytest.raises(Refusal): a.admit(env(PRODUCER_SEQUENCE=99), False)           # bad integrity: refused, and does not advance
    a.admit(env(PRODUCER_SEQUENCE=7), True)
    a.admit(env(PRODUCER_SEQUENCE=1, PRODUCER_ID="other"), True)                      # separate producer scope
    a.admit(env(PRODUCER_SEQUENCE=1, SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "XAUUSD"}), True)   # instrument scope
    a.admit(env(PRODUCER_SEQUENCE=1, SUBJECT_IDENTITY={"AUTHORITY_STATE": "TEST", "INSTRUMENT_ID": "EURUSD"}), True)   # authority-state scope

def test_silence_is_never_healthy_and_unknown_expectation_is_not_not_expected():
    assert HV.derive_silence(10, 10, "EXPECTED") is None and HV.derive_silence(11, 10, "EXPECTED") == "STALE_NO_PRODUCER"
    assert HV.derive_silence(11, 10, "EXPECTATION_UNKNOWN") == "EXPECTATION_UNKNOWN_SILENCE"
    assert HV.derive_silence(11, 10, "NOT_EXPECTED") == "NOT_APPLICABLE_SILENCE"
    assert HV.derive_silence(5, 10, "EXPECTATION_UNKNOWN") is None
    with pytest.raises(Refusal): HV.derive_silence(11, 10, "MAYBE")

def test_recovery_gating_heartbeat_never_clears_integrity_class():
    assert HV.may_clear("TRANSIENT_AUTO_RECOVERABLE", "FRESH_QUALIFYING_EVIDENCE")
    assert not HV.may_clear("TRANSIENT_AUTO_RECOVERABLE", "HEARTBEAT")
    assert not HV.may_clear("EVIDENCE_REVALIDATION_REQUIRED", "HEARTBEAT") and not HV.may_clear("EVIDENCE_REVALIDATION_REQUIRED", "FRESH_QUALIFYING_EVIDENCE")
    assert HV.may_clear("EVIDENCE_REVALIDATION_REQUIRED", "REVALIDATION_PROOF")
    for k in ("HEARTBEAT", "FRESH_QUALIFYING_EVIDENCE", "REVALIDATION_PROOF", "GOVERNED_RESTORATION"):
        assert not HV.may_clear("AUTHORISED_RESTORATION_REQUIRED", k)
    with pytest.raises(Refusal): HV.may_clear("SOMETHING", "HEARTBEAT")
