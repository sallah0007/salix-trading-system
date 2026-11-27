"""Resolver for the baseline's single designated construction-authority seam
(tracker_identity.store._governed_construction_authority(verified)).

This module BUILDS the resolver. It does NOT install it: the baseline function stays hard-False in production, and
installing a resolver is a governance decision (open decision D1 in the PR) that only the Manager/Owner can record.
The resolver is fail-closed: True only when the freshly synced claims journal holds a BOUND claim for exactly the
baseline-derived content key and request id under a still-valid, anchored, unrevoked, unexpired order."""

def make_construction_authority_resolver(claim_service):
    def resolver(verified):
        try:
            key = verified["content_key_composite"]
            rid = verified["request_id"]
        except Exception:
            return False
        return claim_service.authorizes(key, rid) is True
    return resolver
