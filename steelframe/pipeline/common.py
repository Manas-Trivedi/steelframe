"""Shared set-up for the model stages."""
import json

from ..env import load_env
from ..llm.providers import build_providers
from ..llm.quota import Quota
from ..llm.router import Router


def build_router(config_path="config/models.json", quota_path="data/raw/quota.sqlite"):
    """Load keys from .env and return a Router over the configured free routes."""
    load_env()
    with open(config_path) as f:
        config = json.load(f)
    return Router(build_providers(config), config["routes"], Quota(quota_path, config["limits"]))
