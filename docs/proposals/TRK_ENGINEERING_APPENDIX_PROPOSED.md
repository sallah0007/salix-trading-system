# Stage A Tracker - PROPOSED engineering appendix (R20)

STATUS: PROPOSED INTERNAL ENGINEERING DESIGN. NOT an adopted governing schema, NOT a source input, NOT an admitted contract. Linked from `docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md`. CODER FINDING != SALIX DECISION: nothing here, and no merge/CI, clears A02 Class B HOLD, A07/COVERAGE OPEN, P12/N2, QC34 ALERT(HOLD), A08 READY_TO_CODE NO or Stage A HOLD. Authority: CLAUDE.md 2A (this repository only; Drive read-only). No SALIX AI, Engine, Stage B or live work. No governing-source text is copied; sources are cited by ID and section.

## How to read this appendix
Each family states: SOURCE (clauses/IDs), REUSE (existing code), PORT (proposed internal port/service/API, inputs -> outputs; the names are CANDIDATE INTERNAL ENGINEERING CHOICES, not source vocabulary), OWNERS (producer / consumer), STATE (the one canonical state path and its persistence/read-model role), REFUSALS (preconditions, refusal, replay, recovery), CALLPATH (real callpath today, or the exact missing binding), TEST (targeted test / negative control to write), EVIDENCE (what is actually demonstrated), INPUT (exact unresolved technical input -> source-owner function -> consequence -> recommended disposition).

Three-way split used throughout: (A) AUTHORABLE NOW = source-present mechanics the Coder can build under 2A with the internal choices made explicit; (B) UNASSIGNED NORMATIVE CONTENT = canonical bytes, opcode/grammar, K3/CASE/counting policy, actors, thresholds, provider evidence, which stay UNBOUND and are never defaulted; (C) OPERATIONAL QUALIFICATION = separate and never claimed here. Reachability != invocation != correctness != qualification.

Design rules that apply to every port below (they follow from CLAUDE.md s1/s3/s4, Build Plan s14A and the R18-R20 counterexamples):
1. One canonical state path per fact: the fenced per-namespace journal (`coordination/object_store_journal`, `tracker/registry.FeatureJournalSet`) -> `replay.replay`; read models/projections are rebuildable and carry no authority. No second registry, no second lifecycle authority.
2. Authority class is a property of WHERE a record lives (`storage/authority_class.SimulationStore` vs the qualified store), never a flag on an in-memory outcome and never a new canonical body field. Publication, read-model rebuild and status projection refuse non-QUALIFIED journals.
3. A scope-qualified or typed-unknown result must make an unaware reader fail closed (typed verdicts: UNDETERMINED / UNCOMPUTED / HELD, never a boolean).
4. A caller-supplied flag is never proof. Identity text in diagnostics is a retrieval hint, never an identity-proof encoding.
5. Every new refusal ships with a mutant that makes its test fail.


## Part 1: Core baseline families B01-B24

### B01 - Canonical observation identity (DOCX s5, s21 Identity)
- SOURCE: Frozen DOCX s5/s21 identity family (canonical bar/event identity immutable; identical retransmission idempotent; conflicting terminal payload -> ambiguity/quarantine; database-enforced). Core is in assigned scope; E03 is a MODULE MAP, not a schema or API, so it cannot supply observation fields.
- REUSE: `pipeline._accept` (idempotent replay vs VERSION_CONFLICT) is the pattern; `storage/keys` namespace-qualified keys; `coordination/object_store_journal` put_if_absent/put_if_match; `tracker_identity.content_identity`.
- PORT: `ObservationIdentityPort.admit(observation_identity_facts, payload_digest) -> {NEW | IDEMPOTENT_REPEAT | CONFLICT_QUARANTINED}` over a per-(instrument,timeframe) journal namespace; a content-addressed key `obs/<ns>/<identity-hash>` written with put_if_absent; the second writer with a different payload digest records an AMBIGUITY journal record and never overwrites.
- OWNERS: Producer: ingestion/Core observation owner (outside this repo). Consumer: Tracker materialization, as-of resolution, Gateway.
- STATE: Journal record kinds OBSERVATION_ADMITTED / OBSERVATION_AMBIGUOUS in the same fenced journal family; rebuildable index only as a read model.
- REFUSALS: Refuse unknown timeframe/instrument; refuse admission under a non-held fence; an AMBIGUOUS identity blocks dependents (fail closed) until a review-successor record resolves it; replay is a pure function of the journal; recovery = `cold_rebuild_head` + orphan scan.
- CALLPATH: None for bars. Missing binding: the observation identity FIELD LIST and its byte encoding (what makes two observations 'the same').
- TEST: Same identity+same payload twice = one record; same identity+different payload = AMBIGUOUS and no overwrite (mutant: drop the digest comparison); instrument-qualified keys never collide across EURUSD/XAUUSD.
- EVIDENCE: Pattern IMPLEMENTED_TESTED for feature versions only. Observation port: PROPOSED_DESIGN, not coded because the field list is unassigned.
- SOURCE-PRESENT: the registry source (1eZThdek..., s5) already names the minimum identity facts of a snapshot/observation (instrument, timeframe/event class, canonical bar/event identity, broker/server time identity, UTC identity, broker-UTC rule/version, source/provider identity, raw source version, schema/calculation-family version, creation/effective/available-as-of identities). These are source-present and are not 'unassigned'.
- INPUT: (distinct, still unbound) the exact canonical byte encoding, the uniqueness constraint instance, and admission of the observation schema. Owner: Core/Tracker blueprint owner. Consequence: the port can be built and tested over an internal candidate carrier (fact names above, sorted canonical bytes via existing primitives) as simulation evidence, but no production key can be asserted. Ready decision: accept the named facts as the identity tuple and fix the byte layout. STATUS=ENCODING_AND_ADMISSION_UNBOUND (fact list source-present).

### B02 - Governed timeframe registry and as-of across timeframes (DOCX s5, s21 Time)
- SOURCE: DOCX s5/s21 Time: governed registry (M15/H1/H4), parent completeness re-derived from segmentation, DST/session rules, cross-timeframe as-of with no back-projection.
- REUSE: `identifiers.Scope`, `currentness.resolve_asof`, `chain_status`.
- PORT: `TimeframeRegistryPort.segment(instrument, timeframe, instant) -> BarWindow | UNSEGMENTABLE` and `parent_complete(parent_window, child_windows) -> COMPLETE | INCOMPLETE | UNDETERMINED` reading a governed calendar object by (id, version, hash).
- OWNERS: Producer: calendar/segmentation source owner. Consumer: materialization, Gateway as-of.
- STATE: Registry objects are immutable content-addressed versions; the active-version pointer lives in the journal (one authority).
- REFUSALS: Unknown timeframe or calendar version -> UNSEGMENTABLE (fail closed); a missing child window makes the parent INCOMPLETE, never 'complete by default'; replay pins the calendar version used.
- CALLPATH: None. Missing binding: the governed segmentation/DST/session rules themselves.
- TEST: DST gap/overlap days; partial parent; back-projection attempt refused (mutant: let a child read a later-closing parent).
- EVIDENCE: PROPOSED_DESIGN.
- INPUT: Calendar/segmentation rule source -> calendar owner -> time-family tests impossible without it -> supply the registry; STATUS=SOURCE_INPUT_UNBOUND.

### B03 - Snapshot fence, TRACKER_SNAPSHOT_MANIFEST, vintage (DOCX s5, s21A)
- SOURCE: DOCX s5/s21A: half-open fence, one QUERY_ASOF, per-timeframe vintage, immutable content-hashed manifest, MIXED_VINTAGE invalid, MIXED_DECLARED default-deny.
- REUSE: `chain_status` (available_asof < fence), `gateway/v038`, `currentness`, `canonical_bytes`/`domain_hash`.
- PORT: `SnapshotPort.seal(query_asof, per_timeframe_vintage, members) -> SnapshotRef(id, hash) | MIXED_VINTAGE_REFUSED`; `verify(ref, members)`.
- OWNERS: Producer: Tracker. Consumers: Gateway, FW, ML.
- STATE: Sealed manifest = immutable object; the seal event is a journal record.
- REFUSALS: Members with different vintage and no declared allow-policy -> MIXED_VINTAGE_REFUSED; a consumer allow-policy is a READ of source-owned policy, never a default.
- CALLPATH: Fence comparison only. Missing: manifest schema/bytes (D13) and DATA_VINTAGE_MODE vocabulary.
- TEST: Mixed batch refused; allow-policy absent = refused (mutant: default allow); two seals of identical members give one hash.
- EVIDENCE: Fence IMPLEMENTED_TESTED; manifest PROPOSED_DESIGN.
- SOURCE-PRESENT: registry s5 names the minimum TRACKER_SNAPSHOT_MANIFEST content (tracker_snapshot_id, instrument, timeframe/event class, bar/event identity, broker/UTC identities and rule version, source/provider, raw source version, schema version, quality/missingness/staleness, creation/effective/available-as-of, observed-vs-corrected-vs-recomputed mode, enrichment identities, fence/read-boundary identity) and the half-open fence (available_asof < fence included).
- INPUT: (distinct, still unbound) exact manifest byte encoding, DATA_VINTAGE_MODE vocabulary values, instance and admission. Consequence: seal/verify mechanics run on an internal candidate carrier in simulation; no production snapshot hash. STATUS=ENCODING_AND_ADMISSION_UNBOUND.

### B04 - SOURCE_DATA_CONTRACT per provider family (DOCX s6, s7A, s21)
- SOURCE: DOCX s6/s7A/s21: versioned contract, independently derived fingerprint, exactly-one match else raw-preserved/quarantined, freshness/watermark, challenge battery.
- REUSE: `security/principals` shape only; journal; quarantine record pattern from B13.
- PORT: `SourceContractResolver.resolve(raw_envelope) -> ResolvedContract | QUARANTINED(raw_preserved)`; fingerprint derived by a function independent of the provider's own label.
- OWNERS: Producer: ingestion owner. Consumer: B01.
- STATE: Contract versions immutable; resolution outcome journaled with the raw digest.
- REFUSALS: Zero or >1 match -> QUARANTINED with raw bytes preserved; stale watermark -> HELD; discriminator without a passed challenge battery -> not usable.
- CALLPATH: None (ingestion is outside this repository).
- TEST: Two contracts match -> quarantine; zero match -> quarantine; label spoof with wrong fingerprint refused.
- EVIDENCE: PROPOSED_DESIGN.
- SOURCE-PRESENT: frozen DOCX s6 names the SOURCE_DATA_CONTRACT content (versioned contract, independently derived fingerprint, exactly-one match, freshness/watermark, challenge battery).
- INPUT: (distinct, still unbound) concrete per-provider contract instances, fingerprint function values, freshness source, admission. Consequence: resolver exactly-one/zero/many/stale logic is buildable and testable on candidate contracts; no provider is qualified. STATUS=INSTANCES_AND_ADMISSION_UNBOUND.

### B05 - Raw bytes != semantic identity; semantic epoch (DOCX s6, s21 Materialization)
- SOURCE: DOCX s6/s21; `epoch_reresolution` is a PROPOSED D25 helper.
- REUSE: `tracker/epoch_reresolution`, `tracker_identity.transition`, append-only journal.
- PORT: `SemanticEpochPort.advance(feature_ns, reason_ref) -> epoch_n+1`; `dependents(epoch_n)` marks materializations STALE_SEMANTIC_EPOCH.
- OWNERS: Producer: source owner of the epoch event. Consumer: materializer, Gateway.
- STATE: EPOCH_ADVANCED journal record; stale marking is a projection, never a rewrite of original-as-observed history.
- REFUSALS: Advance requires the fence and an evidence ref; replay returns the history as observed at each epoch.
- CALLPATH: Helper exists, no pipeline call.
- TEST: Epoch advance invalidates dependents and keeps original rows byte-identical (mutant: overwrite).
- EVIDENCE: Helper REFERENCE_ONLY; port PROPOSED_DESIGN.
- INPUT: Epoch object and invalidation event definition -> source owner; SOURCE_INPUT_UNBOUND.

### B06 - Formula-qualified identity (DOCX s7, s21)
- SOURCE: DOCX s7: ID+VERSION+FORMULA_HASH; same ID/version with different semantics fails closed.
- REUSE: `quant_intake_adapter.admit` recompute, `pipeline._accept`, `tracker_identity.content_identity`.
- PORT: Existing. No new port.
- OWNERS: Tracker (producer and consumer).
- STATE: CANONICAL_ACCEPTED body carries the three hashes; VERSION_CONFLICT on mismatch.
- REFUSALS: Different manifest under accepted version -> VERSION_CONFLICT; idempotent replay returns the same record.
- CALLPATH: INVOKED: `TrackerPipeline.run` -> `_accept`.
- TEST: Exists (test_pipeline VERSION_CONFLICT, idempotent replay, sweeps).
- EVIDENCE: IMPLEMENTED_TESTED against PROTOTYPE byte layouts.
- INPUT: Governed byte layouts (D3/D13) -> A02/SPEC owner; operational qualification not claimed.

### B07 - Definition-fit manifest and fitted-transform firewall (DOCX s7, s7A, s21)
- SOURCE: DOCX s7/s7A/s21; Composer V9 fit/generation sections.
- REUSE: `composer/expression/fit_generation.check_fit_refs`, accepted-generation dict in the pipeline.
- PORT: `FitFirewallPort.check(manifest, accepted_generations, fitted_state_refs) -> PASS | FUTURE_FITTED_STATE_LEAK | UNDETERMINED`.
- OWNERS: Producer: fit/generation owner. Consumer: intake.
- STATE: Accepted generations come from the journal (ML/FW generation records), never from a caller dict in qualified mode.
- REFUSALS: Reference presence is not content verification: UNDETERMINED when the generation record cannot be read.
- CALLPATH: INVOKED for reference presence with caller-supplied generations (a documented limit).
- TEST: Future-fitted ref refused; unread generation = UNDETERMINED (mutant: treat unread as pass).
- EVIDENCE: Presence check IMPLEMENTED_TESTED; content check PROPOSED_DESIGN.
- INPUT: Fitting-manifest content schema + accepted-generation provenance -> source owner; SOURCE_INPUT_UNBOUND.

### B08 - Dependency truth, DAG, contamination (DOCX s7, s7A, s21)
- SOURCE: DOCX s7/s7A: DAG, declared-vs-inspectable, transitive/cross-instrument contamination, similarity detector, default cross-instrument deny. Build Plan 14A/OB2.
- REUSE: `check_declared`, `independent_traversal`, `fw/lanes`, `health/blast_radius` (R19 mandatory closure adapter, cyclic refusal), `tracker/feature_lineage`.
- PORT: `FeatureDependencyStore` (read model over accepted QuantManifests: feature->feature edges from INPUT_DEPENDENCIES) feeding the existing injected probes; persisted by journal record, rebuildable.
- OWNERS: Producer: Tracker acceptance. Consumers: Health blast radius, FW/ML receivers.
- STATE: Edges derived from accepted manifest bodies; the derivation is deterministic; no separate authority.
- REFUSALS: Cyclic or unread lineage -> UNDETERMINED (R19); empty graph without unread is a resolved no-dependency fact.
- CALLPATH: Probes REFERENCE_ONLY. Missing binding: persistence/adapter, real manifest instances, D3 REF_TYPE vocabulary (which ref types denote a feature).
- TEST: Existing blast-radius suite incl. cycles; add a round-trip test once manifests persist.
- EVIDENCE: IMPLEMENTED_TESTED for propagation; persistence PROPOSED_DESIGN.
- INPUT: D3 REF_TYPE vocabulary; similarity detector + battery; cross-instrument policy -> A02/SPEC owner; SOURCE_INPUT_UNBOUND.

### B09 - Version-relationship layer (registry, Matrix-selected frozen post-core function)
- SOURCE: Registry source 1eZThdek... (read in full). The layer is the Matrix-selected FROZEN post-core function even though retained body headers still say candidate; this implementation remains candidate.
- REUSE: `tracker/version_relationship` (FIELD->DIMENSION partition, UNCOMPUTED/UNCOMPUTABLE).
- PORT: `VersionRelationshipPort.compute(old_version_ref, new_version_ref, diff_schema) -> {relationship_id, hash, outcome} | UNCOMPUTED | UNCOMPUTABLE`; the relationship object is journaled and pinned by historical replay.
- OWNERS: Producer: Tracker. Consumer: lifecycle, replay.
- STATE: One journal record; no second lifecycle authority.
- REFUSALS: UNCOMPUTABLE is reserved for genuinely missing/unverifiable HISTORICAL evidence (`classify_not_computed`); skipped work or a software failure is UNCOMPUTED (blocks the supersession claim, retryable) and is never UNCOMPUTABLE. UNCOMPUTED and UNCOMPUTABLE have distinct consequences (UNCOMPUTABLE routes to MATERIAL_ALTERNATIVE, UNCOMPUTED blocks supersession). CORRECTION requires VERIFIED predecessor-defect evidence; unknown field -> refuse.
- CALLPATH: Pure partition validator only.
- TEST: Partition totality/disjointness mutants (exist); add diff-engine tests when the diff schema exists.
- EVIDENCE: Partition IMPLEMENTED_TESTED.
- INPUT: Diff-schema instance + relationship object bytes + defect-evidence verification -> registry source owner; SOURCE_INPUT_UNBOUND.

### B10 - Terminal canonical identity and state (registry s8; DOCX s8)
- SOURCE: Registry s8; narrow Type1 CURRENT-ONLY EXACT semantics preserved (minimal Type1 sources 12TgjoKX..., 17wmtxF0..., authorization 13bEHX5f...).
- REUSE: `tracker_identity.search.identity_lookup` (unchanged), `stage_a/tracker/terminal_identity` (R19, R20-corrected).
- PORT: `resolve_terminal_identity(start_row, rows) -> TerminalIdentity(status, chain_facts, terminal_facts)`; `terminal_notes` = hints only.
- OWNERS: Producer: baseline store rows. Consumer: pipeline `_register_baseline` failure report.
- STATE: Reads the one baseline store; writes nothing; authorizes no claim, resurrection, delivery or near-match substitution.
- REFUSALS: Link scope = (era_id, instrument, timeframe); foreign-scope successor -> SURVIVOR_CROSS_SCOPE_LINK_UNPROVEN; conflicting same-scope candidates -> AMBIGUOUS in any row order; cycle/orphan refused; result independent of row order; hints never parsed back into identity.
- CALLPATH: INVOKED report-only from `_register_baseline`. Unchanged: lookup stays fail-closed.
- TEST: R19+R20 tests (comma/colon ids, permutations, foreign era/instrument/timeframe, conflicting successor, cycle/orphan, noncurrent terminal, unaffected current) with mutants.
- EVIDENCE: IMPLEMENTED_TESTED, UNQUALIFIED.
- INPUT: D1 production install of the construction authority (hard-False seam) -> Manager; the baseline connection is mandatory in qualified mode.

### B11 - Lifecycle, admissibility, quarantine states (DOCX s8, s10)
- SOURCE: DOCX s8/s10.
- REUSE: `pipeline._reject`, `lifecycle_status_event`, `tracker_identity.lifecycle`, `transition_record`.
- PORT: `LifecyclePort.transition(subject, from, to, evidence_ref) -> record | ILLEGAL_TRANSITION`, single state machine in `transition_record`.
- OWNERS: Tracker.
- STATE: Journal.
- REFUSALS: Classification is advisory; admissibility is a terminal precondition; unknown reason -> REJECTED (D15).
- CALLPATH: Admission failure path INVOKED; transitions beyond ACCEPTED/PUBLISHABLE/WITHDRAWN NOT_BUILT.
- TEST: State-machine table test (exists); add per-new-state negatives.
- EVIDENCE: Partly IMPLEMENTED_TESTED.
- INPUT: State-transition schema, reason mapping (D15), taxonomy service -> source owner; SOURCE_INPUT_UNBOUND.

### B12 - Eligibility as-of-T (DOCX s8, s21 Currentness)
- SOURCE: DOCX s8/s21: time-indexed, append-only, no silent fallback to current.
- REUSE: `replay.replay`, `currentness.resolve_asof` (AS_KNOWN/EVENTUAL), publication records.
- PORT: `EligibilityAsOf.lookup(ns, version, asof_seq) -> ELIGIBLE | NOT_ELIGIBLE | UNDETERMINED` derived only from QUALIFIED journals.
- OWNERS: Tracker producer; Gateway consumer.
- STATE: Derived from PUBLISHABLE/WITHDRAWN records of a qualified journal; read model rebuildable (`storage/postgres_read_model`, which refuses non-QUALIFIED journals).
- REFUSALS: Simulation journals refuse (R20); future asof refuses; no fallback to EVENTUAL for an AS_KNOWN question.
- CALLPATH: REFERENCE_ONLY.
- TEST: Exists for resolve_asof; add the simulation-refusal and restart-rebuild tests (R20 `test_r20_simulation_boundary`).
- EVIDENCE: IMPLEMENTED_TESTED for the resolver and the R20 boundary; ledger schema (ADD-4) unassigned.
- INPUT: Eligibility ledger schema -> ADD-4 owner; SOURCE_INPUT_UNBOUND.

### B13 - Quarantine, retry suppression, reverse dependency (DOCX s10, s21)
- SOURCE: DOCX s10/s21.
- REUSE: `epoch_reresolution`, `tracker_identity.stale_sweep`, `blast_radius`.
- PORT: `QuarantineLedger.append(subject, reason_code, freshness_proof)`, `reasons(subject)` (set, multi-reason, append-only), `reopen_trigger` != reactivation, `reverse_dependents(subject)` from B08 edges across retention tiers.
- OWNERS: Tracker.
- STATE: Journal records; retention-tier index is a read model.
- REFUSALS: Reason without freshness proof -> HELD; retry suppressed while a live reason exists; reconstructability unproven -> not purge-eligible.
- CALLPATH: None as a subsystem.
- TEST: Multi-reason set; retry suppression; reopen != reactivation (mutant: reopen reactivates).
- EVIDENCE: PROPOSED_DESIGN.
- INPUT: Reason ledger schema, retention tiers, reconstructability API -> Quarantine blueprint owner; SOURCE_INPUT_UNBOUND.

### B14 - L1/L2 verification and Recording Health (DOCX s9, s21)
- SOURCE: DOCX s9/s21.
- REUSE: `stateful_verifier.verify_materialization`, `independent_traversal`, `health/evidence`.
- PORT: `VerificationScheduler.reverify(feature_key, trigger) -> VerificationResult`. CORRECTION of an earlier appendix error: there is no `L2_REQUIREMENT=UNAVAILABLE`. Source states are L2_REQUIREMENT = REQUIRED | NOT_APPLICABLE_BY_GOVERNED_DEFINITION; L2_STATUS = UNAVAILABLE; RECORDING_HEALTH = UNKNOWN / NOT_HEALTHY. L2_REQUIREMENT=REQUIRED with L2_STATUS=UNAVAILABLE -> RECORDING_HEALTH UNKNOWN/NOT_HEALTHY (never silent L2->L1 fallback).
- OWNERS: Tracker verifier; Health consumer.
- STATE: Verification result journaled by hash; Recording Health is derived, never authority.
- REFUSALS: UNAVAILABLE L2 -> UNKNOWN; stale health cannot certify PASS.
- CALLPATH: One-shot at intake only.
- TEST: Fallback mutant; stale-health PASS mutant.
- EVIDENCE: One-shot IMPLEMENTED_TESTED (domain-limited; independent oracle is same author, D4).
- SOURCE-PRESENT: the three states above.
- INPUT: (unbound only) appointment/profile that sets L2_REQUIREMENT per feature family, and the transport that carries L2_STATUS. Consequence: continuous L1/L2 health logic is buildable over those states; assigning a requirement to a real family is held.

### B15 - Component vs contract health; localization packet (DOCX s17, s19)
- SOURCE: DOCX s17/s19; Build Plan 14A.
- REUSE: `health/envelope`, `health/evidence`.
- PORT: `LocalizationPacket.build(failure) -> packet` with root cause, first bad, affected, downstream, scope, safe action, unaffected.
- OWNERS: Health.
- STATE: Derived; no health state write by Tracker.
- REFUSALS: Missing field -> packet INCOMPLETE (fail closed).
- CALLPATH: REFERENCE_ONLY.
- TEST: Every field required; stale evidence refused.
- EVIDENCE: IMPLEMENTED_TESTED for envelope pieces.
- INPUT: Packet schema; Master Health interface; D17/D18 thresholds -> Health owner.

### B16 - Localized blast radius with positive controls (DOCX s19; registry s17, s19)
- SOURCE: Build Plan 14A/OB2/Q12/M4.
- REUSE: `health/blast_radius` (R19: probes mandatory, cyclic lineage refused), `fw/lanes` probes.
- PORT: Existing: `blast_radius(failed, consumers, feature_deps, closure_contains_target, closure_features, unread_features)`.
- OWNERS: Health consumer of Tracker lineage.
- STATE: Pure function; no write.
- REFUSALS: CLOSURE_PROOF_ADAPTER_REQUIRED, FEATURE_LINEAGE_CYCLIC/INCOMPLETE, GRAPH/CONSUMER_KEY_MISMATCH.
- CALLPATH: REFERENCE_ONLY (no real Health provider).
- TEST: Exists incl. unrelated-baseline positive control and mutants.
- EVIDENCE: IMPLEMENTED_TESTED.
- INPUT: Action for an UNDETERMINED non-required consumer -> Health owner.

### B17 - Versioning, release coupling (DOCX s18)
- SOURCE: DOCX s18.
- REUSE: `replay`, `transition_record`.
- PORT: `ReleaseIdentity.bind(component_versions, health_ref, evidence_hashes) -> release_id`.
- OWNERS: Tracker.
- STATE: Journal.
- REFUSALS: Unlinked evidence -> refuse bind.
- CALLPATH: None.
- TEST: Replay uses historical identities (exists); coupling object tests when defined.
- EVIDENCE: PARTLY.
- INPUT: Release-identity coupling object -> blueprint owner.

### B18 - Plane/role separation, restore (DOCX s4, s21 Restart; registry s18)
- SOURCE: DOCX s4/s21; Sydney probe (18aMPP7L...): S3 CAS alone does not enforce semantic fencing.
- REUSE: `coordination/recovery`, `fencing`, `storage/authority_class` (R20: simulation vs qualified keyspace).
- PORT: `WriterGate.append(...)` as a restricted writer that validates epoch/sequence semantically before the conditional put.
- OWNERS: Tracker plus storage provider.
- STATE: Journal + HEAD.
- REFUSALS: Old-epoch body with a current ETag refused by the gate (the probe's failing case).
- CALLPATH: Fence checks in `ObjectStoreJournal`; real provider absent (E-01 harness is tooling, PROVIDER_ACCEPTED=NO).
- TEST: Provider conformance harness stale-epoch case against a real provider.
- EVIDENCE: In-memory IMPLEMENTED_TESTED; provider NOT_QUALIFIED.
- INPUT: Database schemas/roles, restore drills, provider evidence -> storage owner (D5/D10).

### B19 - Authority transitions, evidence-truth (DOCX s7A, s21A)
- SOURCE: DOCX s7A/s21A: SIGNED != VALID; direct/admin writes cannot create current authority.
- REUSE: `ClaimService`, `check_transition`, fenced journal.
- PORT: `EvidenceResolver.resolve(ref) -> VALID | INVALID | UNRESOLVED`; transition requires VALID.
- OWNERS: Tracker.
- STATE: Journal.
- REFUSALS: UNRESOLVED evidence refuses the transition; qualified DutyEvidence must resolve through this port (today none exists, so qualified acceptance holds).
- CALLPATH: Evidence resolution NOT_BUILT.
- TEST: SIGNED-but-invalid refused.
- EVIDENCE: PARTLY.
- INPUT: Evidence-resolution API; restricted writer -> source/storage owner.

### B20 - Resolver determinism, research multiplicity (DOCX s7A, s21A)
- SOURCE: DOCX s7A/s21A.
- REUSE: `news_hub_v2.resolve_context` (order-independent).
- PORT: `SelectionLineage.record(attempt, family, selection_rule_ref)`; multiplicity count read by validation.
- OWNERS: Research/Tracker.
- STATE: Journal.
- REFUSALS: No outcome-based selection; MULTIPLE_CANDIDATES refuses rather than picks.
- CALLPATH: Resolver REFERENCE_ONLY.
- TEST: Order-independence (exists).
- EVIDENCE: PARTLY.
- INPUT: Attempt-lineage schema; battery registry; K3/CASE/counting policy (UNASSIGNED, never defaulted) -> research-policy owner.

### B21 - Consumer Gateway semantics (DOCX s12, s21)
- SOURCE: DOCX s12/s21; V0.38.
- REUSE: `gateway/v038`, `gateway/contracts.SimulatedGateway`.
- PORT: Real Gateway behind the same contract; direct-SQL denial needs a store boundary (B18).
- OWNERS: Gateway owner.
- STATE: FinalResolutionStore is single-process in memory (D10).
- REFUSALS: Required missing -> refuse; no silent substitution.
- CALLPATH: SIMULATED.
- TEST: Exists against the simulation.
- EVIDENCE: IMPLEMENTED_TESTED vs simulation only.
- INPUT: Real Gateway; D13/D15/D16 -> Gateway owner.

### B22 - Tracker-side AI boundary controls (DOCX s15, s21)
- SOURCE: DOCX s15/s21: AI reviewer boundary, creator != certifier. SALIX AI itself is out of scope; the TRACKER-SIDE controls are in scope.
- REUSE: `security/principals` shape, `ClaimService.issued_by`, `tracker_component/order`, the R18 no-self-certification pattern (`unresolved_mandatory`).
- PORT: `ReviewerInputGuard.check(review_request) -> ALLOWED | REFUSED`: (1) reviewer receives only declared inputs (no outcome-bearing data unless the order declares it); (2) reviewer output is a FINDING record, never a state mutation: it cannot call lifecycle transition, publication or claim APIs (structurally: no write handle is passed); (3) task origin/framing is recorded in the journal and a reviewer cannot rewrite its own task; (4) creator principal != certifier principal for the same artifact.
- OWNERS: Producer: Tracker. Consumer: any AI/human reviewer boundary.
- STATE: REVIEW_FINDING journal records are append-only evidence; they never change eligibility.
- REFUSALS: Same principal as creator and certifier -> REFUSED; reviewer handle with a write capability -> REFUSED at construction.
- CALLPATH: Not built. The no-self-certification pattern exists for claims and duty evidence.
- TEST: Creator==certifier refused; reviewer given a write handle refused (mutant: pass the handle).
- EVIDENCE: PROPOSED_DESIGN; part (4) is authorable now once principal identities exist.
- INPUT: Principal/grant appointments (D2) -> Owner; SOURCE_INPUT_UNBOUND for who the reviewer is.

### B23 - Negative controls for every protection (DOCX s21, s21A)
- SOURCE: DOCX s21/s21A falsifiability.
- REUSE: Mutation sweeps r5..r18, plus R19/R20 targeted mutants.
- PORT: Test discipline, no runtime port.
- OWNERS: Coder.
- STATE: n/a
- REFUSALS: A family with no implementation gets no green placeholder test.
- CALLPATH: n/a
- TEST: Each new refusal in this appendix lists a mutant.
- EVIDENCE: IMPLEMENTED for built modules.
- INPUT: None.

### B24 - Implementation blueprint (DOCX s22; registry s22)
- SOURCE: DOCX s22 and registry s22 name the blueprint's required content (schemas, APIs, state machines, write roles, indexes, migrations, caching, telemetry, restart, backup/restore, tests).
- REUSE: This appendix is the Coder's CANDIDATE counterpart; it is not the blueprint.
- PORT: n/a
- OWNERS: Core/Tracker blueprint owner.
- STATE: n/a
- REFUSALS: n/a
- CALLPATH: n/a
- TEST: n/a
- EVIDENCE: Blueprint: SEARCH_INCOMPLETE / NOT_LOCATED_IN_NAMED_SOURCES (the earlier statement that it does not exist is WITHDRAWN: absence in the sources searched is not absence).
- INPUT: Locate or supply the blueprint; E03 is a module map and cannot stand in for schemas. Source-present mechanics proceed meanwhile.

## Part 2: TR-01..TR-15 (what is built, what the next concrete piece is)
| Row | Existing reuse (callpath) | Proposed next concrete piece (candidate internal choice) | Targeted test / negative control | Unresolved input -> owner -> consequence -> disposition |
|---|---|---|---|---|
| TR-01 | `StatefulMaterializer.materialize` <- `pipeline.run` | `OpcodeTablePort` loading a governed opcode table by (id, version, hash) instead of `schema/candidate_code_tables` | unknown opcode refused; table hash mismatch refused | Numeric opcode table + program byte grammar (D3) -> A02/SPEC owner -> prototype grammar only -> supply table |
| TR-02 | `admit` + `tracker_identity` one registry path | None new: baseline connection is mandatory in qualified mode (R19); `baseline=None` is simulation only | qualified run without baseline HELD | D1 install of the construction authority -> Manager |
| TR-03 | `canonical_encoding`, `byte_primitives` | `CanonicalEncodingContractRef` carried with every encoded body | foreign contract ref refused | Sort rule/wire layouts D3/D13 -> SPEC owner |
| TR-04 | manifest/graph/program recompute | none | exists | Field semantics D3/D6 -> SPEC owner |
| TR-05 | `build_output_check`, `request_record` | resolve the P02/G01 association through existing s27 evidence refs (Part 5) | cross-attempt substitution refused | s27 prose fields + exact existing slots (Part 5) -> Composer package authority |
| TR-06 | `request_classification.route_from_adapter`; R20: qualified no-quant is `CLASSIFICATION_UNRESOLVED_HELD` | `RequestClassificationSource.classify(governed_request_ref) -> DIRECT_TRACKER_FEATURE / COMPOSER_BUILT_QUANT_FEATURE / NO_QUANT_FEATURE / UNRESOLVED` reading the governed request, so the three-way router at Tracker<->Composer (Build Plan 1256) is one request/identity authority | unbound ids -> UNRESOLVED (R20 test); genuine no-quant only via verified source or isolated simulation | source-owned mapping from governed request to classification (D8) -> Tracker/Composer request authority |
| TR-07 | `gateway/v038`, `fw/receiver`, `ml/receiver` | none until a real Gateway | exists vs simulation | D13-D16 -> Gateway owner |
| TR-08 | `health/*` | none | exists | D17/D18 -> Health owner |
| TR-09 | `certify`, `check_declared` | `CapabilityClassStructurePort.check(declared_class, structure) -> COMPATIBLE / INCOMPATIBLE / UNDETERMINED` | incompatible class refused; UNDETERMINED holds | compatibility semantics (Parent V1.2; Annex cert 3-6) -> source owner |
| TR-10 | `currentness`, `decision_context` | none | exists | D14 -> Manager |
| TR-11 | `claims`, journals | `WriterGate` (B18) | stale-epoch with current ETag refused | D5/D10 provider -> storage owner |
| TR-12 | `context/*` | none | exists | D13 encodings -> News Hub owner |
| TR-13 | `fw/*` | none until FW payload fields exist | exists | A04 bindings false; FW payload fields -> FW owner |
| TR-14 | `ml/receiver` (R20: `check_standalone`, `union_closure`) | see Part 4 | exists | ML edge schema + coverage witness -> ML source owner |
| TR-15 | `identifiers`, `keys`, `authority_class` | none | exists | none |

## Part 3: R20 authority-class boundary and qualified acceptance (design as implemented)
- Problem reproduced by Codex: a simulated acceptance in the ordinary namespace XAUUSD/H4/mom3 could be published and replayed as PUBLISHABLE; only the ephemeral Outcome said simulation.
- Design (no new canonical field): `storage/authority_class.SimulationStore` keeps all keys under `SIMULATION/`; journals, claims and the pipeline compute the class from the store. `TrackerPipeline` refuses a mismatch between the `simulation` flag and the class of its store, journals and claims (`AUTHORITY_CLASS_MISMATCH`). `publication.publish`, `ReadModel.rebuild/status/verify_against` and `StatusProjection` refuse a non-QUALIFIED journal (`SIMULATION_NOT_ELIGIBLE`). A QUALIFIED reader of the same bucket after restart/cache rebuild sees nothing simulated.
- Limits: an object that declares no class is treated as QUALIFIED; a wrapper that forgets the attribute would be mis-classed. There is still no real DutyEvidence verifier, so no QUALIFIED acceptance can be produced by a real run. The test helper `qualified_journal_from_simulated` hand-writes a record into a qualified store only to exercise publication mechanics; it is not an acceptance path.
- Callers updated: pipeline construction, publication, read model, status projection, `Rig` fixture, publication tests, restart test.

## Part 4: ML_STANDALONE union closure (MLCore 1cf1uR0w..., paras 99-118)
- Source-given: complete UNION closure over feature->feature, learned-feature->model/generation, generation->training/predictor, materialized-output and other content-carrying edges; administrative-only edges do not taint; unknown or incomplete required edges fail closed; FW-augmented generation is a taint source.
- Built (REFERENCE_ONLY): `ml/receiver.union_closure/check_standalone` traverse SUPPLIED (child, parent, class) edges; `require_standalone_qualified` ALWAYS refuses `UNION_CLOSURE_COMPLETENESS_UNPROVEN`. Traversing supplied edges is NOT a completeness proof.
- Held until: a source-owned edge schema (edge kinds, how the three classes attach to them) and a coverage witness (proof that the edge set supplied is the whole set). Proposed port once supplied: `EdgeSource.edges_for(root_ref) -> (edges, witness)`; qualify only when `witness` verifies; test: omit one edge -> witness fails -> refused (mutant: ignore witness).
- Existing duties are applied at the ML receiving boundary (`check_generation` linear chain stays labelled NOT union closure).

## Part 5: D3/D6 concrete slots from P02, G01, S02 (read by the Coder in R20 from Drive; PROPOSED / NOT ADMITTED; not admitted here)
Sources read in full by the Coder: P02 (22,129 B per S02's pin; Drive 1h7gxpXrHKcr_6pEnAQZvTKgzqEgEqo9w), G01 (21,637 B per pin; 16oK02ZU2MVxx5PEPuqD3qjNJFIrqntSv), S02 (Drive 19weJfitFvSi-PhwQWKpkzO2v9rZNERdW). Byte sizes/hashes quoted are the documents' own pins; the Coder did NOT recompute them in R20 (DERIVATION_CLASS = MANAGER_CLAIM for those hashes). All three say they are fixed-case, Composer-only, A02 literal ADD material (node0 +1.0, node1 +2.0, node2 ADD(left=node0,right=node1), root=node2): NOT a universal PROGRAM_REF grammar, NOT an opcode allocation, NOT admitted. The wire labels `A02_LITERAL_ADD_PROGRAM_P01` and `A02_ORDERED_GRAPH_G01` are document-local proposals.

SOURCE-PRESENT (usable): Parent V1.1 controlling arithmetic overlay SQE_OPSET_V1_1 finite binary64 ADD (nearest/ties-even, no fast-math/reassociation/contraction/FMA, FTZ/DAZ disabled, canonical +0, nonfinite refuses); Typed Annex V1.2 s I primitives (UINT32, VERSION_ID, BINARY64_BITS, REF, raw SHA-256). The arithmetic RULE is present; what is missing is the admitted REF / binding / program representation. These are different missing things and must not be conflated.

Still-unbound slots S02 names for a concrete D3/D6 source-owner return (each is `UNBOUND`; nothing is defaulted or fabricated):
| # | Slot | Responsible function | Candidate Tracker-side engineering that can be prepared now (not admitted) |
|---|---|---|---|
| 1 | Artifact class / reference class, namespace, identity/version rule, evidence home, validity (no numeric REF_TYPE allocated) | Composer package/SPEC authority | `ReferenceClassRegistry` lookup that refuses any unregistered class |
| 2 | Program representation identity/version/hash incl. registration of the label | Composer package/SPEC authority | decoder dispatch keyed by admitted (id, version, hash), not by the label |
| 3 | Decoder/spec REF and compatibility with P02 + the existing evidence-reference slot | Composer representation authority with Tracker intake | `ProgramDecoderPort.decode(bytes, admitted_decoder_ref) -> NodeGraph | REFUSED` |
| 4 | ARITHMETIC_CONTRACT_REF type/ID/version/hash | arithmetic source authority | carry-through check that program and graph refs are equal |
| 5 | LOGICAL_ENCODING_CONTRACT_REF | encoding source authority | same equality check |
| 6 | Graph contract identity/version/hash and the exact existing s27 construction-graph slot | Composer graph/SPEC authority | `GraphDecoderPort` symmetrical to #3 |
| 7 | Program<->graph comparison contract + verification-policy identity/hash + replayable evidence mapping under s28 | Tracker intake authority | `compare_program_graph(program, graph) -> MATCH | MISMATCH(reason)` incl. the swapped-input cases G01 s4 lists |
| 8 | Package association: BUILDER_BUILD_ID, ORDER/CLAIM/CREATION_REQUEST ids, manifest/evidence-reference schema and locators resolving program, decoder, graph and contracts from one immutable package | Composer package authority with Tracker intake/journal | `SameAttemptAssociation.verify(package, journal) -> BOUND | CROSS_ATTEMPT | UNRESOLVED` |
| 9 | Journal namespace/profile identity, RD4a field paths, package/report/evidence resolver + integrity coverage, accepted epoch/sequence/HEAD locator, accepted-chain entry locator, review-successor locator | Tracker journal/lifecycle + environment/SIFP namespace functions | maps onto the existing fenced journal records; field paths remain UNBOUND |
| 10 | Case/SPEC: subject id + spec identity, target/invocation, instrument/profile, policy/proxy/search envelope, request + expected-delivery contract, producer/evidence-home closure | request/Tracker/SPEC authorities | none (unassigned normative content) |
Effect on the present code: the pipeline admits an expression `Manifest` (a quant program); the P02 artifact is a Composer-only description resolved through s27 evidence references, which `pipeline.run` does not do. Until slots 1-8 are admitted the A02 case cannot flow through intake as P02/G01 describe, and the Coder builds no P01/G01 parser (that would present a proposed byte layout as operative). Hashes of the Drive documents are document-byte hashes and never program-body, graph-body, package or report hashes. The same-attempt rule (G01 s5, S02 s3): matching hashes or matching numeric 3.0 never prove origin; each attempt must prove its own association; S02's A02-only no-cross-attempt-reuse restriction is PROPOSED and does not disable mandatory identity/duplicate lookup. S02's signer finding (no qualified technical admitting principal evidenced; evaluator bootstrap unresolved) is an authority input, not Coder work, and the existing 2A delegation is not treated as technical admission.

## Part 6: E03 paths not yet real code
| E03 # | Path | Proposed | Input needed |
|---|---|---|---|
| 9 | composer/governed_order_adapter | none: Tracker is sole order issuer (`tracker_component/order`, `authority_bridge`); Composer side LATER | Composer-owned |
| 10, 11 | build_executor, refit_executor | none: Composer-owned | Composer-owned |
| 48 | health/expectation | `ExpectationRule` port reading a governed expectation object | expectation rule (D17/D18) |
| 28-37, 38-47 | context/gateway/fw/ml/health aliases | keep alias mapping (no gratuitous rename); real providers behind the existing contracts | provider evidence |
The `tests/stage_a` sub-trees concurrency, golden_mirrors and e2e stay NOT_BUILT because no real counterpart exists to mirror.

## Part 7: D1-D18, D12' (what the Coder can prepare vs the unassigned input)
| Row | Authorable now | Unassigned input (never defaulted) |
|---|---|---|
| D1 | `ClaimService.authorizes` hook already tested; install point design: one `construction_authority` provider handed to the baseline at composition time | Manager records the install point |
| D2 | `principals.GRANT_EVIDENCE_FIELDS` shape only | Owner appointment of signer/anchor |
| D3 | candidate code tables; Part 5 decoder/graph ports | REF_TYPE vocabulary, opcode table, grammar, sort rule |
| D4 | harness for an independent oracle; Claude authors, Codex re-derives/challenges expected bytes (not a staffing blocker) | runtime creator!=certifier and source-principal requirements remain; independence limitation recorded |
| D5 | `tests/provider_conformance` | real provider evidence |
| D10 | cross-journal atomicity design on one fenced journal family (B18 WriterGate) | real provider evidence |
| D6 | `docs/proposals/D6_composer_s27_mapping.md`; Part 5 slots | prose-only s27 field semantics |
| D7 | none | certified-ABSENT producer/certifier |
| D8 | `RequestClassificationSource` (TR-06) | source mapping |
| D9 | dependency-direction test | Manager mapping record |
| D11 | none | lane names |
| D12 | resolved in V0.38 text; code follows | n/a |
| D12' | unknown reasons REJECTED | REQUEST_AFTER_CUTOFF trigger |
| D13 | inequality checks | byte layouts |
| D14 | tests pin the divergence | cutoff vs fence |
| D15 | candidate list | reason->status |
| D16 | none | delay value |
| D17 | `health/*` | News/Context Health profile home |
| D18 | `health/*` | thresholds, flap limits, critical set, registry |

## Part 8: A07-1..4 (programme obligations stay visible; integrity checks do not clear them)
- A07-1 100 ML qualifiers: Codex independently verified extract 1Avpm0dF... (1,019,411 B, SHA fd594244...), 100 range hashes with 0 mismatch, CSV 100 rows / 41 units / 65 with no current ref, and the MLCore native 1692 paragraphs = extract capture 180,872 B SHA 0579d71c... (text-snapshot integrity only). The Coder did not recompute these in R20. These are integrity facts, not dispositions: of the 35 current-line-cited qualifiers, 12 weak, 19 partial and 4 strong lexical hints prove no disposition; NL-0187 (V235) qualifier_comparison (shadow counters) vs display-visibility inconsistency is a bounded candidate correction and the EVERY-display question stays open. See `docs/proposals/ML_joins_and_qualifiers.md`.
- A07-2 staffing: settled (Owner Direction Addendum R02); reconciliation/incorporation/readback of the R06 text open.
- A07-3 whole-domain history: open (Drive Activity export or scoped waiver).
- A07-4 currentness/effectiveness remainder (A01 currentness, QC34, D19/D22, D23/D24/D26/Q03): open with named source owners.
- Source/qualifier/currentness/history/procedure/QC remainder stays visible. Sallah's sign-off and all gates stay separate.


## R21 implementation note
B01, B03, B04, B05, B13/quarantine, B14 and the as-of eligibility / reviewer guard now have IMPLEMENTED_UNQUALIFIED internal ports in `stage_a/core/tracker_core.py` over candidate carriers (simulation evidence); the composition path feeds the real Gateway, FW and ML receivers (`tests/trk_stage_a/test_r21_core.py`). Byte encodings, calendar rules and provider proof remain unbound.
