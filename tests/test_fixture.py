import xml.etree.ElementTree as ET


def test_fixture_has_three_items(feed_xml: bytes) -> None:
    root = ET.fromstring(feed_xml)

    assert len(root.findall("./channel/item")) == 3
