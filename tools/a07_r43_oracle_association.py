"""R43: relates each of the 100 R42 per-qualifier readings to the THREE oracle-level extract sources (recovered extract Drive 1Avpm0dFCr5jH-ax6WhPXSXpV4jQMtY4m; ZIP sha256 fd594244...):
V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json (unit role, prior-body verdict, oracle adequacy, full-equivalence statement, adoption), V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339.json (oracle/target hash transitions, declared deltas, the undeclared semantic-loss list) and V235_CROSSWALK_CANDIDATE.json (Manager-proposed crosswalk: disposition, target requirement, current-source RANGES, qualifier-comparison text).
Output is IDENTIFIERS, ranges, hashes and flags only (no governing text copied). It awards NOTHING: V230 global_source_semantic_acceptance/global_oracle_acceptance and V235 independent_acceptance are read from the files and must be False for the run to proceed; hash parity is never used as semantic equivalence.
Usage: python tools/a07_r43_oracle_association.py <extract dir> <R42 per-qualifier csv> <out csv>"""
import csv, hashlib, json, sys, pathlib
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main(ext, r42, out):
    ext = pathlib.Path(ext); f230, f232, f235 = (ext / n for n in ("V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json", "V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339.json", "V235_CROSSWALK_CANDIDATE.json"))
    a = json.load(open(f230)); b = json.load(open(f232)); c = json.load(open(f235))
    assert a["global_source_semantic_acceptance"] is False and a["global_oracle_acceptance"] is False and c["independent_acceptance"] is False, "a source claims acceptance: stop and re-read"
    A = {r["id"]: r for r in a["rows"]}; B = {r["id"]: r for r in b["rows"]}; C = {r["id"]: r for r in c["manager_comparisons"]}
    assert len(A) == len(B) == len(C) == 339
    loss = set(b["V231_undeclared_semantic_losses"]); rows = list(csv.DictReader(open(r42))); res = []
    for r in rows:
        u = r["unit_id"]; x, y, z = A[u], B[u], C[u]
        cur = ";".join("%s:%s-%s" % (s["source_key"], s["line_start"], s["line_end"]) for s in z["current_sources"])
        flags = []
        if u in loss: flags.append("V231_UNDECLARED_SEMANTIC_LOSS_LISTED")
        if y["V231_explicit_delta"]: flags.append("V231_EXPLICIT_DELTA")
        if y["V232_content_modified_relative_to_V231_decoded"]: flags.append("V232_CONTENT_MODIFIED")
        if not y["same_as_V230_exact_plain_oracle"]: flags.append("ORACLE_TEXT_DIFFERS_FROM_V230")
        if z["disposition"] != "INCORPORATED-AT": flags.append("V235_DISPOSITION_" + z["disposition"])
        if "NOT_GLOBALLY_CERTIFIED" in x["V230_oracle_adequacy"] or "per-claim" in x["V230_oracle_adequacy"]: flags.append("ORACLE_NOT_GLOBALLY_CERTIFIED_PER_CLAIM_MAPPING_REQUIRED")
        if r["class"] in ("C", "P") and not z["current_sources"]: flags.append("R42_READS_CURRENT_BUT_V235_LISTS_NO_CURRENT_SOURCE")
        if r["class"] in ("H", "L", "N", "R") and z["disposition"] == "INCORPORATED-AT": flags.append("R42_READS_NOT_CURRENT_BUT_V235_SAYS_INCORPORATED_AT")
        res.append(dict(unit_id=u, qualifier_index=r["qualifier_index"], r42_class=r["class"], v230_unit_role=x["unit_role"], v230_prior_verdict=x["prior_body_comparison_verdict"], v235_disposition=z["disposition"], v235_target=z["target_requirement_id"], v235_current_source_ranges=cur,
                        v235_qualifier_comparison_sha256=hashlib.sha256(z["qualifier_comparison"].encode()).hexdigest(), v232_oracle_hash_equals_v230=y["same_as_V230_exact_plain_oracle"], flags=";".join(flags), oracle_acceptance="NONE_V230_global_false_V235_independent_false", status="UR_REMAINS__NO_AWARD__HASH_PARITY_IS_NOT_SEMANTICS"))
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0])); w.writeheader(); w.writerows(res)
    from collections import Counter
    print("sources sha256:", {f.name: sha(f) for f in (f230, f232, f235)}); print("qualifiers:", len(res), "units:", len({r["unit_id"] for r in res}))
    print("flag counts:", dict(Counter(fl for r in res for fl in r["flags"].split(";") if fl)))
if __name__ == "__main__": main(*sys.argv[1:4])
