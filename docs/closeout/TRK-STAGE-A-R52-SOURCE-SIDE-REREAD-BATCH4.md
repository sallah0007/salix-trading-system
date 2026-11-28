# R52 source-side reread — batch 4 (S4 registry paragraphs 483–550, read in full)

DERIVATION_CLASS = INDEPENDENTLY_DERIVED (reading) / INSUFFICIENT_EVIDENCE where stated. EXACT_INPUTS = /tmp capture `registry_paras.txt` lines 483–550 (paragraph = line number), repo main 7eb4b87. METHOD = read each paragraph complete; grep repo for the named object; no closure claimed from grep. REPRODUCIBLE_BY_MANAGER = YES. Source text is not copied (cited by paragraph number).

| Para | Duty (own words) | Repo evidence (own grep, main 7eb4b87) | Status |
|---|---|---|---|
| 483–509 | The later blueprint must make the frozen architecture explicit across ~23 named areas; architecture freeze must not be read as authorization. | This is a requirements list for a blueprint, not a runtime clause. Candidate modules exist for most areas (core, schema, snapshot, feature registry, gateway, health/blast_radius, coordination/recovery, security/principals, composer, ops). No area is claimed closed from module presence. | MAPPING ONLY. No claim. |
| 509 | Blueprint must not infer authorization from freeze. | Consistent with CLAUDE.md §1/§2A: merge/test/delegation clear no gate. | HELD-by-design |
| 512–514 | Provenance audit "PASS WITH CORRECTION"; 70/70 oracle mapping bound to two named JSON artifacts with stated SHA-256 values. | The two JSON files are not in the repo and I have not opened them this session. Hashes not recomputed. | INSUFFICIENT_EVIDENCE (needs the two artifacts from Drive; source-owner ROLE: Manager). |
| 518 (AF-2) | L2 required + L2 unavailable means recording health UNKNOWN / not healthy, never silent L1 fallback. | `tracker_core.py:494` refuses on health != HEALTHY; the stored-source L2 failure test (test_r53_real_assembly_base, causal version) exercises refusal to FW and exclusion from ML. The literal tokens L2_REQUIRED/L2_UNAVAILABLE do not occur in stage_a (grep), so correspondence is by behaviour, not by name. | IMPLEMENTED (behavioural), name mapping is an open reviewer check. |
| 519 (AF-3) | Half-open fence is architecture-level; no per-source contract may make equality inclusive. | `observation_snapshot.py:19` excludes avail >= fence. Whether any registry/source-contract field could override it: no such field exists (no source-contract registry object — see p398 open finding). | IMPLEMENTED at snapshot; override-attempt negative not separately counted here. |
| 520 (AF-4) | Disambiguate Manager governance role vs Manager AI; enumerate non-authority housekeeping with mutation exclusions. | Not examined this batch. | NOT READ AGAINST CODE (open). |
| 521 (AF-5) | FW_INPUT_BINDING_RECORD is an append-only bind event referencing the response-package hash and the FW feature-view-manifest hash; no content redefinition. | The literal name does not occur in stage_a or tests. `gateway/binding.py` builds delivered entries and verifies hashes, which is a related but different object. | NOT IMPLEMENTED under this name; candidate record needs the owner-defined field list (exact irreducible input: record schema, role: Manager/Owner). Not invented. |
| 523 (AF-7) | Event/Context reaches consumers through the Consumer Gateway as ordinary governed input; no store/resolver bypass. | Store has no resolver/Gateway caller (wiring review in closeout §28.10). | UNBUILT callpath; port unbound. |
| 524–545 | Status block: freeze reopen NO; amendment freeze YES (540) although 528 says NO until Owner decides (later state wins by the document's own date ordering, but I cannot confirm ordering from the text alone); IMPLEMENTATION AUTHORIZATION NO; PRODUCTION/FW/ML/ENGINE NO. | Repo work proceeds under CLAUDE.md §2A owner delegation, which is a standing Owner instruction, not a registry status change. | GOVERNANCE TENSION recorded for Manager: p541 "IMPLEMENTATION AUTHORIZATION = NO" vs §2A delegation. Coder does not resolve it; nothing here is cited as authority to clear any gate. |
| 546–550 | Historical provenance: V1.9 is the frozen-core history; AI plan §27 is the current provenance for the Feature Agent/Manager AI interface; §28 is rough and non-authorizing; ADD-1..4 stay attributed to the 2026-09-15 reconciliation. | Documentation attribution rule; no code. | NA to code. Attribution preserved in this batch. |

## Seven-lens declaration
MATHEMATICAL=NA (no arithmetic claim); DATA_SCIENCE=NA (no sample claim); SOFTWARE_ARCHITECTURE=YES; ADVERSARIAL=YES (override-path check on half-open fence: none found); TRADING_MICROSTRUCTURE=NA (no market claim); GOVERNANCE=YES (p541 tension, p512–514 unverifiable hashes); FALSIFICATION=YES (name-absence checked by grep, not treated as absence of behaviour).

## Open items from this batch
1. p521 FW_INPUT_BINDING_RECORD: needs owner-defined schema.
2. p512–514 provenance artifact hashes: need Drive artifacts opened by someone with read access to the bytes.
3. p520 AF-4 not yet compared to code.
4. p541 vs §2A: Manager to record the reading.
