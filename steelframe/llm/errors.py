class LLMError(Exception):
    """Base class for every model-call failure."""


class RateLimited(LLMError):
    """HTTP 429. The provider's free quota is used up for now."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class Unavailable(LLMError):
    """5xx, network failure, or a reply that is not valid JSON. A retry may work."""


class Rejected(LLMError):
    """4xx other than 429. The same request will fail again, so it is never retried."""


class AuthError(Rejected):
    """401, 403, or a missing key. Needs a human, so it is reported loudly."""


class NotFree(LLMError):
    """A route points at a model that is not on a free tier. Refused at start-up."""


class AllRoutesFailed(LLMError):
    """Every route for a stage failed. `reasons` lists why, one line per route."""

    def __init__(self, stage, reasons):
        super().__init__(f"all routes failed for '{stage}': " + "; ".join(reasons))
        self.reasons = reasons
