"""R41 CODER READING (not an owner disposition, not an award) of the 41 distinct historical units behind the 100 R02 qualifiers. Paragraph numbers are NATIVE MLCore paragraphs (current revision AHj4eMQJ…, 1692p). Only identifiers/paragraph numbers are recorded; no governing text is copied.
Tuple: (disposition, current native paragraphs, historical-only difference (identifiers only), oracle / implementation, source-owner ROLE, consequence, recommendation).
R02 stores a qualifier INDEX and the historical RANGE, not the qualifier wording; qualifiers sharing one paragraph therefore inherit one unit reading (INSUFFICIENT_EVIDENCE to split them)."""
EQ = "CURRENT_CLAUSE_EQUIVALENT__CODER_READING"; PA = "CURRENT_CLAUSE_PARTIAL__HISTORICAL_DETAIL_NOT_IN_CURRENT"; PR = "HISTORICAL_PROCESS_NOTE__NO_CURRENT_BEHAVIOUR_REQUIREMENT"; AR = "ALREADY_REPAIRED__NOT_REPEATED"; OR = "TRACKER_ORACLE_REQUIRED__CURRENT_CLAUSE_EQUIVALENT"
OWN = "ML source owner confirms; Manager records in Drive"; CONS = "UR stays open until the disposition is accepted; no equivalence award"
def d(disp, cur, diff, impl, rec): return (disp, cur, diff, impl, OWN, CONS, rec)
CONFIRM = "owner confirms the reading or names the exact clause/difference"
DISP = {
 "NL-0098": d(PA, "103;158;250;288;296", "field names UPSTREAM_MODEL_VERSION/UPSTREAM_TRAIN_WINDOW/UPSTREAM_PREDICTION_TS/UPSTREAM_EVIDENCE_CLASS and 'causal generation method' not found in 1-459 (UPSTREAM_MODEL_ID/GENERATION_ID are)", "none: field-name list is source-owner schema (held)", "owner decides whether the extra UPSTREAM_* names are normative"),
 "NL-0225": d(PR, "361", "review-process instruction for V1.4 (full-system regression), superseded by freeze", "none", CONFIRM),
 "NL-0263": d(PR, "361", "review-process instruction for V1.6, superseded by freeze", "none", CONFIRM),
 "NL-0087": d(PA, "274;327;330;333;385", "PREDICTION_COVERAGE / ABSTENTION_RATE / PERFORMANCE_WHEN_PREDICTING names and 'suppressed-case profile' not found as such (abstention policy inside selection chronology p274 and coverage/abstention in scorecard p333 are)", "none", CONFIRM),
 "NL-0180": d(EQ, "297;298;299;302;303;309", "none identified (state list CANDIDATE/COMPLETE-CERTIFIED/SUPERSEDED/REVOKED is in p298)", "reusable: coordination/lifecycle_framework history; serving-service refusal of REVOKED is consumer-side", CONFIRM),
 "NL-0184": d(PA, "309;310;311", "'every consumer validates its CACHED generation identity against the current authority' not found (no 'cache' term in 1-459 other than p361 test list 'stale caches')", "candidate: R41 consumer snapshot-identity check (see closeout 20)", "owner states whether cached-identity validation is normative beyond p310/311 snapshot+fence"),
 "NL-0030": d(PA, "298;313;319", "'reconstruction query exposes ledger epoch/sequence/watermark' only partly: epoch/fence p298, watermark p319; sequence not named", "candidate: R41 historical_eligibility returns (epoch, resolved_through) with its answer", CONFIRM),
 "NL-0034": d(OR, "313;319;361", "none: oracle text for p313 crash-before-snapshot path (paragraph 548 is only its heading)", "R41 historical_eligibility: genuine stale authoritative resolver/index AND incomplete/complete historical slice negatives; MISSED/QUARANTINED; no current-generation fallback", "owner supplies a deployed resolver instance + slice-closure evidence; generic logic is built"),
 "NL-0038": d(PA, "326;327;328;330;333", "'mechanically distinct in storage, analysis, dashboards, exports, scorecards' only as p330 separately visible + p333 scorecard", "none", CONFIRM),
 "NL-0042": d(PR, "336;337;338;339", "V0.7 revision note; substance (two portability corrections) is in p336-339", "none", CONFIRM),
 "NL-0056": d(PA, "250", "'feature breadth selective, versioned, redundancy-tested' only via REDUNDANCY_GROUP/HYPOTHESIS_FAMILY_ID in p250", "none", CONFIRM),
 "NL-0063": d(PA, "424;455", "'ML may strengthen but never weaken these rules' stated for payload semantics (p424) not as a general clause", "none", "owner states whether a general no-weakening clause is required"),
 "NL-0065": d(EQ, "272;274;280;383", "none identified for append-only attempt ledger with CONFIRMATORY/EXPLORATORY labels", "reusable: tracker/research_lineage (R39 CAS-appended attempts)", CONFIRM),
 "NL-0073": d(EQ, "291;391", "none identified", "none", CONFIRM),
 "NL-0076": d(AR, "250", "already repaired in root's earlier record", "none", "no new allegation"),
 "NL-0078": d(EQ, "247", "none identified", "reusable: E05 as_known_rows (as-of causality)", CONFIRM),
 "NL-0079": d(PA, "236;237;239;292", "'versioned dependency/provenance contract for EVERY information-altering stage, purge over the composed reach' only via p236-239 and p292 (multi-hop)", "none", CONFIRM),
 "NL-0080": d(EQ, "176;276", "none identified", "none", CONFIRM),
 "NL-0096": d(AR, "265", "already repaired (NO MODEL valid outcome)", "none", "no new allegation"),
 "NL-0099": d(EQ, "286;400", "name POCKET_SUPPORT_STATE not found in 1-459 (support/sufficiency requirement is)", "none", CONFIRM),
 "NL-0113": d(PA, "47;336;459", "'self-contained and authoritative for portability; the separate portability document is supporting only' not stated as such", "none", CONFIRM),
 "NL-0122": d(PA, "288;294", "'source instrument model never gains control authority over target' not found as such", "none", CONFIRM),
 "NL-0126": d(EQ, "2;39;145;146;203", "none identified (p203 FORWARD_WALK_REOPEN_REQUIRED = NO)", "none", CONFIRM),
 "NL-0143": d(PA, "236;404", "name ARTIFACT_INSTRUMENT_SCOPE not found in 1-459 (instrument qualification of artifacts/caches is p236, INSTRUMENT_ID p404)", "none", CONFIRM),
 "NL-0162": d(PA, "296;297;299;309;310", "historical 'unless a governed compatibility contract is in the manifest' exception is NOT in current (p310: all components from the same snapshot): current is stricter", "reusable: manifest/snapshot binding (R39 snapshot_binding)", "owner confirms the exception is dropped"),
 "NL-0167": d(PA, "237;239;340", "'before each use verify the object's scope matches the consuming model' only via FIT_INSTRUMENT_SET p237/239 and p340 attack list", "none", CONFIRM),
 "NL-0174": d(EQ, "294;333;340", "name POOLED_MODEL_CLASS not found (MODEL_RESEARCH_CLASS is p333)", "none", CONFIRM),
 "NL-0186": d("TRACKER_SIDE_RESIDUAL__CURRENT_CLAUSE_PARTIAL", "323;324", "'no reader observes a partial shadow record' not stated in 1-459 (immutable prospective record p323; idempotent one-record p324); normative shadow-row schema/reader contract is UNBOUND", "R41 atomic_publication: candidate atomic read/publish over named candidate interfaces; whole-frame IPC is NOT promoted to shadow-record proof", "owner/Manager names the shadow-row field set and reader contract"),
 "NL-0187": d(EQ, "333;334", "none identified (see R25 delta)", "none", "reuse A07_NL0187 R25 delta"),
 "NL-0199": d(EQ, "316;317;318", "none identified", "reusable: lifecycle history reads", CONFIRM),
 "NL-0200": d(PA, "324", "minimum identity field list for PREDICTION_EVENT_ID not enumerated in current (p324 says 'governed identity')", "none", CONFIRM),
 "NL-0220": d(PA, "304;305", "'must be disclosed' and byte-identical/fine-tuned/copied derivation wording only partly (p304 lists fine-tuning, reserialization, pruning, distillation, partial copying)", "none", CONFIRM),
 "NL-0221": d(PA, "304", "'explicit review of the original revocation reason + documented determination' only as 'specific review gate' (p304)", "none", CONFIRM),
 "NL-0223": d(PA, "298;319;323", "mandatory append-only ANNOTATION on historical records not found; current clause is dynamic resolution of trust with freshness (p319): distinct mechanisms", "none", "owner states whether an appended annotation is required in addition to p319"),
 "NL-0224": d(PA, "319;361", "named adversarial test 'revoke a generation that contributed to a historical comparison' not listed in p361", "candidate: R41 historical_eligibility/annotation-free oracle (original unchanged + later revocation visible via resolver)", CONFIRM),
 "NL-0242": d(EQ, "319", "none identified (p319: stale derived views cannot masquerade as current trust; watermark/freshness machine-checkable)", "reusable: E05 stale-head refusal", CONFIRM),
 "NL-0249": d(AR, "405;424", "already repaired (ML405-424)", "none", "no new allegation"),
 "NL-0250": d(EQ, "312;313;316", "none identified", "R41 historical_eligibility", CONFIRM),
 "NL-0258": d(PA, "298;319", "'resolver carries source-ledger epoch/version/watermark AND its own resolved-through version' only as watermark (p319)/epoch (p298); 'resolved-through' not named", "R41 historical_eligibility: resolver result carries resolved_through; caller compares", CONFIRM),
 "NL-0262": d(OR, "319;333;361", "none: oracle is artificial index lag after revocation -> caller detects stale watermark/epoch", "R41 historical_eligibility stale-resolver negatives", "owner supplies deployed resolver instance; generic logic built"),
 "NL-0266": d(PA, "313", "'the ledger's own ordering/commit semantics must prove the historical interval is complete and closed' only as HISTORICAL_SLICE_COMPLETENESS = PASS (p313); the closing proof mechanism is not defined", "R41 historical_eligibility consumes a slice-closure assertion; producer held", "owner names how closure is proven"),
}
assert len(DISP) == 41
