# SALIX Type-1 canonical identity content import boundary

This branch does not invent or reconstruct feature definitions.

A population run may only import rows supported by an explicit source manifest **and** a separate versioned/hashed source-universe authority.

Key fences:

- MECHANISM_COMPLETE != CANONICAL_CONTENT_POPULATED
- ZERO IMPORTABLE ROWS != PROOF OF ABSENCE
- MANIFEST_DECLARATION != SOURCE_UNIVERSE_PROOF
- HISTORICAL_EXAMPLE != CANONICAL_IMPORT_AUTHORITY
- population_complete may be TRUE only when the external source-universe authority is complete, unresolved source classes are empty, every expected source is enumerated and searched, row counts reconcile by source, imported-row provenance is permitted, and the stale-state sweep passes.

Current SALIX evidence does not prove a complete source universe for the populated Tracker registry / canonical feature-definition catalogue / historical Gold feature manifest. Therefore the current real population state remains incomplete even though zero rows are importable from the presently located documents.
