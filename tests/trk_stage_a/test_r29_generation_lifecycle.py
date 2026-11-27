import dataclasses, threading, pytest
from stage_a.ml import generation_lifecycle as GL
from stage_a.errors import Refusal

def man(i="M1", **drop):
    comps = tuple((n, "h-" + n + i) for n in GL.MIN_COMPONENTS if n not in drop); return GL.CertifiedGenerationManifest(i, "mh-" + i, comps)
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
    assert code(r.register_manifest, GL.CertifiedGenerationManifest("M1", "other", man().components)) == "ML_MANIFEST_IMMUTABLE"
    assert code(r.register_manifest, GL.CertifiedGenerationManifest("M2", "h", (("a", "b"), ("a", "c")))) == "ML_MANIFEST_COMPONENT_MALFORMED"
def test_eligibility_needs_manifest_and_latest_ledger_state_and_ledger_is_append_only_monotonic():
    r = GL.GenerationRegistry(); r.register_manifest(man()); assert not r.eligible("M1")                 # no ledger state: not eligible
    r.append_lifecycle("M1", "CANDIDATE", 5, "c", "A"); assert not r.eligible("M1")
    e = r.append_lifecycle("M1", "COMPLETE_CERTIFIED", 6, "c", "A"); assert r.eligible("M1") and e.epoch == 2
    r.append_lifecycle("M1", "REVOKED", 9, "bad", "A"); assert not r.eligible("M1") and r.eligible("M1", 7)   # as-of history preserved
    assert [x.epoch for x in r.ledger()] == [1, 2, 3] and code(r.append_lifecycle, "M1", "BOGUS", 9, "r", "a") == "ML_LIFECYCLE_ENTRY_MALFORMED"
    assert code(r.append_lifecycle, "M1", "SUPERSEDED", 1, "r", "a") == "ML_LIFECYCLE_TS_REGRESSED" and code(r.append_lifecycle, "NOPE", "REVOKED", 20, "r", "a") == "ML_LIFECYCLE_FOR_UNREGISTERED_MANIFEST"
def test_publish_positive_control_and_idempotence():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1"); assert r.compare_and_publish(s, "R").status == GL.PUBLISHED
    assert r.compare_and_publish(s, "R2").reason == "ALREADY_PUBLISHED_IDEMPOTENT" and r.published(ev())[1] == "R"
def test_revocation_between_snapshot_and_publish_rejects_and_never_regenerates_under_newer_generation():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1")
    r.append_lifecycle("M1", "REVOKED", 50, "bad", "A"); r.register_manifest(man("M2")); r.append_lifecycle("M2", "COMPLETE_CERTIFIED", 60, "c", "A")
    o = r.compare_and_publish(s, "R"); assert o.status == GL.REJECTED_QUARANTINED and r.published(ev()) is None
    assert r.retry_publish(s, "R").reason == "NO_RETROACTIVE_REGENERATION"                           # still no publish
    assert r.compare_and_publish(r.snapshot("q2", ev(), "M2"), "R").reason == "EVENT_ALREADY_FAILED_NO_REGENERATION"    # a newer generation may NOT fill the failed slot
    assert r.compare_and_publish(r.snapshot("q3", ev(ts=200), "M2"), "N").status == GL.PUBLISHED     # ...but is a NEW event with its own identity
def test_supersession_is_discarded_not_quarantined_and_unrelated_generation_epoch_change_is_tolerated():
    r = reg("M1", "M2"); s = r.snapshot("q", ev(), "M1"); r.append_lifecycle("M2", "SUPERSEDED", 40, "old", "A")                  # unrelated manifest changes the global epoch
    assert r.compare_and_publish(s, "R").status == GL.PUBLISHED                                       # M1's own state unchanged: positive control
    s2 = r.snapshot("q2", ev(ts=101), "M1"); r.append_lifecycle("M1", "SUPERSEDED", 41, "x", "A")
    assert r.compare_and_publish(s2, "R").status == GL.REJECTED_DISCARDED
def test_atomic_compare_and_publish_revocation_injected_at_the_commit_point_cannot_split_check_from_commit():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1"); done = []
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
    assert r.reconstruct_for_event(ev(ts=20)) == GL.Reconstruction("RECONSTRUCTED", "M1")              # certified at that time
    x = r.reconstruct_for_event(ev(ts=55)); assert x.outcome == GL.MISSED and x.manifest_id is None     # nothing eligible then; M2 (current) must NOT be returned
    assert r.reconstruct_for_event(ev(ts=5)).outcome == GL.MISSED                                       # before any certification
    r2 = reg("A", "B"); assert r2.reconstruct_for_event(ev(ts=100)).outcome == GL.NOT_PROVABLY_RECONSTRUCTABLE      # ambiguous
    assert code(r.reconstruct_for_event, ev(knowledge_boundary=None)) == "ML_EVENT_IDENTITY_INCOMPLETE"
def test_snapshot_requires_eligible_generation_and_complete_event_identity():
    r = reg("M1"); assert code(r.snapshot, "q", ev(instrument_id=""), "M1") == "ML_EVENT_IDENTITY_INCOMPLETE"
    r.append_lifecycle("M1", "REVOKED", 20, "x", "A"); assert code(r.snapshot, "q", ev(), "M1") == "ML_GENERATION_NOT_SERVING_ELIGIBLE"
    assert code(r.compare_and_publish, "not a snapshot", "R") == "ML_PUBLISH_NEEDS_REQUEST_SNAPSHOT"

def test_epoch_change_alone_fails_the_fence_even_if_the_generation_is_eligible_again_at_commit():
    r = reg("M1"); s = r.snapshot("q", ev(), "M1")
    r.append_lifecycle("M1", "SUPERSEDED", 30, "x", "A"); r.append_lifecycle("M1", "COMPLETE_CERTIFIED", 31, "re", "A")      # eligible again, but the lifecycle epoch moved since the snapshot
    assert r.eligible("M1") and r.compare_and_publish(s, "R").status == GL.REJECTED_DISCARDED
