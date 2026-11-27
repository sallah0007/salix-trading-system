"""Drift guard: proposal docs must list exactly the code-side field sets (they are PROPOSALS, not authority)."""
import pathlib
from tests.trk_stage_a.test_composer_s27_coverage import ABSENT
from stage_a.fw import descriptor_crosswalk as X
D = pathlib.Path(__file__).resolve().parents[2] / "docs" / "proposals"
def test_d6_doc_lists_each_absent_field_once_as_a_row():
    t = (D / "D6_composer_s27_mapping.md").read_text()
    rows = [l for l in t.splitlines() if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    assert len(rows) == len(ABSENT) == 27
    for i, f in enumerate(ABSENT, 1): assert rows[i - 1].split("|")[2].strip() == f
    assert "NOT runtime authority" in t
def test_fw_doc_lists_ten_descriptors_with_source_status():
    t = (D / "FW_descriptor_bindings.md").read_text()
    for f in X.FIELDS: assert "| %s | %s |" % (f, X.SOURCE_STATUS[f]) in t
def test_every_proposal_doc_is_labelled_proposed():
    for p in D.glob("*.md"): assert "PROPOSAL" in p.read_text().upper() or "requests only" in p.read_text(), p
