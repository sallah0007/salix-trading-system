# Current Type-1 identity population package

This directory is the reproducible population input for the currently located SALIX identity evidence.

Current result:

- importable governed identity rows: **0**
- externally governed source universe complete: **NO**
- population complete: **NO**
- absence proven: **NO**

The source manifest no longer certifies its own coverage. It is reconciled against `current_source_universe.json`, which binds the current Drive census as a separate versioned/hashed source-universe authority.

The package is intentionally empty because no concrete governed FEATURE_ID/FEATURE_VERSION rows with sufficient identity fields were located in the current authority corpus.

Three source classes remain unresolved:

- populated Tracker registry
- canonical feature-definition catalogue
- historical Gold feature manifest

Therefore zero rows cannot become ABSENT / DEFINITION_REQUIRED evidence.

Any future imported identity row must preserve its import source ID and source authority class. Rows from historical, superseded, draft, example, supporting-contract, or otherwise non-permitted authority classes fail closed before store mutation.
