from stage_a.errors import Refusal
import pytest
from stage_a.tracker import version_relationship as v

def test_missing_evidence_is_uncomputable_only_when_genuine():
    assert v.classify_not_computed(v.EVIDENCE_GENUINELY_MISSING) == v.UNCOMPUTABLE

@pytest.mark.parametrize("r", [v.WORK_NOT_DONE, v.SOFTWARE_FAILURE])
def test_skipped_work_or_failure_is_uncomputed_never_uncomputable(r):
    assert v.classify_not_computed(r) == v.UNCOMPUTED
    assert v.relationship_consequences(v.classify_not_computed(r))["blocks_supersession_claim"] is True

def test_unknown_reason_refuses():
    with pytest.raises(Refusal):
        v.classify_not_computed("whatever")

def test_distinct_consequences():
    assert v.relationship_consequences(v.UNCOMPUTED) != v.relationship_consequences(v.UNCOMPUTABLE)
