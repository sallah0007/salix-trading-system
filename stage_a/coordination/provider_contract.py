"""E-01 provider adapter contract (Build Plan E-01, closed at software-design level; 'provider must prove adapter contract').
Source: six required adapter methods and five required test classes. Vendor selection is 'deployment configuration, not semantic authority':
NO provider is selected or accepted here. Mapping below is of the repository's ObjectStore protocol onto the six E-01 methods.
Candidate conformance evidence tooling (NOT runtime, NOT acceptance, 'DO NOT MERGE'): branch e01/conformance-harness (PR16, tip cefe69e4f60e7f126dc215de819f0b1b47e24ab7),
15 case specs under tests/provider_conformance/; scoped older S3/RouteA/R4 provider acceptance does not cover the R7 commit-time deadline semantics."""
from ..errors import Refusal

E01_METHOD_TO_STORE = {                                   # E-01 name -> ObjectStore protocol method here
    "read_head": "get", "compare_and_swap_head": "put_if_match", "append_transition_if_absent": "put_if_absent",
    "read_transition": "get", "scan_transitions": "list_prefix", "read_after_write_probe": None}
REQUIRED_CONFORMANCE = ("linearizability", "conditional_write", "rebuild", "stale_fence", "unknown_commit")

def missing_store_methods(store) -> list:
    return sorted(m for m in {v for v in E01_METHOD_TO_STORE.values() if v} if not callable(getattr(store, m, None)))

def read_after_write_probe(store, key: str) -> bool:
    """Single-process probe: create-if-absent then read back the same bytes. It cannot show linearizability across clients/provider;
    a True here is a SIM result only."""
    data = b"probe:" + key.encode()
    store.put_if_absent(key, data)
    got = store.get(key)
    return got is not None and got[0] == data

CLAIMED_FIELDS_ONLY_NOT_AUTHENTICATED = True

def require_provider_proof(evidence: dict) -> None:
    """CLAIMED-FIELD CHECK ONLY. Refuses unless the supplied dict names a provider and claims PASS for every required class. It does NOT
    authenticate the evidence, bind it to a run/commit/provider build, or prove conformance; returning normally is NOT provider acceptance.
    Reachable consumers in this repository: none (grep of stage_a/ and tests/ finds only its own tests). PROVIDER_ACCEPTED stays NO."""
    if not isinstance(evidence, dict) or not evidence.get("provider_id"):
        raise Refusal("provider_id", code="PROVIDER_NOT_NAMED")
    results = evidence.get("results", {})
    for c in REQUIRED_CONFORMANCE:
        if results.get(c) != "PASS":
            raise Refusal(c, code="PROVIDER_CONFORMANCE_NOT_PROVEN")
