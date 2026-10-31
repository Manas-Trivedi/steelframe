"""Fetch one URL. Retry only what a retry can fix."""
import socket
import time
import urllib.error
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; SteelframeBot/0.1; +https://github.com/Manas-Trivedi/steelframe)"
MAX_BYTES = 10 * 1024 * 1024
RETRY_STATUS = {429} | set(range(500, 600))


class FetchRejected(Exception):
    """The server refused the request in a way a retry cannot fix (4xx except 429, or too large)."""


class FetchFailed(Exception):
    """A rate limit, server error or network failure that kept failing after the retries."""


def fetch(url, *, timeout=20, attempts=3, sleep=time.sleep, opener=urllib.request.urlopen):
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener(request, timeout=timeout) as response:
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise FetchRejected(f"{url}: response larger than {MAX_BYTES} bytes")
            return body
        except urllib.error.HTTPError as error:  # before URLError: it is a subclass
            if error.code not in RETRY_STATUS:
                raise FetchRejected(f"{url}: HTTP {error.code}") from error
            last = error
        except (urllib.error.URLError, socket.timeout, ConnectionError) as error:
            last = error
        if attempt < attempts - 1:
            sleep(2 ** attempt)
    raise FetchFailed(f"{url}: {last}") from last
