"""Parse an RSS 2.0 or Atom feed into items. Metadata only: title, link, date."""
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

FeedItem = namedtuple("FeedItem", "title link published_at")
ATOM = "{http://www.w3.org/2005/Atom}"
IST = timezone(timedelta(hours=5, minutes=30))  # dates with no zone come from Indian sites


class FeedError(Exception):
    """The body is not a feed we can read."""


def _text(element, tag):
    child = element.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def _date(value):
    value = value.strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)  # RSS dates
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Atom dates
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(timezone.utc).isoformat()


def parse_feed(body):
    """Return (items, skipped). An entry with no link or no title is skipped and counted."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise FeedError(f"not valid XML: {error}") from error
    items, skipped = [], 0
    if root.tag == "rss" or root.find("channel") is not None:
        for node in root.iter("item"):
            title, link = _text(node, "title"), _text(node, "link")
            if not title or not link:
                skipped += 1
                continue
            items.append(FeedItem(title, link, _date(_text(node, "pubDate"))))
    elif root.tag == ATOM + "feed":
        for node in root.findall(ATOM + "entry"):
            title = _text(node, ATOM + "title")
            anchor = node.find(ATOM + "link")
            link = (anchor.get("href") or "").strip() if anchor is not None else ""
            if not title or not link:
                skipped += 1
                continue
            date = _text(node, ATOM + "published") or _text(node, ATOM + "updated")
            items.append(FeedItem(title, link, _date(date)))
    else:
        raise FeedError(f"unknown feed root <{root.tag}>")
    return items, skipped
