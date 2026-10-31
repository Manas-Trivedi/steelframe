"""Load KEY=value lines from a .env file into the environment. No dependency.

A variable that is already set in the shell wins over the file. The file is git-ignored, so keys never
reach the repository.
"""
import os


def load_env(path=".env"):
    """Return the names loaded. A missing file is fine: keys may come from the shell instead."""
    loaded = []
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return loaded
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded
