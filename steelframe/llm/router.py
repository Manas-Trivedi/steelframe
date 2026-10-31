"""Send a stage's request down its list of routes until one works."""
import json
import logging
import re
import time

from .errors import AllRoutesFailed, AuthError, RateLimited, Rejected, Unavailable

log = logging.getLogger("steelframe.llm")
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class Router:
    def __init__(self, providers, routes, quota, sleep=time.sleep, clock=time.time):
        """routes: {stage: [(provider_name, model), ...]} in order of preference."""
        self.providers, self.routes, self.quota = providers, routes, quota
        self.sleep, self.clock = sleep, clock
        self.cooldown = {}  # provider -> time before which it is skipped
        self.disabled = {}  # provider -> reason (bad or missing key), skipped for this process
        self.closed_routes = {}  # (provider, model) -> reason (403 on one model), skipped for this process
        for stage, route in routes.items():
            for provider, model in route:
                providers[provider].check_free(model)  # refuse non-free models at start-up

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096):
        """Return (parsed_json, Result). `validate(obj)` may raise ValueError to reject an answer."""
        route = self.routes.get(stage) or []
        if not route:
            raise AllRoutesFailed(stage, ["no model configured; run list_models and fill config/models.json"])
        reasons = []
        for provider_name, model in route:
            label = f"{provider_name}/{model}"
            if provider_name in self.disabled:
                reasons.append(f"{label}: skipped, {self.disabled[provider_name]}")
                continue
            if (provider_name, model) in self.closed_routes:
                reasons.append(f"{label}: skipped, {self.closed_routes[(provider_name, model)]}")
                continue
            if self.cooldown.get(provider_name, 0) > self.clock():
                reasons.append(f"{label}: skipped, cooling down after a rate limit")
                continue
            if not self.quota.allowed(provider_name):
                reasons.append(f"{label}: skipped, own quota ceiling reached")
                continue
            try:
                result = self._call(provider_name, model, system, user, max_tokens)
                self.quota.record(provider_name, result.tokens_in + result.tokens_out)
                parsed = self._parse(result.text)
                if validate:
                    validate(parsed)
                return parsed, result
            except RateLimited as error:
                self.cooldown[provider_name] = self.clock() + (error.retry_after or 60)
                reasons.append(f"{label}: rate limited")
            except AuthError as error:
                if error.status == 403:
                    self.closed_routes[(provider_name, model)] = f"forbidden for this model: {error}"
                    log.error("route %s closed: %s", label, error)
                else:
                    self.disabled[provider_name] = f"auth problem: {error}"
                    log.error("provider %s disabled: %s", provider_name, error)
                reasons.append(f"{label}: auth problem")
            except Rejected as error:
                reasons.append(f"{label}: rejected, {error}")
            except (Unavailable, ValueError) as error:
                reasons.append(f"{label}: unusable answer or outage, {error}")
        log.error("stage %s failed on every route: %s", stage, reasons)
        raise AllRoutesFailed(stage, reasons)

    def _call(self, provider_name, model, system, user, max_tokens):
        provider = self.providers[provider_name]
        try:
            return provider.complete(model, system, user, True, max_tokens)
        except Unavailable:
            self.sleep(2)  # one retry for a server error or network blip, then move on
            return provider.complete(model, system, user, True, max_tokens)

    @staticmethod
    def _parse(text):
        try:
            return json.loads(FENCE.sub("", text.strip()))
        except ValueError as error:
            raise ValueError(f"answer is not valid JSON: {error}") from error
