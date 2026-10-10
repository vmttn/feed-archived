import xml.etree.ElementTree as ET

import pytest

from feed_archived import FeedError, rewrite_feed

MEDIA = "{http://search.yahoo.com/mrss/}"
ATOM = "{http://www.w3.org/2005/Atom}"


def items(xml: bytes) -> list[ET.Element]:
    return ET.fromstring(xml).findall("./channel/item")


def without_link(item: ET.Element) -> str:
    for link in item.findall("link"):
        item.remove(link)
    return ET.canonicalize(ET.tostring(item, encoding="unicode"), strip_text=True)


def test_item_links_point_to_archive(feed_xml: bytes) -> None:
    links = [item.findtext("link") for item in items(rewrite_feed(feed_xml))]

    assert links == [
        "https://archive.ph/newest/https://www.lemonde.fr/politique/article/2026/10/10/budget-2027-le-gouvernement-presente-ses-arbitrages_6600001_823448.html",
        "https://archive.ph/newest/https://www.lemonde.fr/planete/article/2026/10/10/climat-un-mois-de-septembre-record-en-europe_6600002_3244.html",
        "https://archive.ph/newest/https://www.lemonde.fr/sport/live/2026/10/10/en-direct-la-finale-du-top-14_6600003_3242.html",
    ]


@pytest.mark.parametrize("field", ["title", "description", "pubDate", "guid"])
def test_item_fields_are_unchanged(feed_xml: bytes, field: str) -> None:
    before = [item.findtext(field) for item in items(feed_xml)]
    after = [item.findtext(field) for item in items(rewrite_feed(feed_xml))]

    assert after == before
    assert all(after)


def test_guid_attributes_are_unchanged(feed_xml: bytes) -> None:
    after = [item.find("guid").attrib for item in items(rewrite_feed(feed_xml))]

    assert after == [{"isPermaLink": "true"}] * 3


def test_images_are_unchanged(feed_xml: bytes) -> None:
    before = [item.find(f"{MEDIA}content").attrib for item in items(feed_xml)]
    after = [item.find(f"{MEDIA}content").attrib for item in items(rewrite_feed(feed_xml))]

    assert after == before


def test_everything_but_the_link_is_unchanged(feed_xml: bytes) -> None:
    before = [without_link(item) for item in items(feed_xml)]
    after = [without_link(item) for item in items(rewrite_feed(feed_xml))]

    assert after == before


def test_channel_links_are_unchanged(feed_xml: bytes) -> None:
    channel = ET.fromstring(rewrite_feed(feed_xml)).find("channel")

    assert channel.findtext("link") == "https://www.lemonde.fr/rss/une.xml"
    assert channel.find(f"{ATOM}link").get("href") == "https://www.lemonde.fr/rss/une.xml"


def test_namespace_prefixes_survive(feed_xml: bytes) -> None:
    out = rewrite_feed(feed_xml).decode("utf-8")

    assert "<media:content " in out
    assert "<atom:link " in out
    assert "ns0:" not in out
    assert "ns1:" not in out


def test_output_is_utf8_with_declaration(feed_xml: bytes) -> None:
    out = rewrite_feed(feed_xml)

    assert out.startswith(b"<?xml")
    assert "Actualités".encode() in out


def test_feed_without_items_is_rejected() -> None:
    xml = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'

    with pytest.raises(FeedError):
        rewrite_feed(xml)


def test_garbage_is_rejected() -> None:
    with pytest.raises(FeedError):
        rewrite_feed(b"<html><body>Access denied")
