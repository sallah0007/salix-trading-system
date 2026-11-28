"""R39: the Registry ENTRY fields the Tracker must carry (ORIGIN, CREATION_REQUEST_ID, CANONICAL_SURVIVOR_ID, TEST_EVIDENCE_REFS, DISPOSITION_HISTORY), modelled WITHOUT a second lifecycle authority (Registry 241):
  * ORIGIN is one of `registry_semantics.ORIGINS`; CREATION_REQUEST_ID is the intake's recorded id (supplied, never minted); CANONICAL_SURVIVOR_ID is None or resolves through `registry_semantics.resolve_survivor_chain` (acyclic, terminating) over the supplied pointer map;
  * TEST_EVIDENCE_REFS are references only (checking them is B19's `evidence_resolver`; a ref here is not evidence);
  * DISPOSITION_HISTORY is NEVER supplied: it is derived read-only from the one `LifecycleFramework` journal (`history(subject)`), so this object cannot hold a disposition the lifecycle journal does not. With an unbound lifecycle policy the history is still readable and the entry carries NO mapped status (mapping to chain-status/currentness is source-owned, HELD).
Not an admission, status or gate. The record byte layout is not source-defined: this is an in-memory typed view, no persisted bytes invented."""
from dataclasses import dataclass
from ..errors import Refusal
from . import registry_semantics as RSM
@dataclass(frozen=True)
class RegistryEntry:
    subject: str; origin: str; creation_request_id: str; canonical_survivor_id: object; test_evidence_refs: tuple; disposition_history: tuple; survivor_chain: tuple
def build_registry_entry(subject, origin, creation_request_id, lifecycle, *, survivor_pointers=None, test_evidence_refs=()):
    if not (isinstance(subject, str) and subject and origin in RSM.ORIGINS and isinstance(creation_request_id, str) and creation_request_id and isinstance(test_evidence_refs, tuple) and all(isinstance(r, str) and r for r in test_evidence_refs) and len(set(test_evidence_refs)) == len(test_evidence_refs)): raise Refusal("entry", code="REGISTRY_ENTRY_INPUT_INVALID")
    if lifecycle is None or not hasattr(lifecycle, "history"): raise Refusal("lifecycle", code="REGISTRY_ENTRY_LIFECYCLE_SOURCE_REQUIRED")
    ptr = dict(survivor_pointers or {}); chain = RSM.resolve_survivor_chain(ptr, subject)
    return RegistryEntry(subject, origin, creation_request_id, ptr.get(subject), test_evidence_refs, lifecycle.history(subject), chain)
