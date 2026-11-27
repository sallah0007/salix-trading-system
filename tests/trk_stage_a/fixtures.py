"""Shared fixtures. Expected values below are HAND-DERIVED by the author from the written opcode spec (see
composer/expression/opcodes.py). They are a self-generated oracle: independent expected-byte review is OPEN."""
import copy
from tracker_identity import LookupOutcome
from tracker_component.order import ConstructionOrder, TrustAnchor
from tracker_component.claims import ClaimService
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.clocks import FixedClock
from stage_a.observability import EventSink
from stage_a.tracker.registry import FeatureJournalSet
from stage_a.tracker.pipeline import TrackerPipeline
from stage_a.tracker.quant_intake_adapter import BuildPackage, admit
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.hashing import manifest_hash, graph_hash, program_hash
from stage_a.composer.expression.evaluator import encode_const

ANCHOR = TrustAnchor(frozenset({"MANAGER"}), "SRC-BINDING-1")

IDENTITY_FIELDS = dict(
    scope="current_active", lifecycle_state="CURRENT", is_current=True, declared_normalization="NONE",
    causal_time_semantics="SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1", completion_semantics="LAST_COMPLETED_BEFORE_T",
    availability_class="RECONSTRUCTED_NOT_OBSERVED", price_basis="BID", data_vintage_mode="CURRENT_RECOMPUTED",
    scope_universe="XAUUSD/ERA_1", parameters={"lookback_bars": 3}, fitted_state="NONE", proxy_status="NOT_PROXY",
    instrument_applicability="INSTRUMENT_SPECIFIC", source_provider="COMPOSER")

def momentum_manifest(feature_id="mom3", version="1", instrument="XAUUSD", timeframe="H4", window=3, fit_refs=None):
    nodes = [{"id": "a", "op": "input", "name": "close"}, {"id": "b", "op": "lag", "args": ["a"], "n": 1},
             {"id": "c", "op": "sub", "args": ["a", "b"]}, {"id": "d", "op": "rolling_mean", "args": ["c"], "n": window}]
    return {"schema": "SALIX_EXPR_MANIFEST_V1", "feature_id": feature_id, "feature_version": version,
            "instrument": instrument, "timeframe": timeframe, "inputs": ["close"], "nodes": nodes, "output": "d",
            "fit_refs": fit_refs or [],
            "declared_opcodes": ["input", "lag", "rolling_mean", "sub"],
            "declared_capabilities": ["ARITH_BINARY64", "INPUT_SERIES", "WINDOW_LAG", "WINDOW_ROLLING"]}

_DEFAULT = object()

def package(manifest=_DEFAULT, *, request_id="REQ-1", attempt_id="ATT-1", order_id="ORD-1", lookup=LookupOutcome.ABSENT,
            quant=True, **over):
    m = momentum_manifest() if manifest is _DEFAULT else manifest
    declared = (None, None, None)
    if m is not None:
        try:
            M = Manifest.from_dict(m)
            declared = (manifest_hash(M), graph_hash(M), program_hash(M))
        except Exception:
            pass
    kw = dict(package_id="PKG-1", attempt_id=attempt_id, request_id=request_id, order_id=order_id,
              expected_instrument=m.get("instrument", "XAUUSD") if isinstance(m, dict) else "XAUUSD",
              expected_timeframe=m.get("timeframe", "H4") if isinstance(m, dict) else "H4",
              quant_feature_requested=quant, manifest=m, declared_manifest_hash=declared[0], declared_graph_hash=declared[1],
              declared_program_hash=declared[2], lookup_outcome=lookup, identity_fields=copy.deepcopy(IDENTITY_FIELDS),
              semantic_definition="3-bar mean of one-bar close change", created_by="SALIX_MANAGER",
              creation_reason_ref="decision:approved-definition", authority_ref="owner:era1-intake",
              creation_evidence_ref="evidence:definition-review", era_id="ERA_1",
              request_record=copy.deepcopy(REQUEST_RECORD))
    kw.update(over)
    return BuildPackage(**kw)

REQUEST_RECORD = {"REQUEST_SCHEMA_VERSION": "1", "REQUESTER_ID": "fixture-requester", "REQUESTER_TYPE": "MANAGER",
                  "REQUEST_CLASS": "GOVERNED_INTAKE_REQUEST", "TARGET_CONSUMER": "FORWARD_WALK",
                  "REQUEST_CONTEXT": "FW_MANIFEST_NEED", "PURPOSE_STATEMENT": "fixture purpose"}

class Rig:
    def __init__(self, store=None, fits=None, baseline=None):
        self.store = store or InMemoryObjectStore()
        self.claims_journal = ObjectStoreJournal(self.store, "claims", "claims-writer")
        self.claims_journal.acquire_epoch()
        self.claims = ClaimService(self.claims_journal, ANCHOR)
        self.journals = FeatureJournalSet(self.store, "tracker-1")
        self.events = EventSink()
        self.fits = fits or {}
        self.pipe = TrackerPipeline(store=self.store, claims=self.claims, journals=self.journals, clock=FixedClock(),
                                    events=self.events, accepted_fit_generations=self.fits, baseline=baseline)

    def issue(self, pkg, issuer="MANAGER", binding="SRC-BINDING-1"):
        adm = admit(pkg, accepted_fit_generations=self.fits)
        assert adm.subject_key, adm.failed
        self.claims.issue_order(ConstructionOrder(pkg.order_id, adm.subject_key, binding, issuer))
        return adm
