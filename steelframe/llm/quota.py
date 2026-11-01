"""Client-side counter. Stops calls before a free tier's own limit, so we never hit its wall."""
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class Quota:
    def __init__(self, path, limits, clock=time.time):
        """limits: {name: {"rpm": int, "rpd": int, "tpd": int, "tz": str}}. Missing keys mean no limit of that kind.

        A name is a provider ("gemini") or one model ("gemini/gemini-3.1-flash-lite"). Calls are counted and
        limited per model, because the providers limit each model on its own; a model's entry overrides the
        provider's, which is the default for models without one. `tz` is the time zone whose midnight starts
        the provider's day (Google's day starts at midnight Pacific); the default is UTC.
        """
        self.limits, self.clock = limits, clock
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT, provider TEXT, calls INTEGER,"
                        " tokens INTEGER, PRIMARY KEY (day, provider))")
        self.recent = defaultdict(deque)

    def limit(self, key):
        """The limits for "provider/model": the provider's, overridden by the model's own."""
        return {**self.limits.get(key.split("/", 1)[0], {}), **self.limits.get(key, {})}

    def _day(self, limit):
        zone = ZoneInfo(limit["tz"]) if "tz" in limit else timezone.utc
        return datetime.fromtimestamp(self.clock(), zone).strftime("%Y-%m-%d")

    def allowed(self, provider):
        """`provider` is a "provider/model" key (a bare provider name works too)."""
        limit = self.limit(provider)
        now = self.clock()
        window = self.recent[provider]
        while window and now - window[0] > 60:
            window.popleft()
        if "rpm" in limit and len(window) >= limit["rpm"]:
            return False
        row = self.db.execute("SELECT calls, tokens FROM usage WHERE day = ? AND provider = ?",
                              (self._day(limit), provider)).fetchone() or (0, 0)
        return not (("rpd" in limit and row[0] >= limit["rpd"]) or ("tpd" in limit and row[1] >= limit["tpd"]))

    def record(self, provider, tokens):
        self.recent[provider].append(self.clock())
        with self.db:
            self.db.execute("INSERT INTO usage (day, provider, calls, tokens) VALUES (?, ?, 1, ?)"
                            " ON CONFLICT (day, provider) DO UPDATE SET calls = calls + 1, tokens = tokens + ?",
                            (self._day(self.limit(provider)), provider, tokens, tokens))
