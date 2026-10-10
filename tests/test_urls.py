import pytest

from feed_archived import archive_url, clean_url

ARTICLE = "https://www.lemonde.fr/politique/article/2026/10/10/budget_6600001_823448.html"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"{ARTICLE}?xtor=RSS-3208", ARTICLE),
        (f"{ARTICLE}?utm_source=x&utm_medium=y", ARTICLE),
        (f"{ARTICLE}?page=2&xtor=RSS-3208&utm_campaign=z&lang=fr", f"{ARTICLE}?page=2&lang=fr"),
        (ARTICLE, ARTICLE),
        (f"{ARTICLE}?page=2#comments", f"{ARTICLE}?page=2#comments"),
    ],
)
def test_clean_url(url: str, expected: str) -> None:
    assert clean_url(url) == expected


def test_archive_url() -> None:
    assert archive_url(f"{ARTICLE}?xtor=RSS-3208") == f"https://archive.ph/newest/{ARTICLE}"
