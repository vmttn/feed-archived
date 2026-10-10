from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def feed_xml() -> bytes:
    return (FIXTURES / "une.xml").read_bytes()
