"""R52: ONE 100-row PROPOSED disposition record for the A07 qualifiers (Coder proposal; awards nothing; all 100 stay UR; no gate/hold change).
Joins, per (unit, qualifier index): R47 (wording hash, V235 comparison hash, prior-map vs V235-range overlap), R42 (per-qualifier reading class, current native paragraphs, note) and R43 (V235 target/ranges/flags/oracle acceptance),
after VERIFYING the four original oracle JSON members' sha256 (recorded in the transport header) and that every acceptance field is false. Output has identifiers, ranges, hashes and OWN-WORD paraphrases only (no governing text).
Dispositions are PROPOSALS for the ML source owner / Manager; hash parity, range overlap and token similarity are never used as COVERED_BY; a missing current ref alone is never used as HISTORY_ONLY.
Usage: python -I tools/a07_r52_disposition_record.py <member dir> <docs/a07 dir> <out csv>"""
import csv, hashlib, json, pathlib, sys
EXPECTED = {"V235_CROSSWALK_CANDIDATE.json": "282d0fd2d541562ca956b973e9aa9b4888ee302ca06d37cf1948cd382f9ad7fb",
            "V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json": "1287086de20f5c0f25bc3250e9bce05d1d916f54d7cd0cc98c47b8183d7cd72d",
            "V232_ORACLE_AND_TARGET_TRANSITION_MANIFEST_339.json": "cc0c27bea542aeaea674a9bae0b0173ee2a54498f7cad5f641db86f2941787d0",
            "V232_FINITE_41_UNIT_QUALIFIER_RESIDUAL.json": "bfee4c8a4aa877f9ba436e1142184f790d0442a3e8942f7b57e82b724441fe3e"}
# --- own-word historical meaning of each qualifier (paraphrase; never the governing wording) --------------------------------------------------------------------
MEANING = """0098#1|the upstream model's identity and its version are both carried, not the downstream model's version
0098#2|the upstream training window and evidence class are carried with the lineage
0098#3|the upstream prediction timestamp and the causal generation method are carried
0225#1|a status overlay does not replace the regression-test duty; the nine-block sequence is reproduced exactly
0263#1|same as 0225 plus a historical domain list and a not-self-certifying qualifier the oracle does not test
0087#1|abstaining or suppressing a prediction is visible as coverage, not hidden
0087#2|performance when the model does predict, and the profile of suppressed cases, is measured where measurable
0087#3|the confirmatory outer test is not used to tune the abstention/coverage trade-off
0180#1|lifecycle state lives in its own append-only ledger instead of mutable manifest storage
0180#2|a minimum set of named lifecycle states exists and revoked is distinct from superseded
0180#3|seven named services each distinguish loading from serving and handle hash-valid revoked generations
0180#4|with no eligible generation the system fails closed, never walks backward, and raises alerts
0180#5|a read-only forensic exception for revoked generations is explicit
0184#1|an atomic pointer alone is not enough to trust a generation
0184#2|every named consumer re-validates a cached generation on every read or use
0184#3|stale caches are invalidated before serving; N versus N+1 visibility is labelled unless it is history
0184#4|original-event history and revoked-generation forensic restrictions are kept
0030#1|a reconstruction answer exposes the ledger epoch, sequence and watermark it was resolved through
0030#2|the answer-specific resolved-through identity is available to the caller
0034#1|the held-back lifecycle test is mandatory, not an optional scenario
0034#2|the held-back test context covers a lagging lifecycle replica and a changed lifecycle authority
0038#1|model abstention and lifecycle-fencing misses are separate categories
0038#2|those two categories stay mechanically distinct in storage, analysis, dashboards, exports and scorecards
0042#1|the earlier no-reopen statement for the forward walk is bound with its current opening-authority context
0056#1|rich raw observations may be retained while only selected, versioned subsets feed models
0056#2|retained observations are tested for redundancy
0056#3|a functional ownership boundary between the two sides is stated
0063#1|an overclaim that a named delta is equivalent to the whole historical no-weakening sentence is withdrawn
0065#1|already-cited classification and retention clauses are carried into the target context instead of a rename-only mapping
0073#1|agreement among errors that depend on each other is not independent confirmation
0073#2|one correlation matrix is not universally sufficient
0073#3|diversity is measured by target and by model class
0076#1|redundancy-group and hypothesis-family metadata are recorded
0076#2|interpretive, hierarchical or dependence groupings are not independent hypotheses
0076#3|search breadth is recorded
0076#4|the multiplicity denominator may not be shrunk arbitrarily without a justified method
0078#1|earliest reproducible SALIX consumption, not public release, is the reference moment
0078#2|a conservative, pre-registered, defensible reconstruction is marked reconstructed and uncertain
0078#3|a feature with no trustworthy causal boundary is excluded
0079#1|each learned or fitted pipeline stage carries a versioned dependency and provenance contract
0079#2|the dependency window is the complete composed interval, not a raw lookback or a simplistic scalar maximum
0080#1|routine transparent mutation tests coexist with generated stress tests and held-back checks
0080#2|exposure is governed and versioned, and repeated redesign consumes it
0080#3|a held-back pass is necessary where required but is never a universal robustness claim
0096#1|ML must be able to kill an idea; no-model is an explicit outcome
0096#2|no profitable model is forced and ML never controls the engine automatically
0099#1|global support does not authorise a pocket-level claim and no universal minimum is set
0099#2|pocket support state comes from occurrence, membership mass, dependence-aware information, uncertainty and stability
0099#3|a source-range versus target-range difference in the mapping
0113#1|the core portability section is authoritative and self-contained
0113#2|no separate portability design analysis is needed to interpret or implement the core
0122#1|current purpose, market-intelligence, no-engine-control and Owner-future-authority statements are bound
0126#1|the portability section does not reopen or weaken the frozen forward-walk statistical contract
0126#2|an instrument namespace and interface can instantiate the same methodology
0126#3|a demonstrated XAUUSD-only defect in the forward-walk core needs an explicit Owner-governed reopen, not a silent patch
0143#1|every persisted or cached ML artifact carries the canonical instrument id
0143#2|an artifact instrument-scope field is required
0162#1|only a complete, certified generation is loaded
0162#2|no arbitrary mixing of model, calibrator, OOD, feature and target components
0162#3|an exception only through an explicit governed compatibility contract recorded in the manifest
0167#1|every fitted, calibration, OOD or learned state keeps its id and the fit set
0167#2|before each use the runtime verifies the consumer and object scope
0174#1|pooled, transfer, multi-task and shared-representation models are a separate research class
0174#2|the artifact carries an explicit model research class or pooled-model class
0174#3|such models cannot run through the ordinary single-instrument path
0186#1|shadow writes are atomic per record: fully present with all mandatory fields, or absent
0186#2|the mandatory shadow-record fields cover identity, prediction, uncertainty, calibration, OOD, support, authority and generation
0186#3|no reader, reconciler, dashboard or evaluation job may observe or consume a partial shadow record
0187#1|pooled, transfer or cross-instrument forecasts are never visually indistinguishable
0187#2|every displayed ML or FW forecast exposes its model research class
0199#1|replay and reconciliation use the original generation, not the current pointer
0199#2|revoked generations are readable only for explicit read-only forensic audit
0199#3|a forensic audit also binds the recorded historical identity
0200#1|a deterministic prediction event id / idempotency key gives identical retry behaviour
0200#2|the key is globally unique and spans at least instrument, generation, target, horizon and forecast time
0200#3|retries are not counted as events
0220#1|cosmetic or derived content cannot erase revoked ancestry
0220#2|derived objects carry explicit revoked-lineage metadata with a minimum field set
0220#3|forensic reading is not certification laundering
0221#1|revoked direct or transitive ancestry requires special review
0221#2|the original revocation reason and a documented removed, irrelevant or remediated finding are recorded
0221#3|changed ids do not earn an ordinary clean certification
0223#1|historical records are immutable and later knowledge is appendable
0223#2|an affected object must receive an annotation with contributor identity, timestamp and reason
0224#1|annotation versus dynamic-trust equivalence is marked consistently with the 0223 treatment
0242#1|materialised annotations, dashboards, comparison caches and reports carry freshness and version identity
0242#2|identity is relative to the revocation-impact index and lifecycle epoch, and stale trust is detected
0242#3|historical artifact immutability is kept distinct from the current trust claim
0249#1|the trigger's causal identity includes the intended forecast or event timestamp and the instrument
0249#2|at minimum target, horizon, source event where applicable and a governed knowledge-time boundary are in the identity
0249#3|reconstruction is deterministic rather than a fallback to the current pointer
0250#1|redelivery, restart, scheduled catch-up, backlog or any delayed execution is covered
0250#2|the generation certified, serving-eligible and causally available at the original time is used, not the current pointer
0250#3|the append-only lifecycle and generation-certification history is what is used
0258#1|the authoritative resolver carries at least the source-ledger epoch, version and watermark
0258#2|the resolver also carries its own resolved-through version
0258#3|the caller determines coverage of every lifecycle event the read-consistency contract requires
0262#1|the held-back test introduces artificial index lag after a revocation
0262#2|the caller detects a stale watermark or epoch instead of reporting current trust
0266#1|sibling exact-mechanics ambiguity is reconciled while functional current duties and adversarial checks are retained"""
M = {}
for l in MEANING.splitlines():
    k, v = l.split("|", 1)
    if v.strip(): M[k.strip()] = v.strip()
# --- individual proposals for the 21 R43 disagreements and the 12 loss-listed qualifiers: (disposition, discrepancy, rationale, source_delta, tracker_action, decision) -------------------------
T0 = "NONE (ML source-owned)"
I = {
 "0030#2": ("CONTAINER_ONLY__RESTORE_DELTA_RECOMMENDED", "V235 wording names two gates and original-event generation only; no clause in 1-459 gives the caller an answer-specific resolved-through identity; the only statement sits in the lineage region after 459", "p313/p319 require both freshness and completeness for reconstruction and 0258#1 carries a watermark, so the resolved-through identity is the missing caller-facing half; absence of a current ref is NOT the reason: the reason is that the container is incorporated and the element is not", "explicit reviewed source delta restoring the caller-visible resolved-through identity on reconstruction answers (same concept as 0258#2)", T0, "DI-07"),
 "0056#1": ("PROPOSED_WORDING_ONLY__NO_CONTROLLING_ANCHOR_YET", "R42 found no clause in 1-459; V235 comparison wording states raw retention versus selective versioned use; paragraphs 250/253 are the nearest controlling context", "R42 'not current' reading is withdrawn as to V235 wording only; V235 is Manager-proposed and not adopted, so wording alone is not a controlling anchor", "none if the owner confirms the V235 wording is the adopted statement; otherwise a one-clause delta at the retention paragraph", T0, "DI-11"),
 "0073#3": ("CONTAINER_ONLY__OWNER_CHOICE", "V235 wording states dependence and traceability only; measurement of diversity by target and model class is not stated", "independence of confirmation is carried (0073#1/#2) but the method of measuring diversity is a strengthener; I cannot tell from sources whether the owner wants it normative", "if wanted: a delta naming diversity measurement by target and model class; if not: HISTORY_ONLY with the effect statement that diversity is judged by dependence only", T0, "DI-04"),
 "0076#4": ("SELF_ADMITTED_RESIDUAL__RESTORE_DELTA_RECOMMENDED", "V235 states the clause and itself calls the method a source-equivalence question; no prior-map line ref", "an arbitrary denominator shrink is a multiple-testing escape; leaving it history-only would let a method shrink the family count unjustified", "explicit rule: no multiplicity-denominator shrink without a justified, recorded method", T0, "DI-03"),
 "0078#2": ("PARTIAL__LINEAGE_ONLY_STRENGTHENER_INCORPORATION_DECISION", "V235 wording keeps observed versus reconstructed marking; the preregistered and conservative requirement is stated only in lines after the controlling boundary (history unless incorporated)", "range membership in V235 does not promote lines after 459; reconstructed feature values without a preregistered conservative method are a look-ahead risk", "explicit incorporation or restoration delta for the preregistered conservative reconstruction rule", T0, "DI-01"),
 "0078#3": ("HISTORY_STRENGTHENER_UNRESOLVED__INCORPORATION_DECISION", "no V235 wording for the exclusion rule; the lines that state it lie after the controlling boundary; current paragraphs give causally governed missing/stale/imputed states and no future imputation but not exclusion", "fail-closed exclusion is the safer reading, but it is a strengthener absent from sections 1-26; earlier CARRIED_BY_SOURCE label withdrawn", "explicit incorporation or restoration delta for exclusion when no trustworthy causal boundary exists", T0, "DI-01"),
 "0079#2": ("PARTIAL__RESTORE_DELTA_RECOMMENDED", "composed intervals are named; the rejection of a raw lookback or scalar maximum is not stated", "scalar-max windows are the concrete leakage class; the restoration is one sentence", "delta stating the dependency window is the composed interval and a raw lookback or scalar maximum is insufficient", T0, "DI-05"),
 "0080#3": ("PROPOSED_WORDING_ONLY__NO_CONTROLLING_ANCHOR_YET", "V235 wording states a scoped held-back pass; R42 found no clause in 1-459; the prior map has no line ref", "wording-only coverage in a not-adopted proposal is not a controlling anchor; a nearby p273/p346 context exists for the held-back test", "none if the owner confirms the V235 wording is adopted; otherwise a one-clause delta", T0, "DI-11"),
 "0096#1": ("COVERED_BY_PROPOSED", "none: V235 wording and the current anchor agree; this is the repaired row", "the explicit no-model outcome is stated at the current paragraph (R42 class R, already repaired)", "none", T0, None),
 "0099#3": ("NOT_A_CLAUSE__MAPPING_ROLE_ONLY", "this is a source-versus-target range difference inside the mapping, not a normative statement", "it should be closed as a mapping-role record, not carried as a coverage item", "none", T0, None),
 "0113#1": ("PARTIAL__OWNER_CONFIRMATION", "both evidence kinds are present; self-containment of the portability section is not stated", "self-containment is a statement about document structure that the owner can confirm without a normative delta", "none unless the owner wants the self-containment sentence restored", T0, "DI-12"),
 "0113#2": ("CONTAINER_ONLY__HISTORY_ONLY_RECOMMENDED_WITH_EFFECT", "no V235 wording and no prior-map line ref", "a process remark about needing no separate design document; no implementation behaviour depends on it", "none; effect statement if history-only: interpretation must rest on the core text alone", T0, "DI-12"),
 "0126#3": ("WORDING_CARRIES__ANCHOR_MISMATCH__RE_ANCHOR_RECOMMENDED", "V235 wording carries the Owner-governed reopen path but its ranges do not contain the paragraph the prior map used (203); R42 finds paragraph 203 says no reopen now and lacks the conditional reopen path", "the conditional path is absent from the controlling paragraph, so this is both an anchor mismatch and a missing conditional", "correct the V235 range list and, if the conditional path is wanted, a delta adding it at the no-reopen paragraph", T0, "DI-11"),
 "0162#3": ("PARTIAL_LINEAGE_ONLY__INCORPORATION_DECISION", "container only; the governed compatibility-contract exception is stated only in the lineage region after 459", "an exception that weakens 'complete certified only' must not be silently restored from history", "explicit incorporation or restoration delta, else HISTORY_ONLY with the effect that no compatibility exception exists", T0, "DI-01"),
 "0186#3": ("PARTIAL__READER_SIDE_UNBOUND", "V235 wording says a record must not expose partial mandatory fields; the reader side is not stated; the immutable prospective record alone does not prove no reader can observe a partial one", "Tracker side: atomic per-record publication exists (R43) but the shadow-row field set and the reader contract are unbound in the sources read", "delta stating the reader-side rule and the mandatory shadow-row field set", "Tracker publication path implements atomic record-level publication (tests only; not wired as a consumer contract); reader contract stays unbound", "DI-08"),
 "0220#2": ("PARTIAL__RESTORE_DELTA_RECOMMENDED", "ancestry and reason/scope are stated; the minimum lineage field set is not", "the minimum field set is what makes a revoked lineage checkable by a consumer", "delta naming the minimum revoked-lineage fields", T0, "DI-06"),
 "0221#2": ("PARTIAL__RESTORE_DELTA_RECOMMENDED", "reason and scope remediation review are stated; recording the original revocation reason and the removed/irrelevant/remediated finding is not", "without the record a later reviewer cannot tell remediation from omission", "delta requiring the original reason and the documented finding", T0, "DI-06"),
 "0223#2": ("WORDING_DIVERGES_FROM_HISTORICAL_MUST__OWNER_CHOICE", "V235 says annotation is useful and not the sole mechanism; the historical statement is mandatory; current paragraphs describe dynamic trust resolution, a distinct mechanism", "a mandatory append-only annotation must not be inferred from present-day revocation freshness; the divergence is real", "if mandatory annotation is wanted: delta; if dynamic trust is the mechanism: HISTORY_ONLY with the effect that no per-object annotation duty exists", T0, "DI-02"),
 "0224#1": ("INHERITED_FROM_0223__NOT_INDEPENDENT", "uses the same wording as 0223; it is not a separate clause", "its disposition follows 0223#2 and cannot be decided separately", "none beyond 0223#2", T0, "DI-02"),
 "0249#1": ("COVERED_BY_PROPOSED__V235_WORDING_CORRECTION", "current paragraphs 405-424 state forecast timestamp plus instrument identity (R42 class R); V235 comparison wording does not state it", "the current text carries it, so the defect is in V235's comparison wording, not in coverage", "correct the V235 comparison wording; no source delta", "Tracker trigger/event identity is derived with forecast time and instrument (existing event-id tests); no further code", None),
 "0258#2": ("CONTAINER_ONLY__RESTORE_DELTA_RECOMMENDED", "V235 wording does not state the resolver's own resolved-through version", "same concept as 0030#2; the watermark in 0258#1 is the source ledger's, not the resolver's", "explicit reviewed delta, handled together with 0030#2", T0, "DI-07"),
 # the loss-listed units (readings of current-range coverage; the V231 loss flag names V231 only)
 "0087#1": ("COVERED_BY_PROPOSED__V235_RESIDUAL", "V235 leaves the unit RESIDUAL; current paragraphs 327/330/333 show selection policy and coverage; the V232/V235 canonical text restores the content as a proposed, NOT RUN claim", "the V231 loss flag is not a finding about the current text", "none", T0, None),
 "0087#2": ("HISTORY_ONLY_GAP__RAISED__D22", "V235 itself states the cited ranges do not establish it; V230 verdict GAP; V235 text keeps it as a separate proposed D22 test", "not inferred away (raise duty); the decision is D22", "restoration delta or HISTORY_ONLY with effect statement, per D22", T0, "DI-09"),
 "0087#3": ("COVERED_BY_PROPOSED__V235_RESIDUAL", "paragraph 274 states the selection/exposure rule; V235 unit RESIDUAL", "reading of current coverage only", "none", T0, None),
 "0180#1": ("REPLACED_EXPLICITLY__SUPERSEDED_BY_PROPOSED", "current paragraph 297 explicitly replaces mutable manifest lifecycle state with the separate append-only ledger (p298)", "replacement, not equivalence", "none", T0, None),
 "0180#2": ("COVERED_BY_PROPOSED__SUPERSEDED_BY_PROPOSED", "named states and revoked != superseded are preserved at p298/p301", "reading only", "none", T0, None),
 "0180#3": ("PARTIAL__D26_OPEN", "no-revoked-serving and recovery validation present at p302/p309; the seven-service load-versus-serve scope is not proven", "scope of services is D26", "per D26", T0, "DI-10"),
 "0180#4": ("PARTIAL__D24_OPEN", "fail-closed and no backward walk present at p302; no alert duty in that clause", "alert owner is D24", "per D24", T0, "DI-10"),
 "0180#5": ("COVERED_BY_PROPOSED__SUPERSEDED_BY_PROPOSED", "read-only audit exception is explicit at p303/p318", "reading only", "none", T0, None),
 "0184#1": ("COVERED_BY_PROPOSED__SUPERSEDED_BY_PROPOSED", "separate integrity authority plus snapshot/fence at p309/p311; pointer alone is insufficient", "current integrity and lifecycle, not the pointer", "none", T0, None),
 "0184#2": ("NOT_ESTABLISHED__D26", "per-use validation for all eight consumers is not established at p361", "scope is D26", "per D26", T0, "DI-10"),
 "0184#3": ("PARTIAL__D26_OPEN", "the broad outcome is kept at p310/p311/p361; non-publishing cache invalidation is open", "scope is D26", "per D26", T0, "DI-10"),
 "0184#4": ("COVERED_BY_PROPOSED__SUPERSEDED_BY_PROPOSED", "original-event history and revoked-forensic restrictions are explicit at p316/p318", "forensics retained", "none", T0, None),
}
TRK = {"0034#2": "implemented: historical_eligibility / lifecycle_eligibility candidate modules (R43); tests only", "0262#1": "implemented: lifecycle_eligibility candidate (R43); tests only",
       "0034#1": "implemented as held-back test duties (R43)", "0200#1": "Tracker event-id determinism covered by existing event-id tests", "0200#3": "retries not counted: existing shadow-publication tests",
       "0186#1": "atomic record-level publication candidate (R43); tests only", "0186#2": "shadow-row field set unbound in the sources read"}
CLS = {"C": ("COVERED_BY_PROPOSED", "current controlling paragraphs state the proposition (Coder reading of 1-459)", "proposal only: the per-qualifier oracle comparison by the ML source owner is required; range/hash overlap is not used"),
       "P": ("PARTIAL__STRENGTHENER_DECISION", "core is stated in current paragraphs; the field/quantifier/surface strengthening is historical-only", "decide per strengthener: restore through an explicit reviewed delta, or HISTORY_ONLY with an effect statement; no silent restoration"),
       "H": ("NO_CURRENT_STATEMENT__DECISION", "no statement found in 1-459", "a missing current ref alone does not justify HISTORY_ONLY; decide restore or history with effect"),
       "N": ("PROCESS_OR_BINDING_NOTE__NO_SOURCE_CLAUSE", "a process or binding note, not a source clause", "closes as a record item, not coverage"),
       "O": ("COVERED_BY_PROPOSED__ORACLE_TEST_MISSING", "the proposition is present in current paragraphs but the target oracle does not test it", "a oracle test must be authored; coverage is not awarded"),
       "L": ("LINEAGE_ONLY__INCORPORATION_DECISION", "stated only in the preserved-lineage region after the controlling boundary", "incorporation is an explicit owner question; range membership does not promote it"),
       "R": ("COVERED_BY_PROPOSED__ALREADY_REPAIRED", "already repaired in current paragraphs", "no repeat")}
def main(d, a07, out):
    d, a07 = pathlib.Path(d), pathlib.Path(a07)
    for n, h in EXPECTED.items(): assert hashlib.sha256((d / n).read_bytes()).hexdigest() == h, "member hash mismatch: " + n
    for n in ("V230_TYPED_339_UNIT_REVIEW_AND_ORACLE_LEDGER.json", "V235_CROSSWALK_CANDIDATE.json"):
        j = json.load(open(d / n)); assert j.get("global_source_semantic_acceptance", False) is False and j.get("independent_acceptance", False) is False, "acceptance field is not false: " + n
    rd = lambda f, a, b: {(x["unit_id"], x["qualifier_index"]): x for x in csv.DictReader(open(a07 / f))}
    r47, r42, r43 = rd("V232_26S_R47_MEMBER_RECONCILIATION.csv", 0, 0), rd("V232_26S_R42_PER_QUALIFIER_READING.csv", 0, 0), rd("V232_26S_R43_ORACLE_ASSOCIATION.csv", 0, 0)
    rows = []
    for k in sorted(r47):
        a, b, c = r47[k], r42[k], r43[k]; key = "%s#%s" % (k[0][3:], k[1]); cls = b["class"]
        assert key in M, "no own-word meaning for " + key; assert a["qualifier_sha256"] and a["qualifier_sha256"] != "", key
        ov = I.get(key); base = CLS[cls]
        disp, disc, rat, delta, trk, dec = ov if ov else (base[0], b["note_identifiers_only"] if cls != "C" else base[1], base[2], "none" if cls in ("C", "R", "N") else "explicit reviewed delta only if the owner wants the strengthener", None, None)
        if not ov and cls in ("P", "H") and not dec: dec = "DI-12" if False else None
        anchor = ("MLCore p" + b["current_native_paragraphs"].replace(";", ";p")) if b["current_native_paragraphs"] and b["in_controlling_1_459"] else ("NONE_IN_1-459" if cls != "L" else "NONE_LINEAGE_ONLY_AFTER_459")
        rows.append({"unit_id": k[0], "qualifier_index": k[1], "qualifier_sha256": a["qualifier_sha256"], "historical_meaning_own_words": M[key], "r42_class": cls,
                     "current_controlling_anchor": anchor, "anchor_basis": "R42 reading of native paragraphs 1-459 (controlling per MLCore 456-459)",
                     "oracle_evidence": "V235 %s -> %s ranges[%s] comparison_sha256=%s; V232 oracle hash %s V230; oracle_acceptance=%s; flags=%s" % (c["v235_disposition"], c["v235_target"], c["v235_current_source_ranges"], c["v235_qualifier_comparison_sha256"][:16], "equals" if c["v232_oracle_hash_equals_v230"] == "True" else "DIFFERS from", c["oracle_acceptance"], c["flags"] or "none"),
                     "prior_map_vs_v235_ranges": a["prior_vs_v235_ranges"], "discrepancy": disc, "recommended_disposition": disp, "rationale": rat, "exact_source_delta_if_needed": delta,
                     "tracker_code_action": trk or TRK.get(key, T0), "decision_input": dec or "", "evidence_class": "CODER_READING (not reported / independently-reviewed / simulated / qualified / accepted)", "award": "NONE: UR_REMAINS"})
    assert len(rows) == 100 and len({(r["unit_id"], r["qualifier_index"]) for r in rows}) == 100
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("wrote", len(rows), "rows;", sum(1 for r in rows if r["decision_input"]), "carry a decision input")
if __name__ == "__main__": main(*sys.argv[1:4])
