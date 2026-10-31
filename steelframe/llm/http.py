"""One JSON POST or GET, with failures sorted into the error classes in errors.py."""
import json
import socket
import urllib.error
import urllib.request

from .errors import AuthError, Rejected, RateLimited, Unavailable

USER_AGENT = "steelframe-pipeline/0.1"


def request_json(url, *, headers, payload=None, timeout=60, opener=urllib.request.urlopen):
    data = None if payload is None else json.dumps(payload).encode()
    all_headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json", **headers}
    request = urllib.request.Request(url, data=data, headers=all_headers,
                                     method="GET" if payload is None else "POST")
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read()[:300].decode("utf-8", "replace") if hasattr(error, "read") else ""
        if error.code == 429:
            raise RateLimited(f"429 {detail}", _retry_after(error)) from error
        if error.code in (401, 403):
            raise AuthError(f"{error.code} {detail}") from error
        if error.code >= 500:
            raise Unavailable(f"{error.code} {detail}") from error
        raise Rejected(f"{error.code} {detail}") from error
    except (urllib.error.URLError, socket.timeout, ConnectionError) as error:
        raise Unavailable(f"network: {error}") from error
    try:
        return json.loads(body)
    except ValueError as error:
        raise Unavailable(f"reply is not JSON: {body[:100]!r}") from error


def _retry_after(error):
    try:
        return float(error.headers.get("Retry-After"))
    except (AttributeError, TypeError, ValueError):
        return None
