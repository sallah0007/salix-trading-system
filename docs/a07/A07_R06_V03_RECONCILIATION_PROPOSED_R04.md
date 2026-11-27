# A07 R06 V03 reconciliation - PROPOSED delta and incorporation/readback prerequisites (R22)

STATUS: PROPOSED by the Coder for Manager review and Sallah's later final sign-off. NOT effective, NOT incorporated, NOT a terminal-issuer appointment, NOT an acceptance of the Coder's own reconciliation.
Sources read read-only from Drive (paraphrased by ID/predicate only; no private governing text is reproduced here):
- `V240_VERSIONED_VALIDITY_RULE_R06_CANDIDATE.json` (Drive 1V5bv2QrbD0U22ExYUbz4FuwHkvXTsCSe, 13,903 bytes; status PROPOSED_NOT_FROZEN_NOT_ADOPTED_NOT_IMPLEMENTED; current evaluation NOT RUN). The Coder confirms by reading, not by recomputation, that its predicate V03 still requires three distinct accountable roles and excludes the candidate author and the author of a relied return from terminal assessment.
- `A07_Owner_Direction_And_Evidence_Addendum_R02` (Drive 1dWldu6G5J1KonK1KWKcoerPR6nBVwfXt): working roles are Claude = production author, Codex = Manager and code reviewer, no third actor required; the independence limitation is explicit; the addendum supersedes the missing-third-actor staffing issue; R06 stays a candidate until incorporation and readback.

## 1. What conflicts (exact, by field)
| R06 element | Conflict with the Owner direction |
|---|---|
| V03 (three distinct accountable roles; assessor is neither candidate author nor relied-return author) | Requires a third actor the Owner has stated does not exist. |
| body field `independent_return_ref` ("its author differs from the terminal assessor") | Presumes an independent returner distinct from the assessor. |
| body field `issuer_eligibility_ref` (independence record) | Must record the explicit independence LIMITATION, not claim independence. |
| decision order step `single_actor_terminal_assessment` | The identity/role of the single terminal assessor/writer is not decided by the direction. |
| V13 ("eligibility and transitive closure") | Inherits V03's role assumption. |

## 2. Proposed reconciliation (delta only; ready for review)
1. V03 -> state the recorded working roles (author, Manager/code reviewer, Sallah final sign-off) and require an explicit INDEPENDENCE-LIMITATION record: Manager reconciliations are prepared by the Manager role and are therefore not third-party independent acceptance.
2. `independent_return_ref` -> rename the intent to "relied review return ref" (exact ID, revision, hash) and drop the author-differs-from-assessor requirement; keep the exact-identity binding and the rule that a return never self-certifies its own reconciliation.
3. `issuer_eligibility_ref` -> binds the protected identity/authority record plus the independence-limitation record from item 1.
4. Terminal assessor/writer identity: LEFT TO SALLAH/SOURCE OWNER. This proposal does not appoint a terminal issuer and does not grant independent acceptance of the Coder's reconciliations.
5. Unchanged and still binding: V01, V02, V04, V05-V12, V13 (after item 1 wording), V14, V15; `strict_default_until_authorized` and the legacy pre-effectiveness posture (V12/V13 mutually exclusive).
Consequence of NOT reconciling: V03 cannot be satisfied by any evidence that exists, so the R06 predicate conjunction can never pass; A07 stays OPEN by construction rather than by missing work.

## 3. Incorporation and readback prerequisites (exact inputs; owner = Manager/Drive custodian under Sallah)
- The entire post-incorporation Governance object (ID, revision, hash) - V09 forbids substituting a retained-body hash.
- Exact rule ID/version/revision/hash after the V03 delta, the attestation body schema and closed schema, the checklist, and the eleven bound rule dependencies (NI-3, event/object class table, provider-event mapping, container/content policy, placement/archive admission, archive classification, pointer profile, canonical body profile, attestation closed schema, attestation body schema R06, attempt lifecycle) - each by its stated path and SHA256 in the R06 file.
- Exact byte readback of the incorporated text and a fresh-reader predicate result (decision-order steps 2 and 9). Nothing here claims that happened.
- Accepted S (whole-domain D definition, coverage, horizon), the 41-unit/100-qualifier dispositions, the four programme obligations, and the actual currentness evidence (V02, V10, V13).

## 4. History/visibility (V10) - bounded capability limitation, not a waiver
The Drive connector available to the Coder exposes file metadata, revisions and permissions but no Drive Activity / change-feed query. This is a limit of THIS tool surface, not provider-wide impossibility, and it waives nothing. Ready-to-review recommendation for Sallah: the Drive owner/admin exports the Drive Activity (or Workspace audit) log for the governed domain D over the requested interval and supplies it read-only to the Manager; V10 then evaluates it. No bounded-history waiver is proposed or assumed.

## 5. Concrete record inconsistencies noted by the Manager addendum (for the 41/100 reconciliation; none awarded here)
NL-0187 (comparison text describes shadow counters while its oracle concerns display visibility: bounded record repair), NL-0186 (immutable prospective record does not by itself prove no reader observes a partial record; consumer-side partial-observation exclusion is a Tracker-side residual, see closeout NL0186), NL-0223 (current trust with freshness evidence is distinct from mandatory append-only annotation), NL-0143/0167 and NL-0162, NL-0174/0187 (field-mandate and compatibility-exception scope questions). Source-owned 35 cited qualifier rows are not awarded by lexical similarity. Rescue stays visible. Normal independently reviewed HTML archive/pointer process applies only when applicable and is not triggered by this repository note.
