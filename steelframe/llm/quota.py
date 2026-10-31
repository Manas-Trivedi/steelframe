"""Client-side counter. Stops calls before a free tier's own limit, so we never hit its wall."""
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timezone


class Quota:
    def __init__(self, path, limits, clock=time.time):
        """limits: {provider: {"rpm": int, "rpd": int, "tpd": int}}. Missing keys mean no limit of that kind."""
        self.limits, self.clock = limits, clock
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT, provider TEXT, calls INTEGER,"
                        " tokens INTEGER, PRIMARY KEY (day, provider))")
        self.recent = defaultdict(deque)

    def _day(self):
        return datetime.fromtimestamp(self.clock(), timezone.utc).strftime("%Y-%m-%d")

    def allowed(self, provider):
        limit = self.limits.get(provider, {})
        now = self.clock()
        window = self.recent[provider]
        while window and now - window[0] > 60:
            window.popleft()
        if "rpm" in limit and len(window) >= limit["rpm"]:
            return False
        row = self.db.execute("SELECT calls, tokens FROM usage WHERE day = ? AND provider = ?",
                              (self._day(), provider)).fetchone() or (0, 0)
        return not (("rpd" in limit and row[0] >= limit["rpd"]) or ("tpd" in limit and row[1] >= limit["tpd"]))

    def record(self, provider, tokens):
        self.recent[provider].append(self.clock())
        with self.db:
            self.db.execute("INSERT INTO usage (day, provider, calls, tokens) VALUES (?, ?, 1, ?)"
                            " ON CONFLICT (day, provider) DO UPDATE SET calls = calls + 1, tokens = tokens + ?",
                            (self._day(), provider, tokens, tokens))
