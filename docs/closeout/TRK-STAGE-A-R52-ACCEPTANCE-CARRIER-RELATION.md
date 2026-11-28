# R52 — relation of the journal acceptance record to the typed CanonicalTransition (Manager 21:37 request)

DERIVATION_CLASS = INDEPENDENTLY_DERIVED. EXACT_INPUTS = Build Plan capture lines 2244–2286 (R3 E01-H1/E01-M1), 3162–3202 (5.5/5.5A), repo main 77d896b (stage_a/tracker/pipeline.py, tracker/materialization/stateful_materializer.py, schema/objects.py, coordination/object_store_journal.py, schema/candidate_code_tables.py). METHOD = read the operative clauses, then trace the real callpaths. REPRODUCIBLE_BY_MANAGER = YES.

## What the operative R3 text says (own words)
E01-H1: the transition journal plus its single mutable HEAD is the authority; the accepted transition itself carries the status/currentness change; a status key space is only a rebuildable projection. E01-M1: authoritative acceptance is the successful conditional CAS that installs THE TRANSITION HASH into the namespace HEAD; an object written earlier is only a candidate. 5.5/5.5A: the canonical transition binds row hash, predecessor state, result, commit point identity, accepted-at, transition hash, status-event ref, epoch/fencing identity and idempotency identity; AVAILABLE_ASOF == CANONICAL_ACCEPTED_AT.

## What the code actually does (callpaths)
1. HEAD (`object_store_journal`): `head/<ns> = {seq, hash, epoch}`; the CAS installs the JOURNAL RECORD HASH (`record_hash(seq, prev, kind, canonical body json)`). Epoch is carried in HEAD, not in the record body.
2. The acceptance body (`pipeline._accept`) carries feature key/version, manifest/graph/program hashes, attempt id, verification hash, certification hash, claim witness, safe-intake report hash, materialization hash and (candidate, PR #127) `canonical_accepted_at`. The record hash therefore covers all of those and the chain predecessor: this is the installed "transition hash" in this repository.
3. `stateful_materializer.materialize` returns a PROBE-LEVEL record (manifest/graph/program hashes, probe batch and incremental outputs, byte length, `materialization_hash` = domain hash of that record). It does NOT produce a typed `StatefulMaterializationRow` (no state tuple, step_index, event_time, input refs/hashes, step class, predecessor row hash, speculation mode). So `schema/objects.PendingRow` / `row_content_hash` has NO production producer, and therefore `CanonicalTransition.row_content_hash` cannot be filled from a real row.
4. `schema/objects.CanonicalTransition/transition_hash` and `schema/independent.transition_hash` are constructed only in tests (`test_schema_annex`, `test_boundaries`): schema/oracle layer.
5. Code tables (`candidate_code_tables.py`, header says PROVISIONAL / D3): `TRANSITION_STATUS_EVENT = ("PUBLISHABLE",)`, so the typed transition's status-event code for an ACCEPT does not exist in the candidate tables; `CURRENTNESS_STATE` has CURRENT etc.

## Field-by-field bridge map (typed CanonicalTransition field -> journal-side source)
| Typed field | Source in the live path | Status |
|---|---|---|
| row_content_hash | none (no typed row is produced) | NOT AVAILABLE |
| verification_evidence_ref | `verification_hash` in the body (Ref shape needs target id/version) | PARTIAL (shape mapping not source-stated) |
| sifp_fencing_epoch | HEAD epoch at the CAS (not in the body) | AVAILABLE from the journal, not recorded in the body |
| canonical_commit_point_id (id128) | no clause defines its derivation in the lines read; (seq, prev hash) is the only commit-point notion present | NOT AVAILABLE without a rule |
| canonical_accepted_at / available_asof | candidate body field `canonical_accepted_at` from the supplied port | AVAILABLE only when a port was bound; equality holds by construction (one value) |
| gate_dependency_transition_ref | Optional, absent | OK (None) |
| currentness_state_at_acceptance | CURRENT is the only value an acceptance can carry here; the code is table-defined | PROVISIONAL |
| status_event | no ACCEPT code in the candidate table | NOT AVAILABLE |

## Conclusion (not a request for the Manager to pick a hash)
The candidate journal record hash is the installed authority today and is kept (history and legacy reads unchanged). A typed-transition bridge cannot be built honestly yet because three INPUTS DO NOT EXIST in the live path, not because a choice is pending: (a) a production StatefulMaterializationRow (the materializer is probe-level), (b) a derivation rule for the commit-point id128, (c) an admitted code table value for the acceptance status event. Everything else maps (see table).
Exact irreducible inputs and roles: (a) Tracker materialization owner: the per-bar row contents (state tuple, step index, event time, input refs) and their evaluator state semantics; (b) Manager/Owner: the commit-point id derivation clause (if the Build Plan lines I have not yet read define it, it will be cited and built); (c) Manager/Owner: admission of the D3 code tables.
Consequence: the typed hash cannot be cited as the acceptance hash; the journal record hash can, as a candidate. Recommendation: build (a) next as the Tracker-owned materialization row path; until then keep the journal record as the carrier and record the mapping above. No hash authority, units, clock or +1 were invented.
Not yet checked: whether the Build Plan lines not yet read (2440–2960, 3232–3335, 4260–5234) or the Typed Schema Annex define the commit point identity.
