"""R40: classify each MLCore ref in the R02 CSV by ACTUAL authority region (not the field label).
Regions come from structure markers in current MLCore (read from Drive by the author; line numbers match CSV).
Writes a derived CSV; does not alter or duplicate the R02 inventory. No governing text is copied."""
import csv, re, sys, collections
ROOT_CURRENT = [(203,203),(208,211),(265,265),(297,319),(405,424)]  # root-designated applicable ranges
def region(n):
    if n <= 20: return "NAV_CURRENTNESS_POINTER"
    if n <= 160: return "V1_16_OVERLAY_CURRENT_FREEZE_STATUS_ONLY"
    if n <= 364: return "V1_12_CONTROLLING_PRE_FREEZE_OVERLAY"
    if n <= 502: return "V1_11_OVERLAY_SUPERSEDED_BY_V1_12_WHERE_CONFLICT"
    return "RETAINED_V1_10_AND_EARLIER_HISTORICAL"
def root(n): return any(a <= n <= b for a, b in ROOT_CURRENT)
def main(src, out):
    rows = list(csv.DictReader(open(src)))
    w = csv.writer(open(out, "w", newline=""))
    w.writerow(["unit_id","qualifier_index","n_refs","regions","root_designated_refs","actual_current_refs","disposition_class","historical_region_refs","lexical_support","source_owner_role","consequence","recommendation"])
    agg = collections.Counter(); tot = 0
    for r in rows:
        ns = [int(m.group(1)) for m in (re.match(r"MLCore:(\d+)", x.strip()) for x in r["controlling_current_line_refs"].split(";")) if m]
        regs = collections.Counter(region(n) for n in ns)
        rd = [n for n in ns if root(n)]
        cur = [n for n in ns if region(n) in ("NAV_CURRENTNESS_POINTER","V1_16_OVERLAY_CURRENT_FREEZE_STATUS_ONLY","V1_12_CONTROLLING_PRE_FREEZE_OVERLAY") or root(n)]
        for n in ns: agg[region(n)] += 1; tot += 1
        if not ns: dc = "NO_CURRENT_REF_IN_R02_LEXICAL_SCREEN__INSUFFICIENT_EVIDENCE_NOT_ABSENCE"
        elif not cur: dc = "HISTORICAL_REGION_ONLY__DIFFERENCE_TO_BE_NAMED_BY_OWNER"
        elif r["lexical_support"] == "LEXICAL_SUPPORT_WEAK": dc = "CURRENT_REGION_REF__LEXICAL_WEAK__OWNER_MUST_CONFIRM_EQUIVALENCE"
        else: dc = "CURRENT_REGION_REF__LEXICAL_NOT_WEAK__OWNER_MUST_CONFIRM_EQUIVALENCE"
        w.writerow([r["unit_id"], r["qualifier_index"], len(ns), ";".join(f"{k}={v}" for k,v in sorted(regs.items())),
                    ";".join(map(str,rd)), ";".join(map(str,cur)), dc,
                    ";".join(str(n) for n in ns if n not in cur), r["lexical_support"],
                    "ML source owner (MLCore) — Manager records disposition in Drive",
                    "A07 coverage stays OPEN for this qualifier; no tracker behaviour changed",
                    "owner to name exact current clause + oracle repair, or the exact historical-only difference"])
    print(tot, dict(agg))
if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
