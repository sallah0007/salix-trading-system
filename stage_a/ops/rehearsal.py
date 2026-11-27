"""E-10: migration / rollback as an ORDERED, GATED, NON-DESTRUCTIVE plan object. It performs no deployment, activates nothing, grants no permission and records no gate clearance: each phase must be marked complete by an explicit `record_phase` call from a caller who holds that decision, in order, and a later phase can never run before an earlier one.
Rollback lists actions only; it never deletes or rewrites canonical history (`never_deleted`)."""
from ..errors import Refusal
PHASES = ("add_stage_a_packages_without_changing_tracker_identity", "deploy_readonly_schema_hash_reference_tests", "object_store_coordination_adapter_in_shadow_namespace", "build_projections_from_test_canonical_journal", "enable_composer_candidate_path_only",
          "enable_tracker_materializer_candidate_writes_only", "enable_independent_verifier", "enable_acceptor_in_nonproduction_namespace", "enable_gateway_health_fw_ml_adapters_after_their_phase_gates", "run_whole_stage_a_replay_rebuild_isolation_rehearsal")
# R3 E10-M1 (read live, para 1073-1083) inserts an EPOCH FENCE before the prior release is restored; tokens issued before the advance are invalid afterwards.
ROLLBACK = ("quiesce_dispatch_and_stop_stage_a_workers", "advance_coordination_epoch_and_durably_verify_new_head", "revoke_stage_a_service_principals_and_credentials", "cease_new_stage_a_manifests_and_bindings", "restore_previous_software_release", "discard_and_rebuild_postgresql_projections", "retain_all_canonical_artifacts_and_transitions_append_only", "supersede_accepted_transitions_by_governed_successor_never_erase")
class MigrationPlan:
    never_deleted = ("canonical artifacts", "coordination transitions", "status events", "gateway bindings and non-delivery", "health evidence")
    def __init__(self): self._done = []
    def record_phase(self, phase: str, evidence_ref: str):
        i = len(self._done)
        if i >= len(PHASES) or phase != PHASES[i]: raise Refusal(phase, code="MIGRATION_PHASE_OUT_OF_ORDER")
        if not isinstance(evidence_ref, str) or not evidence_ref: raise Refusal(phase, code="MIGRATION_PHASE_EVIDENCE_MISSING")
        self._done.append((phase, evidence_ref))
    def completed(self): return tuple(self._done)
    def next_phase(self): return PHASES[len(self._done)] if len(self._done) < len(PHASES) else None
    def rollback_actions(self): return ROLLBACK
class RollbackRun:
    """Ordered rollback record (no action is executed here). `restore_previous_software_release` is refused until the epoch advance has been recorded WITH evidence of the durable HEAD verification; an out-of-order action is refused."""
    def __init__(self): self._done = []
    def record(self, action: str, evidence_ref: str):
        i = len(self._done)
        if i >= len(ROLLBACK) or action != ROLLBACK[i]: raise Refusal(action, code="ROLLBACK_ACTION_OUT_OF_ORDER")
        if not isinstance(evidence_ref, str) or not evidence_ref: raise Refusal(action, code="ROLLBACK_EVIDENCE_MISSING")
        self._done.append((action, evidence_ref))
    def completed(self): return tuple(self._done)
    def epoch_fenced(self): return any(a == ROLLBACK[1] for a, _ in self._done)
