# R53 — per-row publication into the SIM publication path (candidate)

`stage_a/tracker/row_publication.py::RowPublication.publish` derives ONE SIM_STATUS_FACT (existing `SimulationPublicationPath.commit`, StatusProjection, Gateway: unchanged) from the committed record chain instead of caller-supplied row fields.

DERIVED: the ROW_ACCEPTED record read back from the row namespace journal; the stored PendingRow (re-verified on load); the accepted feature-version manifest (bytes re-hashed). The row must bind that feature_version and quant_manifest_hash. AVAILABLE_ASOF = the acceptance record's time. The typed transition hash is recomputed by the independent encoder and the producer and must equal the recorded one; the canonical_transition_ref carries it. Origin = ROW_ACCEPTED seq/hash + row hash.

SUPPLIED / HELD (not invented): status token (through the path's status_map; PUBLISHABLE never read as CURRENT), sequence, VISIBLE_AT (no ordering vs AVAILABLE_ASOF is asserted), projection HASH (no rule defined), vintage mode, source/causal policy ref.

Tests (6): derived-field delivery through Gateway; replay returns same record; not accepted / other feature key / PUBLISHABLE token write nothing; different token on replay refused; manifest-hash and feature-version mismatches; forged later duplicate record refused. Mutants killed: acceptance not required, version binding, manifest binding, hash compare, replay token, replay lookup, as-of derivation, last-record choice.
Surviving (equivalent): skipping only the PRODUCER-side transition hash comparison (the independent hash is still compared and both encoders agree on every valid input).

Limits: SIM only; no per-row A1 SUBJECT_STATUS_EVENT (lifecycle-kind vocabulary does not cover ROW_ACCEPTED; no mapping invented); the Composition/FW/ML delivery route and the E05 rebuild over these side records are not yet wired for the per-row route. Clears no gate/hold.

## Addendum — side-HEAD pinning (Manager race finding on f25ff53)
Finding (reproduced by the reviewer through public ports): two RowPublication instances on one path; p1 preflighted an empty side journal, p2 landed the same row, p1's `path.commit` re-read a NEW side HEAD and appended too: side sequences [1,1], cold projection refused SEQUENCE_NOT_INCREASING.
Fix: the side and owning heads are pinned BEFORE the replay lookup and sequence validation, and the single append is compare-and-append against that basis (`expected_side_head`, `expected_source_head`), the StatusEmitter pattern. HeadMismatch/UnknownCommit/source-advance re-read and re-validate (an exact replay returns the genuine winner; a landed unknown is found as the replay; an absent one is re-attempted); exhaustion refuses. Also added (found while testing): per-MV sequence strictly increasing and AVAILABLE_ASOF non-decreasing (chain_status rules) are validated at the pinned basis, so an older accepted row cannot follow a newer one for the same MV.
Tests: concurrent exact replay (one effect, cold projection authoritative); different row same MV sequence refused; older-asof row refused; unrelated MV unaffected; unknown landed/absent; sequential replay control. 8 of 9 mutants killed; surviving: reordering the head pin after `_derive` (derive reads no side state; the owning-head pin then follows the manifest read) - equivalent for the side journal. No cross-HEAD atomicity is claimed.
