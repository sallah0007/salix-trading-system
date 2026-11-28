"""R42: per-QUALIFIER Coder reading table (supersedes the R41 unit-level table, which equated qualifiers sharing a paragraph; that was a limit of the R02 CSV, not absent source input).
Inputs (supplied by the caller, never committed): native MLCore text (1692 non-empty paragraphs), the recovered extract's V232_FINITE_41_UNIT_QUALIFIER_RESIDUAL.json (each qualifier's exact wording), and the R02 CSV (inventory + historical range hashes).
Output rows carry: unit, qualifier index, SHA-256 of the exact qualifier wording (proves association without copying governing text), re-verified range hash, my class, current native paragraphs (1-459 = controlling Sections 1-26 per p456-459; >459 = preserved lineage), a short identifier-only note.
Classes: C current text states the proposition; P current states the core, the qualifier's field/quantifier/surface strengthening is historical-only; H no statement found in 1-459 (keyword + reading); L stated only in the preserved-lineage region (>459), incorporation is the p456-459 question; O proposition present but the target oracle does not test it; N process/binding note with no behaviour duty; R already repaired (not repeated).
Every class is a CODER READING: no equivalence award; all 100 UR remain until accepted source-backed dispositions."""
import csv, hashlib, json, re, sys
C, P, H, L, O, N, R = "C", "P", "H", "L", "O", "N", "R"
T = {
 ("NL-0098",1): (P,"103;158;250","UPSTREAM_MODEL_ID present; UPSTREAM_MODEL_VERSION not"), ("NL-0098",2): (P,"250;296","fit-window/evidence identity present; binding to the exact upstream artifact not stated"), ("NL-0098",3): (P,"247;268;408;409","forecast/as-of fields present; no upstream causal-generation-method statement"),
 ("NL-0225",1): (N,"343;361","V1.4 full-system-regression process note; superseded by proportionate review wording (p343/26.R); oracle does not test the 15-domain list"), ("NL-0263",1): (N,"343;361","V1.6 process note, same as NL-0225"),
 ("NL-0087",1): (C,"327;330;333","coverage/abstention reported"), ("NL-0087",2): (H,"","PERFORMANCE_WHEN_PREDICTING and suppressed-case profile: none in 1-459"), ("NL-0087",3): (C,"274","abstention policy inside governed selection chronology"),
 ("NL-0180",1): (C,"297","manifest immutable; lifecycle separate"), ("NL-0180",2): (C,"298;301","state set and REVOKED != SUPERSEDED"), ("NL-0180",3): (P,"302;309","revoked never serving-eligible even if hash-valid; the seven named services / load-vs-serve split not enumerated"), ("NL-0180",4): (P,"302","fail closed/no backward walk present; 'alerts' not"), ("NL-0180",5): (C,"303;318","forensic read-only mode"),
 ("NL-0184",1): (P,"309;311","atomic promotion + compare-and-publish; 'pointer alone insufficient' not stated"), ("NL-0184",2): (H,"361","no clause requires every consumer to validate cached generation identity on each read/use; only the stale-caches test family is named"), ("NL-0184",3): (P,"310;311;361","snapshot/fence present; stale-cache invalidation before serving and N/N+1 visibility not stated"), ("NL-0184",4): (C,"316;318","original-event history and revoked forensic restriction"),
 ("NL-0030",1): (P,"298;310;313;319","epoch/fence and watermark present; answer-specific resolved-through identity on a reconstruction answer not"), ("NL-0030",2): (H,"","answer-specific resolved-through identity available to caller: only p543 (lineage region)"),
 ("NL-0034",1): (C,"361","mandatory test family named"), ("NL-0034",2): (O,"313;319;361","duties present; oracle lacks stale-reconstruction-answer with otherwise complete slice and lagged replica/authority change"),
 ("NL-0038",1): (C,"326;327;330","terminal events and separate visibility"), ("NL-0038",2): (P,"330;333","distinctness in storage/analysis/dashboards/exports not enumerated; scorecard only"),
 ("NL-0042",1): (C,"203","FORWARD_WALK_REOPEN_REQUIRED = NO bound; no executable portability PASS implied"),
 ("NL-0056",1): (H,"250;253","no clause on raw-observation retention versus selective model use"), ("NL-0056",2): (P,"250;398","REDUNDANCY_GROUP identity present; a redundancy TEST is not required as such"), ("NL-0056",3): (P,"47;51","ownership split stated at document level"),
 ("NL-0063",1): (P,"424","no-weakening stated for payload semantics only; the general strengthen-not-weaken sentence is historical"),
 ("NL-0065",1): (O,"272;280;383","classification/retention clauses present; oracle is rename-only, lacks missing-class and removed-failure cases"),
 ("NL-0073",1): (C,"391","agreement not independent confirmation"), ("NL-0073",2): (C,"391","one correlation matrix not sufficient"), ("NL-0073",3): (H,"","diversity by target/model class: none in 1-459"),
 ("NL-0076",1): (P,"250","metadata named; 379 grouping interpretive"), ("NL-0076",2): (C,"379","dependency grouping interpretive, not independent hypotheses"), ("NL-0076",3): (P,"128;168","cross-program multiplicity accounting; 'search breadth fully recorded' not in these words"), ("NL-0076",4): (H,"","no clause on shrinking the multiplicity denominator without a justified method; locator repair already made (not repeated)"),
 ("NL-0078",1): (C,"247","exact definition"), ("NL-0078",2): (L,"487;488;489","reconstruction must be pre-registered and marked: stated only in lineage region"), ("NL-0078",3): (L,"489;490","exclusion from causal CONFIRMATORY use only; D23 scope open"),
 ("NL-0079",1): (P,"236;237;239;250","provenance/dependency metadata present; a versioned contract for EVERY information-altering stage not stated"), ("NL-0079",2): (H,"250;256","dependency interval named; composed non-scalar interval not stated"),
 ("NL-0080",1): (P,"273;346","mutation tests named; generated-stress vs transparent vs final family split not instantiated"), ("NL-0080",2): (C,"174;175;176;276","held-back exposure governed/versioned; redesign consumes"), ("NL-0080",3): (H,"","'held-back pass necessary where required, never universal robustness': none"),
 ("NL-0096",1): (R,"265","ML265 NO MODEL valid outcome: already repaired"), ("NL-0096",2): (C,"208;211;393","no forced profitable model / no engine control"),
 ("NL-0099",1): (C,"286","pocket claims need pocket support; no universal threshold"), ("NL-0099",2): (P,"286;400","POCKET_SUPPORT_STATE and its component list not named"), ("NL-0099",3): (N,"","range/body difference noted by reviewer is not an obligation"),
 ("NL-0113",1): (H,"335;336;47","no 'self-contained and authoritative' portability clause"), ("NL-0113",2): (H,"","no 'supporting analysis not required to implement' clause"),
 ("NL-0122",1): (C,"208;209;210;211","purpose/market-intelligence-only/no engine control/future authority"),
 ("NL-0126",1): (C,"2;203;346","frozen FW contract not reopened"), ("NL-0126",2): (C,"225;227;228;339","instance by namespace/interface"), ("NL-0126",3): (H,"203","203 says no reopen required now; the conditional Owner-governed reopen path for a demonstrated XAUUSD-only defect is absent"),
 ("NL-0143",1): (C,"236;404","artifacts instrument-qualified"), ("NL-0143",2): (P,"241;404","ARTIFACT_INSTRUMENT_SCOPE not named; missing scope metadata fails closed (p241)"),
 ("NL-0162",1): (C,"297;298;299","load only certified/eligible"), ("NL-0162",2): (C,"309;310;361","no component mixing; same snapshot"), ("NL-0162",3): (L,"1329","governed compatibility-contract exception stated only in lineage; current is stricter or silent"),
 ("NL-0167",1): (C,"237;239","FIT_INSTRUMENT_SET"), ("NL-0167",2): (P,"241;340","mismatch fails closed; 'before EACH use' during sequential batch not stated"),
 ("NL-0174",1): (C,"240;294","separate research class"), ("NL-0174",2): (P,"260;333;334","class visible in scorecard; artifact field and value set (open Q03) not defined"), ("NL-0174",3): (C,"294;340","not through ordinary path"),
 ("NL-0186",1): (P,"323;361","immutable prospective record + partiality test family; record-level all-or-nothing not stated"), ("NL-0186",2): (P,"310;323;324","identity fields exist; all-or-nothing field set unbound"), ("NL-0186",3): (H,"361","no reader/reconciler/dashboard exclusion of partial records; oracle is narrower"),
 ("NL-0187",1): (C,"334","never visually indistinguishable"), ("NL-0187",2): (P,"333","Owner-review minimum, not a field on EVERY displayed contribution"),
 ("NL-0199",1): (C,"316","original generation"), ("NL-0199",2): (C,"303;318","revoked read-only forensic"), ("NL-0199",3): (P,"315;316","forensic audit mode exists; binding to recorded historical identity stated for replay/reconciliation only"),
 ("NL-0200",1): (C,"324","deterministic key; identical retry idempotent"), ("NL-0200",2): (P,"324","'governed identity' without the five-field minimum or global uniqueness"), ("NL-0200",3): (C,"328","counters per logical event not per retry"),
 ("NL-0220",1): (C,"304","ancestry survives fine-tune/reserialize/prune/distill"), ("NL-0220",2): (H,"304","DERIVED_FROM_REVOKED_GENERATION_ID metadata and derivation scope not named"), ("NL-0220",3): (P,"303","read-only audit mode; no-laundering sentence absent"),
 ("NL-0221",1): (C,"304","specific review gate"), ("NL-0221",2): (H,"304","reason + documented determination not in current"), ("NL-0221",3): (C,"304;305","new IDs/weights do not make a candidate clean"),
 ("NL-0223",1): (C,"298;323","immutable records; append-only lifecycle"), ("NL-0223",2): (H,"319","mandatory annotation on the affected object not found; current is dynamic trust resolution (distinct mechanism)"),
 ("NL-0224",1): (N,"319;361","follows NL-0223: annotation-vs-dynamic-trust is the same open question"),
 ("NL-0242",1): (P,"319;333","stale derived views cannot masquerade; per-artifact freshness carrier not required"), ("NL-0242",2): (C,"298;319","epoch + machine-checkable watermark"), ("NL-0242",3): (P,"316;319","dynamic read is an alternative mechanism"),
 ("NL-0249",1): (R,"405;408;409;424","ML405-424 already repaired"), ("NL-0249",2): (P,"405;424","target/horizon in payload; source-event and governed knowledge-time boundary composition UR"), ("NL-0249",3): (C,"313;316","reconstruct from original identity, no current-pointer fallback"),
 ("NL-0250",1): (P,"310;313;316","covers crash-before-snapshot; redelivery/catch-up/backlog not named"), ("NL-0250",2): (C,"299;310;313;316","original-time eligibility"), ("NL-0250",3): (C,"298;313","append-only history"),
 ("NL-0258",1): (C,"298;319","epoch + watermark"), ("NL-0258",2): (H,"319","'resolver resolved-through version' not stated"), ("NL-0258",3): (P,"319","caller-determinable coverage unbound"),
 ("NL-0262",1): (O,"319;361","freshness family named; oracle does not inject resolver/index lag"), ("NL-0262",2): (C,"319;333","stale watermark/epoch detected"),
 ("NL-0266",1): (P,"313","slice completeness gate present; how the ledger proves closure is unbound"),
}
assert len(T) == 100
def main(native, resid, r02, out):
    P_ = [x.rstrip("\r") for x in open(native, encoding="utf-8").read().split("\n") if x.strip()]; assert len(P_) == 1692
    J = json.load(open(resid)); wording = {(u["id"], i): q["qualifier"] for u in J["units"] for i, q in enumerate(u["qualifier_dispositions"], 1)}
    assert set(wording) == set(T), set(T) ^ set(wording)
    rows = {(r["unit_id"], int(r["qualifier_index"])): r for r in csv.DictReader(open(r02))}; assert set(rows) == set(T)
    w = csv.writer(open(out, "w", newline="")); w.writerow(["unit_id", "qualifier_index", "qualifier_wording_sha256", "range_hash_reverified", "class", "current_native_paragraphs", "in_controlling_1_459", "note_identifiers_only", "disposition_status"])
    for k in sorted(T):
        a, b = map(int, re.match(r"MLCore:(\d+)-(\d+)", rows[k]["historical_locator"]).groups()); ok = hashlib.sha256(("\n".join(P_[a-1:b]) + "\n").encode()).hexdigest() == rows[k]["historical_range_LF_sha256"]
        cls, paras, note = T[k]; ps = [int(x) for x in paras.split(";") if x]
        w.writerow([k[0], k[1], hashlib.sha256(wording[k].encode()).hexdigest(), "YES" if ok else "NO", cls, paras, ";".join(str(p) for p in ps if p <= 459), note, "UR_REMAINS__CODER_READING_NO_AWARD"])
    import collections; print(collections.Counter(v[0] for v in T.values()))
if __name__ == "__main__": main(*sys.argv[1:5])
