"""Mirror Le Monde's RSS feed with article links pointing to archive.today."""

import io
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

FEED_URL = "https://www.lemonde.fr/rss/une.xml"
ARCHIVE_PREFIX = "https://archive.ph/newest/"
OUTPUT = Path("docs/feed.xml")
USER_AGENT = "Mozilla/5.0 (compatible; feed-archived; +https://github.com/vmttn/feed-archived)"
TIMEOUT = 30.0


class FeedError(Exception):
    """The feed could not be downloaded or is not usable."""


def _is_tracking(param: str) -> bool:
    name = param.partition("=")[0].lower()
    return name == "xtor" or name.startswith("utm_")


def clean_url(url: str) -> str:
    """Remove tracking parameters, leaving the rest of the URL as it is."""
    parts = urlsplit(url)
    query = "&".join(p for p in parts.query.split("&") if p and not _is_tracking(p))
    return urlunsplit(parts._replace(query=query))


def archive_url(url: str) -> str:
    return ARCHIVE_PREFIX + clean_url(url)


def rewrite_feed(xml: bytes) -> bytes:
    """Point every item link to its archive.today snapshot."""
    try:
        # Keep the feed's own prefixes (media:, atom:) instead of ns0:, ns1:.
        for _, (prefix, uri) in ET.iterparse(io.BytesIO(xml), events=("start-ns",)):
            try:
                ET.register_namespace(prefix, uri)
            except ValueError:
                pass
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise FeedError(f"feed is not valid XML: {e}") from e

    links = [link for link in root.findall("./channel/item/link") if link.text and link.text.strip()]
    if not links:
        raise FeedError("feed has no items")
    for link in links:
        link.text = archive_url(link.text.strip())

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def fetch_feed() -> bytes:
    request = Request(FEED_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            status: int = response.status
            body: bytes = response.read()
    except OSError as e:
        raise FeedError(f"download failed: {e}") from e
    if status != 200:
        raise FeedError(f"download failed: HTTP {status}")
    return body


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(output: Path = OUTPUT) -> int:
    try:
        feed = rewrite_feed(fetch_feed())
        _write_atomic(output, feed)
    except (FeedError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0
