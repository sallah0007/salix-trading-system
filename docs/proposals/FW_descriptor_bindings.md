# FW ten descriptors — proposed seven-field binding records (PROPOSED)

STATUS: PROPOSAL. Source statuses are from the Build Plan mapping/dependency disposition (Drive id in coder_returns; not copied). All ten real payload bindings are UNDECLARED. `require_real_binding` now refuses anything that is not a shape-valid seven-field record, but shape validity is NOT admission.

| # | Descriptor | Source status | Producer | Proposed type/rule | Source gap |
|---|---|---|---|---|---|
| 1 | OBSERVATION_REF | PARTIAL_SOURCE_CARRIER | FW observation record | ref (id, sha256) to the observation; must resolve to a row whose AVAILABLE_ASOF precedes the fence | source carrier is partial: exact carrier field not named |
| 2 | DEPENDENCY_INTERVAL_START | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | FW dependency descriptor | timestamp; START <= END; half-open convention must be stated by source | schema field exists, no instance binding |
| 3 | DEPENDENCY_INTERVAL_END | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | FW dependency descriptor | timestamp; END < fence (strict, V0.38) | schema field exists, no instance binding |
| 4 | HORIZON_ID | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | FW horizon registry | text id from admitted horizon registry | schema field only |
| 5 | HORIZON_VERSION | DIRECT_SCHEMA_FIELD_NOT_INSTANCE | FW horizon registry | text version bound to HORIZON_ID | schema field only |
| 6 | SEGMENT_REF | MISSING_EXACT_SOURCE_MAPPING | FW / segment owner | ref to authorised segment; exact source mapping MISSING | source supplies no exact mapping; proposal: reference into AUTHORIZED_SEGMENT_SET members only |
| 7 | AUTHORIZED_SEGMENT_SET | DIRECT_SCHEMA_CARRIER_NOT_INSTANCE | Segment authority | sorted unique set of segment refs, with set hash | carrier exists in schema, no instance |
| 8 | KNOWABLE_AT | MISSING_EXACT_SOURCE_MAPPING | FW causal clock | timestamp; causal, NOT identity timestamp; must be <= decision cutoff | exact source mapping MISSING; clock domain depends on E4 |
| 9 | ADMISSIBILITY_STATE | INTERNAL_DERIVATION_UNBOUND | Tracker internal derivation | derived enum from the above fields; no stored authority | derivation unbound: rule not in sources |
| 10 | VINTAGE_REF | PARTIAL_SOURCE_CARRIER | FW vintage registry | ref (id, sha256) to vintage; partial carrier | vintage lineage rule not fully source-stated |

## Proposed binding record shape (same for each descriptor; values to be supplied by source owner)
```
scope:                 FW -> Tracker descriptor <NAME>
interface_id:          <Manager-assigned>
version:               <FW contract version>
content_hash:          <sha256 of admitted descriptor definition bytes>
source_authority:      <governed doc id + range>
acceptance_record:     <Manager acceptance id>
validity/supersession: <valid-from, supersedes>
```
Missing admission (single): Manager acceptance of the FW descriptor interface, one record per descriptor or one covering record listing all ten.

Drift guard: tests/trk_stage_a/test_r09_proposal_docs.py checks all ten names appear.
