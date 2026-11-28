"""R53: separated per-ROW verifier and acceptor handlers (run INSIDE `worker_child` processes by the ProcessSupervisor). CANDIDATE, SIMULATION; reference-only IPC: a job carries ("row", row_content_hash) [+ ("verification", result_hash)].
The governed profile pieces (schema + registry, reference program, codec, input resolver and symbol map, code tables, time port, commit-point port, optional invariant resolver) are NOT defined by any source read: they are a SUPPLIED port named by the
environment variable SALIX_ROW_PROFILE = "module:callable" (the callable returns a dict of ports). Absent => the job refuses ROW_PROFILE_HELD; nothing is defaulted. Shared state is the ONE directory SALIX_SEP_ROOT (labelled TEST adapter, SimulationStore).
  row_verify  ("row", h)                    : re-load the committed row (bytes + producer/independent hash) and its predecessor, run the real independent `verify_row_step`; ONLY a PASS writes sep/row-verification/<result_hash> (+ link sep/row-ver-by-row/<h>); anything else raises.
  row_accept  ("row", h) ("verification", rh): re-load, require the verifier handler's link for this row, then RE-DERIVE the result in THIS process (cross-process agreement: its hash must equal rh) and call the real epoch-fenced `RowAcceptor.accept` with that genuinely issued result.
The in-process verifier receipt is a label, not a security boundary; the cross-process equality of two independent runs is the evidence here, not the receipt. Clears no gate/hold; no profile/program instance is appointed."""
import importlib, json, os
from ..errors import Refusal, IntegrityFailure
from ..storage.byte_primitives import canonical_bytes
from ..storage.authority_class import SimulationStore
from ..storage.file_object_store import FileObjectStore
from ..schema.encoding import Ref
from ..schema import independent as X
from ..tracker import row_acceptance as RA
from ..tracker.registry import FeatureJournalSet
from ..tracker.materialization import row_store as RS
from ..tracker.verification.row_step_verifier import verify_row_step, SCOPE_ROW_STEP
from ..tracker.verification.verification_result import PASS
from .separated_handlers import _store, _ref, _get, _put_once

def _profile():
    spec = os.environ.get("SALIX_ROW_PROFILE")
    if not spec or ":" not in spec: raise Refusal("SALIX_ROW_PROFILE", code="ROW_PROFILE_HELD")
    mod, _, fn = spec.partition(":"); p = getattr(importlib.import_module(mod), fn)()
    need = ("tables", "schema", "schema_registry", "reference_step", "decode", "encode", "resolve_inputs", "input_symbols", "time_port", "commit_point_port")
    if not isinstance(p, dict) or any(k not in p for k in need): raise Refusal(spec, code="ROW_PROFILE_INCOMPLETE")
    return p
def _verify(store, rows, p, h):
    row = rows.load(h); pred = None if row.predecessor_row_hash is None else rows.load(row.predecessor_row_hash.hex())
    return verify_row_step(row=row, predecessor=pred, schema=p["schema"], reference_step=p["reference_step"], decode=p["decode"], encode=p["encode"], resolve_inputs=p["resolve_inputs"], input_symbols=p["input_symbols"],
                           recompute_row_hash=lambda r: X.row_hash(RS.independent_dict(p["tables"], r), p["tables"].enums).hex(), expect_row_hash=h, schema_registry=p["schema_registry"], invariant_resolver=p.get("invariant_resolver"))
def row_verify(job):
    store = _store(); p = _profile(); h = _ref(job, "row"); rows = RS.PendingRowStore(store, p["tables"]); res = _verify(store, rows, p, h)
    if res.status != PASS or res.scope != SCOPE_ROW_STEP: raise Refusal(",".join(res.reasons), code="SEP_ROW_VERIFICATION_NOT_PASS")
    _put_once(store, "sep/row-verification/" + res.result_hash, canonical_bytes({"result_hash": res.result_hash, "row": h, "status": res.status, "scope": res.scope})); _put_once(store, "sep/row-ver-by-row/" + h, res.result_hash.encode())
def row_accept(job):
    store = _store(); p = _profile(); h = _ref(job, "row"); rh = _ref(job, "verification"); rows = RS.PendingRowStore(store, p["tables"])
    link = store.get("sep/row-ver-by-row/" + h)
    if link is None or link[0].decode() != rh: raise Refusal(h, code="SEP_ROW_ACCEPT_RECEIPT_NOT_LINKED_BY_VERIFIER_HANDLER")
    rec = json.loads(_get(store, "sep/row-verification/" + rh, "SEP_ROW_VERIFICATION_ABSENT"))
    if rec.get("row") != h or rec.get("result_hash") != rh or rec.get("status") != PASS: raise Refusal(h, code="SEP_ROW_ACCEPT_RECEIPT_DIFFERS")
    res = _verify(store, rows, p, h)                                                                                         # independent re-derivation in THIS process
    if res.result_hash != rh or res.status != PASS: raise Refusal(h, code="SEP_ROW_ACCEPT_RESULT_NOT_REDERIVED")
    ev = Ref("VERIFICATION_EVIDENCE_REF", b"row-step", b"v1", bytes.fromhex(rh))
    RA.RowAcceptor(FeatureJournalSet(store, "row-acceptor-1"), rows, p["tables"], p["time_port"], p["commit_point_port"]).accept(h, verification_result=res, verification_evidence_ref=ev, currentness_state="CURRENT", status_event="PUBLISHABLE")
    from .separated_handlers import _crash_after_effect; _crash_after_effect(job)
