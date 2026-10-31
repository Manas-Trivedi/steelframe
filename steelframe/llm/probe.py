"""Try each candidate model once and report whether the free key can use it.

    python3 -m steelframe.llm.probe [provider ...]

One tiny request per model, 4 seconds apart, so the free per-minute limit is respected. With billing off
at the provider a model outside the free tier fails instead of charging. A 429 that mentions a limit of
zero means "not in the free tier"; a plain 429 means "busy, try again later".
"""
import json
import sys
import time

from .errors import LLMError
from .providers import build_providers

SYSTEM = "Reply with JSON only."
USER = 'Return exactly this JSON: {"ok": true}'


def probe(providers, candidates, sleep=time.sleep, out=sys.stdout):
    rows = []
    for name, models in candidates.items():
        for model in models:
            started = time.time()
            try:
                result = providers[name].complete(model, SYSTEM, USER, True, 64)
                outcome = f"OK  {time.time() - started:4.1f}s  {result.tokens_in}+{result.tokens_out} tokens"
            except LLMError as error:
                outcome = f"{type(error).__name__}: {str(error)[:110]}"
            rows.append((f"{name}/{model}", outcome))
            print(f"{name}/{model:48} {outcome}", file=out)
            sleep(4)
    return rows


def main(argv=None):
    config = json.load(open("config/models.json"))
    chosen = (argv if argv is not None else sys.argv[1:]) or list(config["candidates"])
    candidates = {n: config["candidates"][n] for n in chosen}
    probe(build_providers(config), candidates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
