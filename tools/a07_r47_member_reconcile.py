"""R47: per-qualifier reconciliation from the four ORIGINAL oracle JSON members (transport A07_EXACT_ORACLE_MEMBERS_TRANSPORT).
Decodes/verifies nothing itself: pass the directory holding the four members; every member's sha256 is checked against the values recorded in the
transport header (EXPECTED below) and the run stops on any mismatch. Output is IDENTIFIERS, ranges, hashes, counts and flags ONLY (no governing text).
It awards NOTHING: acceptance fields in V230/V235 must read false or the run stops. A lexical overlap number is a LEAD, never a verdict.
Usage: python -I tools/a07_r47_member_reconcile.py <member dir> <out csv>"""
import csv, hashlib, json, pathlib, re, sys
EXPECTED = {
    "V235_CROSSWALK_CANDIDATE.json": "282d0fd2d541562ca956b973e9aa9b4888ee302ca06d37cf1948cd382f9ad7fb",
    "V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json": "1287086de20f5c0f25bc3250e9bce05d1d916f54d7cd0cc98c47b8183d7cd72d",
    "V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339.json": "cc0c27bea542aeaea674a9bae0b0173ee2a54498f7cad5f641db86f2941787d0",
    "V232_FINITE_41_UNIT_QUALIFIER_RESIDUAL.json": "bfee4c8a4aa877f9ba436e1142184f790d0442a3e8942f7b57e82b724441fe3e",
}
STOP = set("a an and any are as at be by do does each every for from has have in is it its may must no not of on or only the to with without that this these those when where which who will".split())
REF = re.compile(r"MLCore\s*:?\s*(\d+)(?:\s*[-–]\s*(\d+))?")


def toks(s):
    return {w for w in re.findall(r"[a-z0-9_]+", s.lower()) if w not in STOP and len(w) > 2}


def lines_of(ref_list):
    out = set()
    for r in ref_list:
        for m in REF.finditer(r):
            a = int(m.group(1)); b = int(m.group(2) or a)
            out.update(range(a, b + 1))
    return out


def main(d, out):
    d = pathlib.Path(d)
    for n, h in EXPECTED.items():
        got = hashlib.sha256((d / n).read_bytes()).hexdigest()
        assert got == h, "member hash mismatch: %s" % n
    a = json.load(open(d / "V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json"))
    b = json.load(open(d / "V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339.json"))
    c = json.load(open(d / "V235_CROSSWALK_CANDIDATE.json"))
    r = json.load(open(d / "V232_FINITE_41_UNIT_QUALIFIER_RESIDUAL.json"))
    assert a["global_source_semantic_acceptance"] is False and a["global_oracle_acceptance"] is False and c["independent_acceptance"] is False
    assert r["population"] == 41 and all(x["runtime"] == "NOT RUN" for x in r["units"])
    B = {x["id"]: x for x in b["rows"]}; C = {x["id"]: x for x in c["manager_comparisons"]}; A = {x["id"]: x for x in a["rows"]}
    loss = set(b["V231_undeclared_semantic_losses"]); rows = []
    for x in r["units"]:
        u = x["id"]; cm = C[u]; cur = set()
        for s in cm["current_sources"]:
            cur.update(range(s["line_start"], s["line_end"] + 1))
        for i, q in enumerate(x["qualifier_dispositions"], 1):
            p = q.get("prior_working_map") or {}
            refs = p.get("current_source_line_refs") or []
            loc = p.get("current_locus") or p.get("current_locus_or_named_omission") or ""
            pl = lines_of(refs) | lines_of([loc])
            ev = p.get("source_evidence") or []
            if not pl: rel = "NO_LINE_REF_IN_PRIOR_MAP"
            elif pl <= cur: rel = "ALL_PRIOR_REFS_INSIDE_V235_RANGES"
            elif pl & cur: rel = "SOME_PRIOR_REFS_INSIDE_V235_RANGES"
            else: rel = "NO_PRIOR_REF_INSIDE_V235_RANGES"
            qt = toks(q["qualifier"]); ct = toks(cm["qualifier_comparison"])
            ov = len(qt & ct) / len(qt) if qt else 0.0
            fl = []
            if u in loss: fl.append("V231_UNDECLARED_SEMANTIC_LOSS_LISTED")
            if not B[u]["same_as_V230_exact_plain_oracle"]: fl.append("ORACLE_TEXT_DIFFERS_FROM_V230")
            if cm["disposition"] != "INCORPORATED-AT": fl.append("V235_" + cm["disposition"])
            rows.append(dict(unit_id=u, qualifier_index=i, qualifier_sha256=hashlib.sha256(q["qualifier"].encode()).hexdigest(),
                             v232_status=q["status"][:34], prior_map_present=bool(p), v235_disposition=cm["disposition"],
                             v235_cur_line_count=len(cur), prior_ref_line_count=len(pl), prior_vs_v235_ranges=rel,
                             v232_evidence_items=len(ev), v232_evidence_in_unit_cited=sum(1 for e in ev if e.get("in_unit_cited_ranges")),
                             v232_evidence_is_historical_not_controlling=sum(1 for e in ev if e.get("is_historical_element_not_controlling_equivalent")),
                             v235_comparison_sha256=hashlib.sha256(cm["qualifier_comparison"].encode()).hexdigest(),
                             lexical_overlap_lead=round(ov, 2), flags=";".join(fl),
                             v230_oracle_adequacy_sha256=hashlib.sha256(A[u]["V230_oracle_adequacy"].encode()).hexdigest()[:16],
                             status="UR_REMAINS__NO_AWARD__SOURCE_INTEGRITY_IS_NOT_EQUIVALENCE"))
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print("qualifiers", len(rows), "units", len(x for x in [1]) if False else len({q["unit_id"] for q in rows}))
    print(dict(Counter(q["prior_vs_v235_ranges"] for q in rows)))
    print("NL-0178 in 41-unit residual:", "NL-0178" in {q["unit_id"] for q in rows}, "| in V232 loss list:", "NL-0178" in loss)


if __name__ == "__main__":
    main(*sys.argv[1:3])
