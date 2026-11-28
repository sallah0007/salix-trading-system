# R53 — per-row route delivered to BOTH FW and ML on the real assembly (SIM, tests only)

Chain exercised (all real modules, SIMULATION): CommittedRowChain -> independent row-step verification (registry-bound schema identity + invariant stage) -> epoch-fenced RowAcceptor -> RowPublication (derived SIM_STATUS_FACT) -> Composition.recover_publication -> Core health -> Gateway.resolve_window -> `Composition.deliver` (FW) and `deliver_ml` (ML).
Results: accepted+published rows deliver to FW (Binding) and ML (included); a row that is accepted-but-unpublished, or never accepted, is NON_DELIVERY (FW) and publication of an unaccepted row is refused ROW_NOT_ACCEPTED; the affected feature (ancestry never declared) stays denied for FW and excluded for ML even with an accepted+published row.

FINDINGS (not decisions):
1. The Gateway encodes the delivered row with its OWN code tables. The per-row path carries a CANONICAL_TRANSITION_REF whose type is only in the candidate row tables; the existing test Gateway tables (ref type "R") refuse it (UNKNOWN_REF_TYPE), and the candidate tables lack DATA_VINTAGE_MODE (KeyError). The test therefore builds a SIM-MERGED table (candidate row tables + test enums). A single admitted code table covering both is a source-owner input (code-value admission, D13); none is invented here.
2. The Gateway window argument is the FENCE (visible_at/available_asof compared with it), not an event time; the entry's expected_projection must equal the row's published projection name (derived from the schema's one PUBLISHED scalar).
3. Per-row side records share the SIM side journal keyed by (feature, version, instrument, timeframe, materialization_version); sequence must strictly increase per key.

Limits: SIM; Composition has no first-class per-row publish method (the route reuses `recover_publication`, which rebuilds the Gateway from the committed side journal); no E05 rebuild over the per-row side records in this route yet; separated-worker route for rows covered by test_r41 only for acceptance. Clears no gate/hold.
