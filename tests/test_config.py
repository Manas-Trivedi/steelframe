import json
import unittest

from steelframe.llm.providers import build_providers
from steelframe.llm.quota import Quota
from steelframe.llm.router import Router


class ModelConfigTests(unittest.TestCase):
    config = json.load(open("config/models.json"))

    def test_every_route_uses_a_probed_candidate_and_passes_the_free_guard(self):
        routes = {stage: [tuple(r) for r in route] for stage, route in self.config["routes"].items()}
        for stage, route in routes.items():
            for provider, model in route:
                self.assertIn(model, self.config["candidates"][provider], f"{stage}: {provider}/{model}")
        Router(build_providers(self.config), routes, Quota(":memory:", {}))  # raises NotFree if any model is not free

    def test_checkers_do_not_start_on_the_writers_provider(self):
        first = {stage: route[0][0] for stage, route in self.config["routes"].items() if route}
        self.assertNotEqual(first["fact_checker"], first["writer"])
        self.assertNotEqual(first["examiner"], first["writer"])

    def test_every_stage_has_at_least_two_providers(self):
        for stage, route in self.config["routes"].items():
            self.assertGreaterEqual(len({r[0] for r in route}), 2, stage)


if __name__ == "__main__":
    unittest.main()
