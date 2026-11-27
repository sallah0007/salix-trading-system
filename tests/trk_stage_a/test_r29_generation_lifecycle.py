import dataclasses, threading, pytest
from stage_a.ml import generation_lifecycle as GL
from stage_a.errors import Refusal

def man(i="M1", **drop):
    comps = tuple((n, "h-" + n + i) for n in GL.MIN_COMPONENTS if n not in drop); return GL.CertifiedGenerationManifest(i, "mh-" + i, comps, "gen-" + i, ("XAUUSD",))
def ev(ts=100, **k): d = dict(forecast_ts=ts, instrument_id="XAUUSD", target_horizon_id="T1", knowledge_boundary=ts); d.update(k); return GL.EventIdentity(**d)
def reg(*ids):
    r = GL.GenerationRegistry()
    for n, i in enumerate(ids):
        r.register_manifest(man(i)); r.append_lifecycle(i, "COMPLETE_CERTIFIED", 10 + n, "cert", "AUTH")
    return r
def code(f, *a):
    try: f(*a)
    except Refusal as e: return e.code

def test_manifest_must_be_complete_immutable_and_component_wellformed():
    r = GL.GenerationRegistry()
    for n in GL.MIN_COMPONENTS: assert code(r.register_manifest, man(**{n: 1})) == "ML_MANIFEST_INCOMPLETE", n
    r.register_manifest(man()); r.register_manifest(man())                                          # identical re-register is idempotent
    assert code(r.register_manifest, GL.CertifiedGenerationManifest("M1", "other", man().components, "gen-M1", ("XAUUSD",))) == "ML_MANIFEST_IMMUTABLE"
    assert code(r.register_manifest, GL.CertifiedGenerationManifest("M2", "h", (("a", "b"), ("a", "c")), "g", ("XAUUSD",))) == "ML_MANIFEST_COMPONENT_MALFORMED"
def test_eligibility_needs_manifest_and_latest_ledger_state_and_ledger_is_append_only_monotonic():
    r = GL.GenerationRegistry(); r.register_manifest(man()); assert not r.eligible("M1")                 # no ledger state: not eligible
    r.append_lifecycle("M1", "CANDIDATE", 5, "c", "A"); assert not r.eligible("M1")
    e = r.append_lifecycle("M1", "COMPLETE_CERTIFIED", 6, "c", "A"); assert r.eligible("M1") and e.epoch == 2
    r.append_lifecycle("M1", "REVOKED", 9, "bad", "A"); assert not r.eligible("M1") and r.eligible("M1", 7)   # as-of history preserved
    assert [x.epoch for x in r.ledger()] == [1, 2, 3] and code(r.append_lifecycle, "M1", "BOGUS", 9, "r", "a") == "ML_LIFECYCLE_ENTRY_MALFORMED"
    assert code(r.append_lifecycle, "M1", "SUPERSEDED", 1, "r", "a") == "ML_LIFECYCLE_TS_REGRESSED" and code(r.append_lifecycle, "NOPE", "REVOKED", 20, "r", "a") == "ML_LIFECYCLE_FOR_UNREGISTERED_MANIFEST"
def test_publish_positive_control_and_idempotence():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1", 100); assert r.compare_and_publish(s, "R").status == GL.PUBLISHED
    assert r.compare_and_publish(s, "R2").reason == "ALREADY_PUBLISHED_IDEMPOTENT" and r.published(ev())[1] == "R"
def test_revocation_between_snapshot_and_publish_rejects_and_never_regenerates_under_newer_generation():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1", 100)
    r.append_lifecycle("M1", "REVOKED", 50, "bad", "A"); r.register_manifest(man("M2")); r.append_lifecycle("M2", "COMPLETE_CERTIFIED", 60, "c", "A")
    o = r.compare_and_publish(s, "R"); assert o.status == GL.REJECTED_QUARANTINED and r.published(ev()) is None
    assert r.retry_publish(s, "R").reason == "NO_RETROACTIVE_REGENERATION"                           # still no publish
    assert r.compare_and_publish(r.snapshot("q2", ev(), "M2", 100), "R").reason == "EVENT_ALREADY_FAILED_NO_REGENERATION"    # a newer generation may NOT fill the failed slot
    assert r.compare_and_publish(r.snapshot("q3", ev(ts=200), "M2", 100), "N").status == GL.PUBLISHED     # ...but is a NEW event with its own identity
def test_supersession_is_discarded_not_quarantined_and_unrelated_generation_epoch_change_is_tolerated():
    r = reg("M1", "M2"); s = r.snapshot("q", ev(), "M1", 100); r.append_lifecycle("M2", "SUPERSEDED", 40, "old", "A")                  # unrelated manifest changes the global epoch
    assert r.compare_and_publish(s, "R").status == GL.PUBLISHED                                       # M1's own state unchanged: positive control
    s2 = r.snapshot("q2", ev(ts=101), "M1", 100); r.append_lifecycle("M1", "SUPERSEDED", 41, "x", "A")
    assert r.compare_and_publish(s2, "R").status == GL.REJECTED_DISCARDED
def test_atomic_compare_and_publish_revocation_injected_at_the_commit_point_cannot_split_check_from_commit():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1", 100); done = []
    def hook():                                                                                          # runs INSIDE the critical section: another thread tries to revoke exactly now
        t = threading.Thread(target=lambda: (r.append_lifecycle("M1", "REVOKED", 70, "late", "A"), done.append(1))); t.start(); t.join(0.2)
        assert not done                                                                                  # blocked: revocation cannot interleave between fence validation and commit
    r._commit_hook = hook; o = r.compare_and_publish(s, "R"); r._commit_hook = None
    assert o.status == GL.PUBLISHED and r.published(ev())[1] == "R"
    for _ in range(50):
        if done: break
        threading.Event().wait(0.02)
    a = r.annotated(ev()); assert a["later_revoked"] and a["record"][1] == "R"                           # original record unchanged; later revocation visible at read
def test_reconstruction_never_defaults_to_the_current_generation():
    r = reg("M1"); r.append_lifecycle("M1", "REVOKED", 50, "bad", "A"); r.register_manifest(man("M2")); r.append_lifecycle("M2", "COMPLETE_CERTIFIED", 60, "c", "A")
    assert r.reconstruct_for_event(ev(ts=20), "PASS", "PASS") == GL.Reconstruction(GL.RECONSTRUCTED_CANDIDATE, "M1", "EVIDENCE_TOKENS_SUPPLIED_NOT_VERIFIED")              # certified at that time
    x = r.reconstruct_for_event(ev(ts=55), "PASS", "PASS"); assert x.outcome == GL.MISSED and x.manifest_id is None     # nothing eligible then; M2 (current) must NOT be returned
    assert r.reconstruct_for_event(ev(ts=5), "PASS", "PASS").outcome == GL.MISSED                                       # before any certification
    r2 = reg("A", "B"); assert r2.reconstruct_for_event(ev(ts=100), "PASS", "PASS").outcome == GL.NOT_PROVABLY_RECONSTRUCTABLE      # ambiguous
    assert code(r.reconstruct_for_event, ev(knowledge_boundary=None), "PASS", "PASS") == "ML_EVENT_IDENTITY_INCOMPLETE"
def test_snapshot_requires_eligible_generation_and_complete_event_identity():
    r = reg("M1"); assert code(r.snapshot, "q", ev(instrument_id=""), "M1") == "ML_EVENT_IDENTITY_INCOMPLETE"
    r.append_lifecycle("M1", "REVOKED", 20, "x", "A"); assert code(r.snapshot, "q", ev(), "M1") == "ML_GENERATION_NOT_SERVING_ELIGIBLE"
    assert code(r.compare_and_publish, "not a snapshot", "R") == "ML_PUBLISH_NEEDS_REQUEST_SNAPSHOT"

def test_epoch_change_alone_fails_the_fence_even_if_the_generation_is_still_eligible_at_commit():
    r = reg("M1"); s = r.snapshot("q", ev(), "M1", 100)
    r.append_lifecycle("M1", "COMPLETE_CERTIFIED", 31, "re-affirmed", "A")                                 # same-state re-affirmation: still eligible, but the lifecycle epoch moved since the snapshot
    assert r.eligible("M1") and r.compare_and_publish(s, "R").status == GL.REJECTED_DISCARDED
def test_r30_revoked_or_superseded_generation_cannot_be_revived_and_new_generation_is_the_positive_control():
    r = reg("M1"); r.append_lifecycle("M1", "REVOKED", 20, "bad", "A")
    for st_ in ("COMPLETE_CERTIFIED", "CANDIDATE", "SUPERSEDED"): assert code(r.append_lifecycle, "M1", st_, 30, "revive", "A") == "ML_LIFECYCLE_RESTORATION_HELD", st_
    assert not r.eligible("M1") and r.eligible("M1", 15) and [e.state for e in r.ledger()] == ["COMPLETE_CERTIFIED", "REVOKED"]      # append-only history intact, nothing appended by the refusals
    r.register_manifest(man("M2")); r.append_lifecycle("M2", "COMPLETE_CERTIFIED", 30, "new generation", "A"); assert r.eligible("M2")
    r2 = reg("M1"); r2.append_lifecycle("M1", "SUPERSEDED", 20, "old", "A"); assert code(r2.append_lifecycle, "M1", "COMPLETE_CERTIFIED", 30, "x", "A") == "ML_LIFECYCLE_RESTORATION_HELD"
    r.append_lifecycle("M1", "REVOKED", 40, "idempotent re-record", "A")                                  # same-state record is not a revival
    assert not r.eligible("M1")


def test_r30_forged_altered_future_cross_request_and_cross_manifest_snapshots_are_refused_and_valid_publishes():
    r = reg("M1", "M2"); s = r.snapshot("q1", ev(), "M1", 100)
    for bad in (dataclasses.replace(s, manifest_hash="WRONG-HASH"), dataclasses.replace(s, epoch_at_snapshot=999999), dataclasses.replace(s, manifest_id="M2"), dataclasses.replace(s, generation_id="gen-X"),
                dataclasses.replace(s, request_id="q-other"), dataclasses.replace(s, feature_id="evil"), dataclasses.replace(s, calibration_id="evil"), dataclasses.replace(s, request_start_ts=1), dataclasses.replace(s, event=ev(ts=999))):
        assert code(r.compare_and_publish, bad, "R") == "ML_SNAPSHOT_NOT_ISSUED_BY_THIS_REGISTRY"
    r2 = reg("M1"); assert code(r2.compare_and_publish, s, "R") == "ML_SNAPSHOT_NOT_ISSUED_BY_THIS_REGISTRY"                      # issued by ANOTHER registry
    assert r.published(ev()) is None and r.compare_and_publish(s, "R").status == GL.PUBLISHED                                       # nothing leaked; the genuine one publishes
    r.append_lifecycle("M2", "SUPERSEDED", 50, "x", "A"); s3 = r.snapshot("q3", ev(ts=300), "M1", 101); assert r.compare_and_publish(s3, "R").status == GL.PUBLISHED      # unrelated generation change tolerated
def test_r30_snapshot_binds_instrument_generation_components_and_request_id_cannot_change_meaning():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1", 100); assert (s.generation_id, s.feature_id, s.target_id, s.calibration_id, s.ood_id) == ("gen-M1", "h-feature_packM1", "h-target_packM1", "h-calibratorM1", "h-ood_support_objectsM1")
    assert code(r.snapshot, "q9", ev(instrument_id="EURUSD"), "M1", 100) == "ML_INSTRUMENT_NOT_IN_MANIFEST_SCOPE" and code(r.snapshot, "q1", ev(ts=999), "M1", 100) == "ML_REQUEST_ID_REUSED_WITH_DIFFERENT_BINDING"
    assert code(r.snapshot, "q8", ev(), "M1") == "ML_SNAPSHOT_START_TS_MISSING" and r.snapshot("q1", ev(), "M1", 100) == s                      # idempotent re-issue of the identical request
def test_r30_reconstruction_needs_both_source_gates_and_is_never_authoritative():
    r = reg("M1")
    for fresh, comp in ((None, None), ("PASS", None), (None, "PASS"), ("PASS", "FAIL"), ("STALE", "PASS"), ("PASS", "pass")):
        x = r.reconstruct_for_event(ev(ts=20), fresh, comp); assert x.outcome == GL.HELD_MISSED_OR_QUARANTINED and x.manifest_id is None, (fresh, comp)
    x = r.reconstruct_for_event(ev(ts=20), "PASS", "PASS"); assert x.outcome == GL.RECONSTRUCTED_CANDIDATE and x.outcome != "RECONSTRUCTED" and "NOT_VERIFIED" in x.reason
    assert r.reconstruct_for_event(ev(ts=20, instrument_id="EURUSD"), "PASS", "PASS").outcome == GL.MISSED                              # instrument isolation applies to reconstruction too
