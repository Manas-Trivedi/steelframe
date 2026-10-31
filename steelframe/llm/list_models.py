"""Print the model names a provider offers, so config/models.json uses real names.

    python3 -m steelframe.llm.list_models [provider ...]

Needs the provider's key in its environment variable. Check each model's free status on the provider's
own pricing page before adding it to a route: only OpenRouter shows it in the name (':free').
"""
import json
import sys

from ..env import load_env
from .errors import LLMError
from .providers import build_providers


def main(argv=None):
    load_env()
    names = (argv if argv is not None else sys.argv[1:])
    providers = build_providers(json.load(open("config/models.json")))
    status = 0
    for name in names or providers:
        try:
            print(f"== {name}")
            print("\n".join(providers[name].list_models()))
        except LLMError as error:
            print(f"   failed: {error}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
