import os

import pytest

from loan_scraper.scraper import (
    _extract_listing_id,
    _major_version_from_text,
    _parse_int_text,
    get_property_details,
)
from loan_scraper.output import write_listing_data


def test_parse_int_text():
    assert _parse_int_text("$123,456") == 123456
    assert _parse_int_text("1,200 sq ft") == 1200
    assert _parse_int_text("") is None
    assert _parse_int_text(None) is None


def test_extract_listing_id():
    url = "https://www.homes.com/property/100-abaco-dr-e-cedar-point-nc/w3p44ve2xfvs9/"
    assert _extract_listing_id(url) == "w3p44ve2xfvs9"


def test_major_version_from_text():
    assert _major_version_from_text("Google Chrome 147.0.7727.138") == 147
    assert _major_version_from_text("ChromeDriver 148.0.0") == 148
    assert _major_version_from_text("") is None


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SCRAPE") != "1",
    reason="Set RUN_LIVE_SCRAPE=1 to run the live scrape test.",
)
def test_live_scrape_single_url():
    url = "https://www.homes.com/property/100-abaco-dr-e-cedar-point-nc/w3p44ve2xfvs9/"
    listing_data = get_property_details([url], market="cedar-point-nc")
    assert len(listing_data) == 1
    row = listing_data[0]
    assert row[0] == url
    assert row[1] == "cedar-point-nc"
    assert row[-1] == "w3p44ve2xfvs9"

    required_env = ("PGHOST", "PGDATABASE", "PGUSER")
    if all(os.getenv(k) for k in required_env):
        write_listing_data(listing_data)
    else:
        pytest.skip("Missing PGHOST/PGDATABASE/PGUSER for insert test.")
