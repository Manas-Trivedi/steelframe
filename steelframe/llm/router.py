"""Send a stage's request down its list of routes until one works."""
import json
import logging
import re
import time

from .errors import AllRoutesFailed, AuthError, RateLimited, Rejected, Unavailable

log = logging.getLogger("steelframe.llm")
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class Router:
    def __init__(self, providers, routes, quota, sleep=time.sleep, clock=time.time, max_wait=90):
        """routes: {stage: [(provider_name, model), ...]} in order of preference."""
        self.providers, self.routes, self.quota = providers, routes, quota
        self.sleep, self.clock, self.max_wait = sleep, clock, max_wait
        self.calls = 0  # model calls made through this router, successful or not, for per-issue counts
        self.cooldown = {}  # provider -> time before which it is skipped
        self.disabled = {}  # provider -> reason (bad or missing key), skipped for this process
        self.closed_routes = {}  # (provider, model) -> reason (403 on one model), skipped for this process
        for stage, route in routes.items():
            for provider, model in route:
                providers[provider].check_free(model)  # refuse non-free models at start-up

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096, exclude=()):
        """Return (parsed_json, Result). `validate(obj)` may raise ValueError to reject an answer.

        `exclude` names providers to skip, so a checker never runs on the provider that wrote the draft.
        If every route failed only because of rate limits and the shortest wait is within `max_wait`
        seconds, wait once and go round again, so a busy minute does not fail the stage.
        """
        route = [r for r in self.routes.get(stage) or [] if r[0] not in exclude]
        if not route:
            raise AllRoutesFailed(stage, ["no model configured; run list_models and fill config/models.json"])
        for attempt in range(2):
            result, reasons, wait = self._go_round(route, system, user, validate, max_tokens)
            if result is not None:
                return result
            if attempt == 0 and wait is not None and wait <= self.max_wait:
                log.warning("stage %s: every route is busy, waiting %.0fs", stage, wait)
                self.sleep(wait + 1)
                continue
            break
        log.error("stage %s failed on every route: %s", stage, reasons)
        raise AllRoutesFailed(stage, reasons)

    def _go_round(self, route, system, user, validate, max_tokens):
        """One pass over the routes. Returns (result_or_None, reasons, wait_or_None).

        wait is set only when no route gave a real failure and at least one is cooling down.
        """
        reasons, hard_failure, waits = [], False, []
        for provider_name, model in route:
            label = f"{provider_name}/{model}"
            if provider_name in self.disabled:
                reasons.append(f"{label}: skipped, {self.disabled[provider_name]}")
                hard_failure = True
                continue
            if (provider_name, model) in self.closed_routes:
                reasons.append(f"{label}: skipped, {self.closed_routes[(provider_name, model)]}")
                hard_failure = True
                continue
            remaining = self.cooldown.get(provider_name, 0) - self.clock()
            if remaining > 0:
                reasons.append(f"{label}: skipped, cooling down after a rate limit")
                waits.append(remaining)
                continue
            if not self.quota.allowed(provider_name):
                reasons.append(f"{label}: skipped, own quota ceiling reached")
                hard_failure = True  # the minute window may clear, but a daily ceiling will not: do not wait
                continue
            try:
                result = self._call(provider_name, model, system, user, max_tokens)
                self.quota.record(provider_name, result.tokens_in + result.tokens_out)
                parsed = self._parse(result.text)
                if validate:
                    validate(parsed)
                return (parsed, result), reasons, None
            except RateLimited as error:
                delay = error.retry_after or 60
                self.cooldown[provider_name] = self.clock() + delay
                reasons.append(f"{label}: rate limited")
                waits.append(delay)
            except AuthError as error:
                if error.status == 403:
                    self.closed_routes[(provider_name, model)] = f"forbidden for this model: {error}"
                    log.error("route %s closed: %s", label, error)
                else:
                    self.disabled[provider_name] = f"auth problem: {error}"
                    log.error("provider %s disabled: %s", provider_name, error)
                reasons.append(f"{label}: auth problem")
                hard_failure = True
            except Rejected as error:
                reasons.append(f"{label}: rejected, {error}")
                hard_failure = True
            except (Unavailable, ValueError) as error:
                reasons.append(f"{label}: unusable answer or outage, {error}")
                hard_failure = True
        return None, reasons, (min(waits) if waits and not hard_failure else None)

    def _call(self, provider_name, model, system, user, max_tokens):
        provider = self.providers[provider_name]
        self.calls += 1
        try:
            return provider.complete(model, system, user, True, max_tokens)
        except Unavailable:
            self.sleep(2)  # one retry for a server error or network blip, then move on
            self.calls += 1
            return provider.complete(model, system, user, True, max_tokens)

    @staticmethod
    def _parse(text):
        try:
            return json.loads(FENCE.sub("", text.strip()))
        except ValueError as error:
            raise ValueError(f"answer is not valid JSON: {error}") from error
