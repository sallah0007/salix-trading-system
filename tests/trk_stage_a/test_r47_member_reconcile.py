import importlib.util, pathlib, tempfile, pytest
P = pathlib.Path(__file__).resolve().parents[2] / "tools" / "a07_r47_member_reconcile.py"
spec = importlib.util.spec_from_file_location("a07_r47", P); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_refuses_members_with_wrong_hash():
    with tempfile.TemporaryDirectory() as d:
        for n in m.EXPECTED:
            (pathlib.Path(d) / n).write_text("{}")
        with pytest.raises(AssertionError, match="member hash mismatch"):
            m.main(d, str(pathlib.Path(d) / "o.csv"))


def test_ref_line_parser_and_tokens():
    assert m.lines_of(["MLCore:297-299", "MLCore:301"]) == {297, 298, 299, 301}
    assert m.lines_of(["MLCore:489–490"]) == {489, 490}
    assert "the" not in m.toks("the held-back pass") and "held" in m.toks("the held-back pass")


def test_expected_hashes_are_four_sha256():
    assert len(m.EXPECTED) == 4 and all(len(h) == 64 for h in m.EXPECTED.values())
