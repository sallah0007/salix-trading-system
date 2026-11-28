"""R41: A07 source-coordinate tool. MLCore:N in the R02 ledger is the 1-based index of the NATIVE non-empty paragraph (1692 in the current revision), NOT a rendered-file line.
Usage: python tools/a07_native_paragraphs.py <native MLCore text file (CRLF ok; supplied by the caller, never committed)> <R02 csv> <dispositions csv out>
Checks: (1) 1692 paragraphs; (2) every R02 `historical_range_LF_sha256` equals sha256('\\n'.join(paragraphs[a-1:b]) + '\\n') (LF-terminated); (3) writes one row per R02 qualifier joined to the R41 unit disposition table. No private text is written."""
import csv, hashlib, re, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from a07_r41_dispositions import DISP
CURRENT_LAST = 459          # p458 heading 26.S + p459: Sections 1-26 controlling; later paragraphs are preserved lineage "supporting unless incorporated"
def paragraphs(path): return [x.rstrip("\r") for x in open(path, encoding="utf-8").read().split("\n") if x.strip()]
def main(native, r02, out):
    P = paragraphs(native); assert len(P) == 1692, len(P)
    rows = list(csv.DictReader(open(r02))); ok = 0
    w = csv.writer(open(out, "w", newline=""))
    w.writerow(["unit_id","qualifier_index","hist_locator_native_paragraph","hist_hash_reverified","r02_ref_native_paragraphs","r02_refs_in_current_1_459","r02_refs_historical_460_plus","disposition","current_native_paragraphs","historical_only_difference","oracle_or_implementation","source_owner_role","consequence","recommendation"])
    for r in rows:
        a, b = map(int, re.match(r"MLCore:(\d+)-(\d+)", r["historical_locator"]).groups())
        h = hashlib.sha256(("\n".join(P[a-1:b]) + "\n").encode()).hexdigest(); good = h == r["historical_range_LF_sha256"]; ok += good
        ns = [int(m.group(1)) for m in (re.match(r"MLCore:(\d+)", x.strip()) for x in r["controlling_current_line_refs"].split(";")) if m]
        d = DISP[r["unit_id"]]
        w.writerow([r["unit_id"], r["qualifier_index"], r["historical_locator"], "YES" if good else "NO", ";".join(map(str, ns)), ";".join(str(n) for n in ns if n <= CURRENT_LAST), ";".join(str(n) for n in ns if n > CURRENT_LAST), *d])
    print("paragraphs", len(P), "hash ok", ok, "of", len(rows))
if __name__ == "__main__": main(*sys.argv[1:4])
