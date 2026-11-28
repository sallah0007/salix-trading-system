"""R38 B20: research ATTEMPT / MULTIPLICITY / BATTERY lineage ledger (Registry: attempt identity is OUTSIDE the version-content diff - `version_relationship.OUTSIDE_VERSION_CONTENT_DIFF`; accepted records carry a recorded `attempt_id` that this ledger can be asked to resolve).
An append-only, chain-verified JOURNAL ledger (candidate record kinds; no normative bytes): BATTERY_REGISTERED(family, battery), ATTEMPT(attempt_id, family, battery, input_ref/hash, params_hash, outcome ref+status, parents), SELECTION(family, battery, selected attempt, declared_n).
What it DERIVES (never trusts a supplied count): the number of attempts per (family, battery) and per family INCLUDING rejected/failed ones, so the selection multiplicity cannot be under-reported; a SELECTION whose declared_n differs from the ledger count at that point is REFUSED; an attempt for an unregistered battery, an unknown parent, a duplicate attempt id with different content, or an unknown status is REFUSED (rejected work is recorded, never silently dropped).
NOT defined here (source-owned, HELD): any multiple-testing correction, threshold, significance rule or what a battery MEANS. `multiplicity_facts` returns counts only; no pass/fail inference. Clears no gate."""
import json
from ..errors import Refusal
from tracker_component.journal_port import GENESIS_HEAD
BAT, ATT, SEL = "BATTERY_REGISTERED", "ATTEMPT", "SELECTION"
STATUSES = ("COMPLETED", "FAILED", "REJECTED", "ABANDONED")             # rejected/failed work stays in the count
def _s(x): return isinstance(x, str) and bool(x)
class ResearchLineage:
    def __init__(self, journal): self._j = journal
    def _state(self):
        bats, atts, sels = set(), {}, []
        head = self._j.head()
        for r in (self._j.read_from(1) if head != GENESIS_HEAD else []):
            b = json.loads(r.body_json)
            if r.kind == BAT: bats.add((b["family"], b["battery"]))
            elif r.kind == ATT: atts[b["attempt_id"]] = b
            elif r.kind == SEL: sels.append(b)
            else: raise Refusal(r.kind, code="LINEAGE_UNKNOWN_RECORD_KIND")
        return bats, atts, sels
    def register_battery(self, family, battery):
        if not (_s(family) and _s(battery)): raise Refusal("battery", code="LINEAGE_INPUT_INVALID")
        if (family, battery) in self._state()[0]: return None
        return self._j.append(self._j.head(), BAT, {"family": family, "battery": battery})
    def record_attempt(self, attempt_id, family, battery, input_ref, input_hash, params_hash, status, outcome_ref, parents=()):
        if not all(_s(x) for x in (attempt_id, family, battery, input_ref, input_hash, params_hash, outcome_ref)) or status not in STATUSES or not isinstance(parents, tuple) or not all(_s(p) for p in parents): raise Refusal("attempt", code="LINEAGE_INPUT_INVALID")
        bats, atts, _ = self._state(); body = {"attempt_id": attempt_id, "family": family, "battery": battery, "input_ref": input_ref, "input_hash": input_hash, "params_hash": params_hash, "status": status, "outcome_ref": outcome_ref, "parents": list(parents)}
        if (family, battery) not in bats: raise Refusal("%s/%s" % (family, battery), code="LINEAGE_BATTERY_UNREGISTERED")
        if attempt_id in atts:
            if atts[attempt_id] != body: raise Refusal(attempt_id, code="LINEAGE_ATTEMPT_ID_REUSED_DIFFERENTLY")
            return None                                                    # identical retry: idempotent, NOT a second attempt (the count does not move)
        if any(p not in atts for p in parents): raise Refusal(attempt_id, code="LINEAGE_UNKNOWN_PARENT")
        if parents and any(atts[p]["family"] != family for p in parents): raise Refusal(attempt_id, code="LINEAGE_PARENT_OTHER_FAMILY")
        return self._j.append(self._j.head(), ATT, body)
    def multiplicity_facts(self, family, battery=None) -> dict:
        _, atts, sels = self._state(); a = [x for x in atts.values() if x["family"] == family and (battery is None or x["battery"] == battery)]
        by = {}
        for x in a: by[x["status"]] = by.get(x["status"], 0) + 1
        return {"family": family, "battery": battery, "attempts": len(a), "by_status": dict(sorted(by.items())), "selections": sum(1 for s in sels if s["family"] == family and (battery is None or s["battery"] == battery)), "inference": "NONE_COUNTS_ONLY"}
    def record_selection(self, family, battery, attempt_id, declared_n):
        bats, atts, _ = self._state(); truth = self.multiplicity_facts(family, battery)["attempts"]
        if attempt_id not in atts or atts[attempt_id]["family"] != family or atts[attempt_id]["battery"] != battery: raise Refusal(str(attempt_id), code="LINEAGE_SELECTED_ATTEMPT_NOT_IN_FAMILY_BATTERY")
        if type(declared_n) is not int or declared_n != truth: raise Refusal("declared %r ledger %d" % (declared_n, truth), code="LINEAGE_MULTIPLICITY_UNDERREPORTED_OR_WRONG")
        if atts[attempt_id]["status"] != "COMPLETED": raise Refusal(attempt_id, code="LINEAGE_SELECTED_ATTEMPT_NOT_COMPLETED")
        return self._j.append(self._j.head(), SEL, {"family": family, "battery": battery, "attempt_id": attempt_id, "declared_n": declared_n})
    def resolves(self, attempt_id) -> bool:
        """For the recorded `attempt_id` an accepted record carries: True only if the ledger holds that attempt (a recorded reference, now resolved)."""
        return attempt_id in self._state()[1]
