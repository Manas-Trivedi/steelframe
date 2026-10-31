"""Canonical form of a URL, so the same page is not stored twice."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "source"}


def canonical_url(url):
    parts = urlsplit(url.strip())
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", parts.netloc.lower(), path, urlencode(query), ""))
