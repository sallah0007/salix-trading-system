# R53 — per-row publication into the SIM publication path (candidate)

`stage_a/tracker/row_publication.py::RowPublication.publish` derives ONE SIM_STATUS_FACT (existing `SimulationPublicationPath.commit`, StatusProjection, Gateway: unchanged) from the committed record chain instead of caller-supplied row fields.

DERIVED: the ROW_ACCEPTED record read back from the row namespace journal; the stored PendingRow (re-verified on load); the accepted feature-version manifest (bytes re-hashed). The row must bind that feature_version and quant_manifest_hash. AVAILABLE_ASOF = the acceptance record's time. The typed transition hash is recomputed by the independent encoder and the producer and must equal the recorded one; the canonical_transition_ref carries it. Origin = ROW_ACCEPTED seq/hash + row hash.

SUPPLIED / HELD (not invented): status token (through the path's status_map; PUBLISHABLE never read as CURRENT), sequence, VISIBLE_AT (no ordering vs AVAILABLE_ASOF is asserted), projection HASH (no rule defined), vintage mode, source/causal policy ref.

Tests (6): derived-field delivery through Gateway; replay returns same record; not accepted / other feature key / PUBLISHABLE token write nothing; different token on replay refused; manifest-hash and feature-version mismatches; forged later duplicate record refused. Mutants killed: acceptance not required, version binding, manifest binding, hash compare, replay token, replay lookup, as-of derivation, last-record choice.
Surviving (equivalent): skipping only the PRODUCER-side transition hash comparison (the independent hash is still compared and both encoders agree on every valid input).

Limits: SIM only; no per-row A1 SUBJECT_STATUS_EVENT (lifecycle-kind vocabulary does not cover ROW_ACCEPTED; no mapping invented); the Composition/FW/ML delivery route and the E05 rebuild over these side records are not yet wired for the per-row route. Clears no gate/hold.
