import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker import lifecycle_status_event as L
EVID = {"SUBJECT_TYPE": "FEATURE_VERSION", "CREATED_AT": 5, "AVAILABLE_ASOF": 5, "EFFECTIVE_AT": 4, "MACHINE_REASON_CODE": "RC", "MACHINE_REASON_CODE_VERSION": "1",
        "DECISION_CONTEXT_ID": "DC-1", "AUTHORITY_STATE": "AUTH", "RELATED_EVIDENCE_REFS": ["e1"]}
def committed(kind, body):
    j = ObjectStoreJournal(InMemoryObjectStore(), "ns", "w"); j.acquire_epoch(); return j.append(j.head(), kind, body)
ACC = {"feature_key": "k", "feature_version": "v1"}
def code(fn, *a):
    try: return fn(*a)
    except Refusal as e: return e.code
class T(unittest.TestCase):
    def test_maps_derived_and_boundary_fields(self):
        r = committed("WITHDRAWN", {"feature_key": "k", "feature_version": "v1", "reason": "x"})
        ev = L.journal_to_status_event(r, "PUBLISHABLE", dict(EVID), True)
        self.assertEqual((ev["STATUS_EVENT_ID"], ev["EVENT_HASH"], ev["SUBJECT_ID"], ev["NEW_STATE"], ev["PRIOR_STATE"]), (r.record_hash, r.record_hash, "k", "WITHDRAWN", "PUBLISHABLE"))
    def test_each_residual_field_is_required_never_defaulted(self):
        r = committed("WITHDRAWN", {"feature_key": "k", "feature_version": "v1", "reason": "x"})
        for k in L.FROM_BOUNDARY:
            e = dict(EVID); del e[k]
            self.assertEqual(code(L.journal_to_status_event, r, "PUBLISHABLE", e, True), "STATUS_EVENT_FIELD_MISSING", k)
    def test_first_transition_needs_prior_state_from_boundary(self):
        r = committed("WITHDRAWN", {"feature_key": "k", "feature_version": "v1", "reason": "x"})
        self.assertEqual(code(L.journal_to_status_event, r, None, dict(EVID), True), "STATUS_EVENT_FIELD_MISSING")
        self.assertEqual(L.journal_to_status_event(r, None, dict(EVID, PRIOR_STATE="S0"), True)["PRIOR_STATE"], "S0")
    def test_conflicting_boundary_evidence_refused(self):
        r = committed("WITHDRAWN", {"feature_key": "k", "feature_version": "v1", "reason": "x"})
        self.assertEqual(code(L.journal_to_status_event, r, "PUBLISHABLE", dict(EVID, SUBJECT_ID="other"), True), "BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD")
        self.assertEqual(code(L.journal_to_status_event, r, "PUBLISHABLE", dict(EVID, PRIOR_STATE="X"), True), "BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD")
    def test_unknown_context_fails_closed_and_non_lifecycle_kind_refused(self):
        r = committed("WITHDRAWN", {"feature_key": "k", "feature_version": "v1", "reason": "x"})
        self.assertEqual(code(L.journal_to_status_event, r, "PUBLISHABLE", dict(EVID), False), "STATUS_WITHOUT_REQUIRED_CONTEXT")
        self.assertEqual(code(L.journal_to_status_event, committed("OTHER", {"a": 1}), None, dict(EVID), True), "NOT_A_LIFECYCLE_TRANSITION_KIND")
if __name__ == "__main__": unittest.main()
