# R54 row audit (WIRING derived from the current tree; verdicts = Coder reading; NOT a gate)

Equality of this table with the generator proves transcription only. WIRING is recomputed from importers in stage_a/ + tracker_component/. A module with TEST_ONLY wiring is an exercised generic connection, not an integrated caller. Rows with no verdict were not re-read in R54 and carry their R43-R54 clause-table reading.

| Row | Status | Source | WIRING (computed) | Tests exist | R54 verdict |
|---|---|---|---|---|---|
| B01 | SD | S4 Reg p99; S3 | core/tracker_core: importers=contracts,reverification | YES | not re-read in R54 |
| B02 | IA | S4 Reg p97-102 | core/time_family: importers=snapshot_binding,tracker_core; tracker/snapshot_carrier: importers=observation_snapshot | YES | not re-read in R54 |
| B03 | IA | S4 Reg p104-124; S5 | tracker/registry_semantics: importers=registry_entry,registry_integrity,snapshot_binding,snapshot_carrier | YES | not re-read in R54 |
| B04 | SD | S4/S3 s6 | tracker/quant_intake_adapter: importers=pipeline,request_classification,separated_caller | YES | not re-read in R54 |
| B05 | MR | S3 s6 p6-8 | n/a (no module cited) | YES | not re-read in R54 |
| B06 | SD | S4 Reg p129 | storage/byte_primitives: importers=atomic_publication,composition,evidence_resolver,object_store_journal+12; tracker/accepted_manifest: importers=composition,sim_publication_path | YES | not re-read in R54 |
| B07 | IA | S4 Reg p130-134,194-195 | n/a (no module cited) | YES | R54: composer/expression operators exercised by R45-R47 parity tests; invoked by the intake/verification path, normative bytes held. |
| B08 | SD | S4 Reg p133-136,167-170,192-199 | n/a (no module cited) | YES | not re-read in R54 |
| B09 | SD | S4 Reg p137-165,322,377 | n/a (no module cited) | YES | not re-read in R54 |
| B10 | IA | S4 Reg p234-253 | n/a (no module cited) | YES | not re-read in R54 |
| B11 | SD | S4 Reg p201-233,267-279 | coordination/lifecycle_framework: PARAMETER:reached only through the `lifecycle=` PARAMETER of Composition.accept_and_publish (object supplied by the caller; policy unbound => HELD); tracker/status_emitter: PARAMETER:reached only through the `status_emitter=` PARAMETER of Composition.accept_and_publish (caller-supplied object; mapping supplied) | YES | R54: lifecycle_framework is reached through a caller-supplied parameter; edge matrix unadopted (R54_DECISION_PACK s4). |
| B12 | SD | S4 Reg p219-222 | n/a (no module cited) | YES | not re-read in R54 |
| B13 | IA | S4 Reg p260-287 | n/a (no module cited) | YES | not re-read in R54 |
| B14 | IA | S4 Reg p203-212,254-259 | n/a (no module cited) | YES | not re-read in R54 |
| B15 | SD | S4 Reg p367-381; S9 | health/envelope: importers=adapters,expectation; health/expectation: importers=composition | YES | not re-read in R54 |
| B16 | SD | S4 Reg p382-408 | health/blast_radius: importers=impact_supplier | YES | not re-read in R54 |
| B17 | MR | S10 bounded prefix (Manager evidence) | n/a (no module cited) | YES | not re-read in R54 |
| B18 | OP | S4 Reg p394-399; S3 s4/s21 | n/a (no module cited) | YES | R54: planes enforced on restart (test_r54_shared_rebuild plane test) and E05 rebuild exercised on the shared assembly's own durable records; data/control/recording plane NAMES beyond the four source-named planes are not invented. |
| B19 | OP | S4 Reg p185-188 | n/a (no module cited) | YES | not re-read in R54 |
| B20 | OP | S4 Reg p173-180 | n/a (no module cited) | YES | not re-read in R54 |
| B21 | IA | S4 Reg p301-323; S6 | fw/outcome_desk: importers=augmented_desk,composition,h1_record; gateway/h1_record: importers=augmented_desk,outcome_desk | YES | R54: FW+ML delivery on the real assembly is exercised (test_r53_real_assembly_base, test_r54_shared_rebuild): Composition.deliver/deliver_ml -> Gateway window path -> DurableFinalResolutionStore; E05 final-resolution rebuild from those records is exercised after cold restart. Composition.outcome_desk (R54) binds the H3 desk to the Composition Gateway; exercised after cold restart. Counterpart FW/ML processes and a production CBID source are NOT integrated. |
| B22 | MR | S4 Reg p353-366 | n/a (no module cited) | YES | not re-read in R54 |
| B23 | IA | S4 Reg p431-433,469,481-482; S9 MLHealth | ml/augmented_desk: TEST_ONLY; ml/consumer_path: TEST_ONLY; ml/shadow_ledger: importers=shadow_publication; ml/shadow_publication: TEST_ONLY | YES | R54: ml/consumer_path, ml/augmented_desk and ml/shadow_publication have NO production importer: they are exercised generic connections (tests), not wired into Composition. Composition.deliver_ml uses ml/receiver.build_row only. Reverse-H1/six-join/augmented association are therefore documentary+exercised, not integrated. Remaining: a governed caller (ML function) that invokes them. |
| B24 | MR | S10 bounded prefix | n/a (no module cited) | YES | not re-read in R54 |
| D1 | MR | S6 | tracker/construction_binding: PARAMETER:reached through claims authorizes() callsite, qualified resolver always False | YES | R54: construction_binding is consulted at the claims callsite; qualified resolver is always False. |
| D2 | MR | - | n/a (no module cited) | YES | not re-read in R54 |
| D3 | SD | S2 s6.2/6.3; S5 SQE_OPSET_V1_1; Annex I | schema/candidate_code_tables: TEST_ONLY | YES | R54: candidate_code_tables has no production importer by design (candidate tables for tests/proposal); not an engine input. |
| D4 | MR | - | n/a (no module cited) | YES | not re-read in R54 |
| D5 | OP | S6 | n/a (no module cited) | YES | not re-read in R54 |
| D6 | SD | S7 | n/a (no module cited) | YES | not re-read in R54 |
| D7 | MR | - | n/a (no module cited) | YES | not re-read in R54 |
| D8 | SD | S3/S4 manifest; Manager 14:47 | n/a (no module cited) | YES | not re-read in R54 |
| D9 | MR | - | n/a (no module cited) | YES | not re-read in R54 |
| D10 | OP | S2 R3 E01-H1 p1021-1026; E01-M1 | tracker_component/lifecycle: importers=generation_lifecycle,registry_entry,registry_integrity,shadow_publication+2 | YES | R54 CORRECTION: the status owning emitter is wired (called through the `status_emitter=` parameter of Composition.accept_and_publish, not imported; test_r50_composition_emitter). The ShadowLedger publication caller `ml/shadow_publication` is NOT called by Composition or any production module (grep: no importer); it is a standalone caller class exercised by tests only. The earlier R54 text saying it is called from Composition.accept_and_publish is WITHDRAWN. Lifecycle apply is a supplied-parameter call. |
| D11 | SF | S2/S6 | n/a (no module cited) | YES | not re-read in R54 |
| D12 | SF | source text | n/a (no module cited) | YES | not re-read in R54 |
| D12' | SD | - | n/a (no module cited) | YES | not re-read in R54 |
| D13 | SD | - | n/a (no module cited) | YES | not re-read in R54 |
| D14 | IA | S8; S10 prefix lines 538-544 | n/a (no module cited) | YES | not re-read in R54 |
| D15 | IA | S6 | stage_a/gateway/v038: importers=contracts,durable_final_store,e05_sources,h1_record | YES | not re-read in R54 |
| D16 | OP | S6 | n/a (no module cited) | YES | not re-read in R54 |
| D17 | SD | S9 | n/a (no module cited) | YES | not re-read in R54 |
| D18 | SD | S9 | n/a (no module cited) | YES | not re-read in R54 |
| A07-1 | MR | A07 ZIP 6e599c5d / extract fd594244 (recomputed match) | n/a (no module cited) | YES | not re-read in R54 |
| A07-2 | MR | R06 candidate V240 (raw recovered by Manager, sha256 f9d9aa9a, 13,903 B) | n/a (no module cited) | YES | not re-read in R54 |
| A07-3 | OP | V10 (Manager reading) | n/a (no module cited) | YES | not re-read in R54 |
| A07-4 | MR | - | n/a (no module cited) | YES | not re-read in R54 |
| TR-01 | SD | S2 s27 | n/a (no module cited) | YES | not re-read in R54 |
| TR-02 | MR | S2 s27 | n/a (no module cited) | YES | not re-read in R54 |
| TR-03 | SD | S2 s27 | composer/expression/canonical_encoding: importers=artifacts,hashing,pipeline,reverification+1 | YES | not re-read in R54 |
| TR-04 | SD | S2 s27 | expression/manifest: importers=accepted_manifest,artifacts,build_output_check,canonical_encoding+19 | YES | not re-read in R54 |
| TR-05 | MR | S2 s27; S7 | composer/request_record: importers=intake,quant_intake_adapter | YES | not re-read in R54 |
| TR-06 | SF | S2 s27; Manager input | n/a (no module cited) | YES | not re-read in R54 |
| TR-07 | IA | S2 s27; S6 | fw/receiver: importers=augmented_desk,composition,consumer_path,lanes+1; ml/receiver: importers=augmented_desk,composition,consumer_path,lanes+1 | YES | not re-read in R54 |
| TR-08 | SD | S2 s27; S9 | n/a (no module cited) | YES | not re-read in R54 |
| TR-09 | MR | S5 | verification/stateful_verifier: importers=pipeline,reverification,separated_caller,separated_handlers+2 | YES | not re-read in R54 |
| TR-10 | SF | S2 s27 | n/a (no module cited) | YES | not re-read in R54 |
| TR-11 | OP | S2 s27 | n/a (no module cited) | YES | not re-read in R54 |
| TR-12 | IA | S2 s27; S8 | context/event_context_store: TEST_ONLY | YES | R54: context/event_context_store has no production importer (only e05_sources references it by name); event/context correction records are exercised generic code, not wired into delivery. Remaining: the Context function caller that records and the Gateway/Health consumer that reads them. |
| TR-13 | IA | S2 s27; S6 | gateway/h1_record: importers=augmented_desk,outcome_desk | YES | not re-read in R54 |
| TR-14 | IA | S2 s27; S9 | ml/augmented_desk: TEST_ONLY; ml/consumer_path: TEST_ONLY; ml/shadow_ledger: importers=shadow_publication; ml/shadow_publication: TEST_ONLY | YES | R54: same as B23 for ML shadow/augmented: exercised generic only; association stays HELD; no Composition-level caller for the publisher. |
| TR-15 | IA | S2 s27 | storage/keys: importers=accepted_manifest,dataset_authority,e05_sources,object_store_journal+6 | YES | not re-read in R54 |
