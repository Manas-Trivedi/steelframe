import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from steelframe.llm.errors import AllRoutesFailed, AuthError, NotFree, RateLimited, Rejected, Unavailable
from steelframe.llm.providers import Gemini, OpenAICompatible
from steelframe.llm.quota import Quota
from steelframe.llm.router import Router


def http_error(code, headers=None):
    return urllib.error.HTTPError("https://x.test", code, "m", headers or {}, io.BytesIO(b"detail"))


class FakeOpener:
    """Replays results in order: dicts become JSON replies, exceptions are raised. Records requests."""

    def __init__(self, *results):
        self.results, self.requests = list(results), []

    def __call__(self, request, timeout):
        self.requests.append(request)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        body = result if isinstance(result, bytes) else json.dumps(result).encode()
        return io.BytesIO(body)


OPENAI_OK = {"choices": [{"message": {"content": '{"a": 1}'}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
GEMINI_OK = {"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}],
             "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"K": "secret"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_openai_format_and_usage(self):
        opener = FakeOpener(OPENAI_OK)
        result = OpenAICompatible("groq", "https://g.test/v1", "K", opener).complete("m", "sys", "user")
        self.assertEqual((result.text, result.tokens_in, result.tokens_out), ('{"a": 1}', 10, 5))
        request = opener.requests[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(json.loads(request.data)["response_format"], {"type": "json_object"})

    def test_gemini_format_and_usage(self):
        opener = FakeOpener(GEMINI_OK)
        result = Gemini("gemini", "https://g.test/v1beta", "K", opener).complete("gem-1", "sys", "user")
        self.assertEqual(result.tokens_out, 5)
        self.assertEqual(opener.requests[0].get_header("X-goog-api-key"), "secret")
        self.assertIn("gem-1:generateContent", opener.requests[0].full_url)

    def test_gemini_blocked_and_empty_answers_are_rejected(self):
        for reply in ({"promptFeedback": {"blockReason": "SAFETY"}}, {"candidates": [{"finishReason": "SAFETY"}]}):
            with self.assertRaises(Rejected):
                Gemini("gemini", "https://g.test", "K", FakeOpener(reply)).complete("m", "s", "u")

    def test_missing_key_is_auth_error(self):
        with mock.patch.dict(os.environ, {"K": ""}):
            with self.assertRaises(AuthError):
                OpenAICompatible("groq", "https://g.test", "K", FakeOpener()).complete("m", "s", "u")

    def test_http_failures_are_sorted(self):
        cases = [(http_error(429, {"Retry-After": "7"}), RateLimited), (http_error(401), AuthError),
                 (http_error(403), AuthError), (http_error(400), Rejected), (http_error(503), Unavailable),
                 (urllib.error.URLError("dns"), Unavailable), (b"<html>not json</html>", Unavailable),
                 ({"unexpected": 1}, Unavailable)]
        for failure, expected in cases:
            with self.assertRaises(expected, msg=repr(failure)):
                OpenAICompatible("groq", "https://g.test", "K", FakeOpener(failure)).complete("m", "s", "u")

    def test_retry_after_is_read(self):
        with self.assertRaises(RateLimited) as caught:
            OpenAICompatible("groq", "https://g.test", "K", FakeOpener(http_error(429, {"Retry-After": "7"}))).complete("m", "s", "u")
        self.assertEqual(caught.exception.retry_after, 7.0)


class Stub:
    """A provider that replays results."""

    def __init__(self, name, *results):
        self.name, self.results, self.calls = name, list(results), 0

    def check_free(self, model):
        pass

    def complete(self, model, system, user, json_mode, max_tokens):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def ok(provider, text='{"a": 1}'):
    from steelframe.llm.providers import Result
    return Result(text, 10, 5, provider, "m")


class RouterTests(unittest.TestCase):
    def make(self, stubs, limits=None):
        providers = {s.name: s for s in stubs}
        route = [(s.name, "m") for s in stubs]
        self.now = [1000.0]
        self.quota = Quota(":memory:", limits or {}, clock=lambda: self.now[0])
        return Router(providers, {"triage": route}, self.quota, sleep=lambda s: None, clock=lambda: self.now[0])

    def test_rate_limited_falls_through_to_next_provider(self):
        a, b = Stub("a", RateLimited("429")), Stub("b", ok("b"))
        parsed, result = self.make([a, b]).complete_json("triage", "s", "u")
        self.assertEqual((parsed, result.provider), ({"a": 1}, "b"))

    def test_rate_limited_provider_cools_down(self):
        a, b = Stub("a", RateLimited("429", 30)), Stub("b", ok("b"), ok("b"))
        router = self.make([a, b])
        router.complete_json("triage", "s", "u")
        router.complete_json("triage", "s", "u")
        self.assertEqual(a.calls, 1)  # not asked again while cooling down
        self.now[0] += 31
        a.results.append(ok("a"))
        router.complete_json("triage", "s", "u")
        self.assertEqual(a.calls, 2)

    def test_server_error_is_retried_once_then_next_provider(self):
        a, b = Stub("a", Unavailable("503"), Unavailable("503")), Stub("b", ok("b"))
        self.make([a, b]).complete_json("triage", "s", "u")
        self.assertEqual((a.calls, b.calls), (2, 1))

    def test_server_error_then_success_stays_on_provider(self):
        a, b = Stub("a", Unavailable("503"), ok("a")), Stub("b")
        _, result = self.make([a, b]).complete_json("triage", "s", "u")
        self.assertEqual((result.provider, b.calls), ("a", 0))

    def test_rejected_is_not_retried(self):
        a, b = Stub("a", Rejected("400")), Stub("b", ok("b"))
        self.make([a, b]).complete_json("triage", "s", "u")
        self.assertEqual(a.calls, 1)

    def test_403_on_one_model_closes_only_that_route(self):
        class Two(Stub):
            def complete(self, model, *args):
                self.calls += 1
                if model == "bad":
                    raise AuthError("403 needs agent harness", 403)
                return ok(self.name)
        two = Two("a")
        router = Router({"a": two}, {"s": [("a", "bad"), ("a", "good")]},
                        Quota(":memory:", {}), sleep=lambda s: None)
        _, result = router.complete_json("s", "s", "u")
        router.complete_json("s", "s", "u")
        self.assertEqual(result.model, "m")
        self.assertEqual(two.calls, 3)  # "bad" asked once, "good" asked twice

    def test_auth_error_disables_provider_for_the_process(self):
        a, b = Stub("a", AuthError("401")), Stub("b", ok("b"), ok("b"))
        router = self.make([a, b])
        router.complete_json("triage", "s", "u")
        router.complete_json("triage", "s", "u")
        self.assertEqual(a.calls, 1)

    def test_bad_json_and_failed_validation_fall_through(self):
        a = Stub("a", ok("a", "not json at all"))
        b = Stub("b", ok("b", '{"wrong": true}'))
        c = Stub("c", ok("c", '```json\n{"a": 1}\n```'))

        def validate(obj):
            if "a" not in obj:
                raise ValueError("missing key a")
        parsed, result = self.make([a, b, c]).complete_json("triage", "s", "u", validate=validate)
        self.assertEqual((parsed, result.provider), ({"a": 1}, "c"))

    def test_quota_ceiling_skips_provider(self):
        a, b = Stub("a", ok("a"), ok("a")), Stub("b", ok("b"))
        router = self.make([a, b], limits={"a": {"rpd": 1}})
        router.complete_json("triage", "s", "u")
        _, result = router.complete_json("triage", "s", "u")
        self.assertEqual(result.provider, "b")

    def test_all_failing_raises_with_reasons(self):
        a, b = Stub("a", RateLimited("429")), Stub("b", Rejected("400"))
        with self.assertRaises(AllRoutesFailed) as caught:
            self.make([a, b]).complete_json("triage", "s", "u")
        self.assertEqual(len(caught.exception.reasons), 2)

    def test_stage_with_no_models_fails_loudly(self):
        router = self.make([Stub("a")])
        with self.assertRaises(AllRoutesFailed):
            router.complete_json("writer", "s", "u")

    def test_openrouter_model_without_free_suffix_is_refused_at_start(self):
        provider = OpenAICompatible("openrouter", "https://o.test", "K", FakeOpener())
        with self.assertRaises(NotFree):
            Router({"openrouter": provider}, {"triage": [("openrouter", "vendor/model")]}, Quota(":memory:", {}))
        Router({"openrouter": provider}, {"triage": [("openrouter", "vendor/model:free")]}, Quota(":memory:", {}))


class QuotaTests(unittest.TestCase):
    def test_per_minute_window_and_daily_reset(self):
        now = [0.0]
        quota = Quota(":memory:", {"p": {"rpm": 2}}, clock=lambda: now[0])
        quota.record("p", 1); quota.record("p", 1)
        self.assertFalse(quota.allowed("p"))
        now[0] = 61
        self.assertTrue(quota.allowed("p"))
        daily = Quota(":memory:", {"p": {"tpd": 10}}, clock=lambda: now[0])
        daily.record("p", 10)
        self.assertFalse(daily.allowed("p"))
        now[0] += 86400
        self.assertTrue(daily.allowed("p"))


if __name__ == "__main__":
    unittest.main()


class ProbeTests(unittest.TestCase):
    def test_probe_reports_ok_and_each_kind_of_failure(self):
        import io as _io
        from steelframe.llm.probe import probe
        from steelframe.llm.providers import Result

        class P:
            def complete(self, model, *a):
                if model == "good":
                    return Result("{}", 3, 2, "p", model)
                raise {"busy": RateLimited("429 busy"), "paid": Rejected("400 paid only")}[model]

        out = _io.StringIO()
        rows = probe({"p": P()}, {"p": ["good", "busy", "paid"]}, sleep=lambda s: None, out=out)
        self.assertTrue(rows[0][1].startswith("OK"))
        self.assertIn("RateLimited", rows[1][1])
        self.assertIn("Rejected", rows[2][1])


class EnvTests(unittest.TestCase):
    def test_load_env_parses_and_never_overrides_the_shell(self):
        import tempfile
        from steelframe.env import load_env
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write('# comment\n\nA_KEY=one\nexport B_KEY="two words"\nC_KEY=\'three\'\nbroken line\nSHELL_KEY=from_file\n')
        with mock.patch.dict(os.environ, {"SHELL_KEY": "from_shell"}, clear=False):
            for name in ("A_KEY", "B_KEY", "C_KEY"):
                os.environ.pop(name, None)
            loaded = load_env(f.name)
            self.assertEqual(sorted(loaded), ["A_KEY", "B_KEY", "C_KEY"])
            self.assertEqual((os.environ["A_KEY"], os.environ["B_KEY"], os.environ["C_KEY"]), ("one", "two words", "three"))
            self.assertEqual(os.environ["SHELL_KEY"], "from_shell")
            for name in ("A_KEY", "B_KEY", "C_KEY"):
                os.environ.pop(name, None)
        os.unlink(f.name)

    def test_missing_file_is_fine(self):
        from steelframe.env import load_env
        self.assertEqual(load_env("/nonexistent/.env"), [])
