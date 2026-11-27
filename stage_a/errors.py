"""Fail-closed error types. A Refusal is a normal, typed negative outcome; it never means 'try again unqualified'."""

class StageAError(Exception):
    code = "STAGE_A_ERROR"
    def __init__(self, detail: str = "", code: str = None):
        if code is not None:
            self.code = code
        self.detail = detail
        super().__init__("%s %s" % (self.code, detail))

class Refusal(StageAError):
    code = "REFUSED"

class IntegrityFailure(StageAError):
    code = "INTEGRITY_FAILURE"

class StaleFence(StageAError):
    code = "STALE_FENCE"

class UnknownCommit(StageAError):
    """The store could not say whether a conditional write landed. Never treated as success or as failure."""
    code = "UNKNOWN_COMMIT"
