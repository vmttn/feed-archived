from pathlib import Path
from typing import Self

import pytest

import feed_archived
from feed_archived import FEED_URL, FeedError, fetch_feed, main

EMPTY_FEED = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'


class FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def serve(monkeypatch: pytest.MonkeyPatch, status: int, body: bytes) -> list[object]:
    calls: list[object] = []

    def fake_urlopen(request: object, timeout: float | None = None) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse(status, body)

    monkeypatch.setattr(feed_archived, "urlopen", fake_urlopen)
    return calls


def fail(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def fake_urlopen(request: object, timeout: float | None = None) -> FakeResponse:
        raise error

    monkeypatch.setattr(feed_archived, "urlopen", fake_urlopen)


def test_fetch_returns_body(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = serve(monkeypatch, 200, b"<rss/>")

    assert fetch_feed() == b"<rss/>"

    request, timeout = calls[0]
    assert request.full_url == FEED_URL
    assert request.get_header("User-agent")
    assert timeout


def test_fetch_raises_on_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, 500, b"oops")

    with pytest.raises(FeedError):
        fetch_feed()


def test_fetch_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    fail(monkeypatch, TimeoutError("timed out"))

    with pytest.raises(FeedError):
        fetch_feed()


def test_main_writes_feed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, feed_xml: bytes) -> None:
    serve(monkeypatch, 200, feed_xml)
    output = tmp_path / "docs" / "feed.xml"

    assert main(output) == 0

    assert b"https://archive.ph/newest/https://www.lemonde.fr/" in output.read_bytes()
    assert list(output.parent.iterdir()) == [output]


def test_main_replaces_previous_feed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, feed_xml: bytes) -> None:
    serve(monkeypatch, 200, feed_xml)
    output = tmp_path / "feed.xml"
    output.write_bytes(b"last good feed")

    assert main(output) == 0

    assert output.read_bytes() != b"last good feed"


def test_failed_download_keeps_previous_feed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fail(monkeypatch, TimeoutError("timed out"))
    output = tmp_path / "feed.xml"
    output.write_bytes(b"last good feed")

    assert main(output) != 0

    assert output.read_bytes() == b"last good feed"
    assert list(tmp_path.iterdir()) == [output]


def test_empty_feed_keeps_previous_feed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    serve(monkeypatch, 200, EMPTY_FEED)
    output = tmp_path / "feed.xml"
    output.write_bytes(b"last good feed")

    assert main(output) != 0

    assert output.read_bytes() == b"last good feed"
    assert list(tmp_path.iterdir()) == [output]
