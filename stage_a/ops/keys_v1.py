"""E-09: the CANDIDATE `stage-a/v1/...` object-store key plan as pure builders. Candidate and NON-NORMATIVE for bytes: it does not replace `storage.keys` (the repository prototype layout differs and legacy data is neither remapped nor deleted; `LEGACY_KEY_FAMILIES` names the old prefixes so a reader can accept both). Rules enforced here:
keys are content/identity addressed and never overwritten; HEAD is the only mutable key and is written only by conditional CAS with an epoch/fence check (`head_cas_allowed`); listing order is never authority (a caller that sorts by key to pick a head is wrong: `sequence_key` zero-pads only for human listing).
RECONCILED with the Build Plan overlays that control E-09 where they conflict (read live, paragraphs 1021-1033 and 1063-1072): R3 E01-H1 - there is NO independently authoritative status/currentness HEAD; one mutable HEAD per coordination namespace is the authority and any status key space is a rebuildable PROJECTION only (so this module has no status HEAD builder; `status_event_projection_key` is projection-only and carries `PROJECTION_ONLY`);
R3 E09-H1 - status and fit namespaces carry INSTRUMENT_ID and TIMEFRAME (equal feature/version/materialization values for different instruments or timeframes can never collide); R3 E09-M1 - ONE final object per binding / resolution identity (`bindings/{id}.bin`, `non-delivery/{id}.bin`, write-if-absent, the final package hash lives inside the object, so two payloads cannot name one identity).
The literal E-09 text (`fits/{feature}/{version}/{gen}/{sha}`, status HEAD, `gateway/bindings/{id}/{hash}`) is superseded and NOT built."""
import re
from ..errors import Refusal
_H = re.compile(r"[0-9a-f]{64}\Z"); _ID = re.compile(r"[A-Za-z0-9_.\-]{1,128}\Z")
LEGACY_KEY_FAMILIES = ("head/", "journal/", "artifact/", "accepted-materialization/", "final-resolution/")
def _h(x): 
    if not isinstance(x, str) or not _H.match(x): raise Refusal(repr(x), code="KEY_HASH_INVALID")
    return x
def _i(x):
    if not isinstance(x, str) or not _ID.match(x) or x in (".", ".."): raise Refusal(repr(x), code="KEY_COMPONENT_INVALID")
    return x
def artifact_key(kind, sha): return "stage-a/v1/artifacts/%s/%s/%s.bin" % (_i(kind), _h(sha)[:2], sha)
def golden_key(set_id, sha): return "stage-a/v1/goldens/%s/%s.bin" % (_i(set_id), _h(sha))
def fit_key(fid, ver, instrument_id, timeframe, gen_or_hash): return "stage-a/v1/fits/%s/%s/%s/%s/%s.bin" % (_i(fid), _i(ver), _i(instrument_id), _i(timeframe), _i(gen_or_hash))
def coordination_head_key(ns): return "stage-a/v1/coordination/%s/HEAD" % _i(ns)
def transition_key(ns, epoch, seq, thash):
    if not (type(epoch) is int and epoch >= 0 and type(seq) is int and seq >= 1): raise Refusal("epoch/seq", code="KEY_EPOCH_SEQUENCE_INVALID")
    return "stage-a/v1/coordination/%s/epochs/%d/transitions/%020d-%s.bin" % (_i(ns), epoch, seq, _h(thash))
def status_event_projection_key(fid, ver, instrument_id, timeframe, mv, seq, ehash):
    """PROJECTION_ONLY key (rebuildable from the accepted journal); it grants no authority, eligibility, currentness, publication or bindability and has no HEAD sibling."""
    if not (type(seq) is int and seq >= 1): raise Refusal("seq", code="KEY_EPOCH_SEQUENCE_INVALID")
    return "stage-a/v1/status/%s/%s/%s/%s/%s/events/%020d-%s.bin" % (_i(fid), _i(ver), _i(instrument_id), _i(timeframe), _i(mv), seq, _h(ehash))
def binding_key(bid): return "stage-a/v1/bindings/%s.bin" % _i(bid)
def non_delivery_key(rid): return "stage-a/v1/non-delivery/%s.bin" % _i(rid)
def health_key(subject_type, subject_id, available_asof_ns, ehash):
    if not (type(available_asof_ns) is int and available_asof_ns >= 0): raise Refusal("asof", code="KEY_TIME_INVALID")
    return "stage-a/v1/health/%s/%s/%d-%s.bin" % (_i(subject_type), _i(subject_id), available_asof_ns, _h(ehash))
def head_cas_allowed(current_epoch: int, writer_epoch: int, current_seq: int, new_seq: int) -> bool:
    """Mutable HEAD may advance only for a writer holding the CURRENT epoch and only by exactly +1 within that epoch; a stale epoch can create no accepted write."""
    return writer_epoch == current_epoch and new_seq == current_seq + 1
