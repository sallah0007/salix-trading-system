"""R52: invariants of the 100-row PROPOSED A07 disposition record (docs/a07/V232_26S_R52_PROPOSED_DISPOSITION_RECORD.csv). Proposals only: nothing here awards, accepts or clears a gate."""
import csv, pathlib, copy
D = pathlib.Path(__file__).resolve().parents[1] / "docs" / "a07"
rd = lambda f: list(csv.DictReader(open(D / f)))
REC = rd("V232_26S_R52_PROPOSED_DISPOSITION_RECORD.csv")
DISAGREE = ["0030#2", "0056#1", "0073#3", "0076#4", "0078#2", "0078#3", "0079#2", "0080#3", "0096#1", "0099#3", "0113#1", "0113#2", "0126#3", "0162#3", "0186#3", "0220#2", "0221#2", "0223#2", "0224#1", "0249#1", "0258#2"]
LOSS = ["0087#1", "0087#2", "0087#3", "0180#1", "0180#2", "0180#3", "0180#4", "0180#5", "0184#1", "0184#2", "0184#3", "0184#4"]
def key(r): return "%s#%s" % (r["unit_id"][3:], r["qualifier_index"])
def check(rows):
    errs = []
    if len(rows) != 100 or len({(r["unit_id"], r["qualifier_index"]) for r in rows}) != 100: errs.append("not 100 unique rows")
    r47 = {(x["unit_id"], x["qualifier_index"]): x for x in rd("V232_26S_R47_MEMBER_RECONCILIATION.csv")}; r42 = {(x["unit_id"], x["qualifier_index"]): x for x in rd("V232_26S_R42_PER_QUALIFIER_READING.csv")}
    for r in rows:
        k = (r["unit_id"], r["qualifier_index"])
        if r["qualifier_sha256"] != r47[k]["qualifier_sha256"]: errs.append("hash differs " + key(r))
        if r["r42_class"] != r42[k]["class"]: errs.append("class differs " + key(r))
        for f in ("historical_meaning_own_words", "current_controlling_anchor", "oracle_evidence", "discrepancy", "recommended_disposition", "rationale", "exact_source_delta_if_needed", "tracker_code_action"):
            if not r[f].strip(): errs.append("empty %s %s" % (f, key(r)))
        if r["award"] != "NONE: UR_REMAINS": errs.append("award " + key(r))
        if "oracle_acceptance=NONE_V230_global_false_V235_independent_false" not in r["oracle_evidence"]: errs.append("oracle acceptance claim " + key(r))
        if r["recommended_disposition"].startswith("HISTORY_ONLY") and r["current_controlling_anchor"].startswith("NONE") and "GAP" not in r["recommended_disposition"]: errs.append("HISTORY_ONLY on a missing ref alone " + key(r))
        if r["recommended_disposition"].startswith("COVERED_BY") and r["current_controlling_anchor"].startswith("NONE"): errs.append("COVERED_BY without a current anchor " + key(r))
    by = {key(r): r for r in rows}
    for k in DISAGREE + LOSS:
        if not by[k]["discrepancy"] or by[k]["recommended_disposition"].startswith(("PARTIAL__STRENGTHENER_DECISION", "NO_CURRENT_STATEMENT__DECISION")): errs.append("not individually adjudicated " + k)
    return errs
def test_record_is_consistent_and_awards_nothing(): assert check(REC) == []
def test_every_disagreement_and_loss_row_has_an_individual_proposal():
    by = {key(r): r for r in REC}; assert all(k in by for k in DISAGREE + LOSS); assert len({by[k]["recommended_disposition"] + by[k]["discrepancy"] for k in DISAGREE}) == 21
def test_negative_controls_the_check_can_fail():
    bad = copy.deepcopy(REC); bad[0]["award"] = "ACCEPTED"; assert check(bad)
    bad = copy.deepcopy(REC); bad[1]["qualifier_sha256"] = "0" * 64; assert check(bad)
    bad = copy.deepcopy(REC); i = next(i for i, r in enumerate(bad) if key(r) == "0073#3"); bad[i]["recommended_disposition"] = "HISTORY_ONLY"; assert check(bad)
    bad = copy.deepcopy(REC); i = next(i for i, r in enumerate(bad) if key(r) == "0030#2"); bad[i]["recommended_disposition"] = "COVERED_BY_PROPOSED"; assert check(bad)
    assert check(REC[:99])
