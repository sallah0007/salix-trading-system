# SALIX Type-1 source-class disposition — 2026-09-19

This record narrows the unresolved source classes after a Manager Drive search and physical folder inventory. It does **not** assert that an unlocated historical object never existed.

## POPULATED_TRACKER_REGISTRY

Disposition: **UNRESOLVED / NOT LOCATED AS A POPULATED OBJECT**.

Evidence:
- current Tracker authority contains the frozen architecture/registry specification, not a populated registry dataset;
- the frozen Tracker explicitly states `TRACKER_ARCHITECTURE_COMPLETE != TRACKER_IMPLEMENTED`;
- no separate populated registry artifact was located in the Tracker authority folder or the current identity implementation folder.

Import consequence: no canonical rows may be invented. This source class remains unresolved.

## CANONICAL_FEATURE_DEFINITION_CATALOGUE

Disposition: **UNRESOLVED / NOT LOCATED AS A POPULATED OBJECT**.

Evidence:
- current Tracker/Composer/connected-contract documents define identity, version, lookup and feature-definition requirements;
- no governed populated catalogue containing concrete canonical `FEATURE_ID / FEATURE_VERSION / definition_hash / graph_hash` rows was located;
- existing EURUSD lookup evidence remains `LOOKUP_COMPLETE = FALSE`.

Import consequence: no canonical rows may be invented. This source class remains unresolved.

## HISTORICAL_GOLD_FEATURE_MANIFEST

Disposition: **TERMINALLY NON-IMPORTABLE FOR CURRENT CANONICAL POPULATION / HISTORICAL EVIDENCE LIMITATION**.

Evidence:
- repeated Drive searches and the dedicated ML research-tree physical inventory did not locate a populated governed Gold/XAUUSD manifest/dependency closure;
- prior Manager reconciliation records `GOLD_ACTUAL_POPULATED_ML_MANIFEST_LOCATED = NO`, `GOLD_DEPENDENCY_CLOSURE_LOCATED = NO`, and historical baseline ancestry as unverified;
- the historical Gold gap has already been decoupled from current architecture portability;
- Type-1 importer authority rules now reject historical/example/supporting sources as canonical import authority.

Important: this is **not** `ABSENT`. If the historical artifact is later recovered, it is historical evidence requiring separate reconciliation and does not automatically become a current canonical identity source.

Import consequence: remove `HISTORICAL_GOLD_FEATURE_MANIFEST` from the unresolved *current import-source* classes. Do not import rows from it under current authority.

## Current population state

- importable governed identity rows: 0
- source universe complete: NO
- population complete: NO
- ABSENT proven: NO
- remaining unresolved current import-source classes:
  - POPULATED_TRACKER_REGISTRY
  - CANONICAL_FEATURE_DEFINITION_CATALOGUE

`NOT LOCATED != PROVEN ABSENT`.
`HISTORICAL EVIDENCE != CURRENT CANONICAL IMPORT AUTHORITY`.
`NO_STEP_AUTO_AUTHORIZES_THE_NEXT = TRUE`.
