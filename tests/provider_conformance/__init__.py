"""SALIX E-01 provider conformance harness — TEST / EVIDENCE TOOLING ONLY.

AUTHORIZATION_CLASS = TEST / EVIDENCE TOOLING ONLY
PRODUCTION_STAGE_A_IMPLEMENTATION_AUTHORITY = NO
CODE_COMMISSION_AUTHORITY = NO
PROVIDER_ACCEPTED = NO
READY_TO_CODE = NO

This package is certification tooling. It emulates the frozen E-01 authority
adapter contract so that a CONFIGURED PROVIDER can be tested against frozen
semantics. It is NOT the commissioned production adapter
(stage_a/coordination/object_store_journal.py), it must never be imported by
Stage A runtime code, and a passing run does not set PROVIDER_ACCEPTED.

Governed basis, read at source by the implementer:
  Manager reconciliation 18aMPP7LmtWMK7SrczDKB_OeYiDlS4whiOdbl9TM9YHg
  Frozen Build Plan      1CVUUPJ4GSOqQiDxZgsFjzu6_R0dKZU9Tn_nEnaBHyRo
    E01-H1  one mutable HEAD per governed authority namespace; journal is authority
    E01-M1  acceptance = successful CAS; pre-CAS transition objects are candidates;
            fresh accepted_at/hash/key per attempt; unknown commit resolves by
            authoritative reread, never blind retry
    E07-M1  an in-memory fake can never prove E-01 provider semantics
    E09     object-store key / epoch namespace layout
    E10-M1  rollback advances the epoch and fences pre-rollback tokens
    §15.1   coordination semantics required of the selected technology
"""
