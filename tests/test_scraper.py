import os

import pytest

from loan_scraper.main import (
    _cleanup_property_urls,
    _write_property_urls,
    build_filters,
    build_parser,
)
from loan_scraper.scraper import (
    _detect_blocked_page,
    _extract_listing_id,
    _chrome_profile_directory,
    _chrome_debugger_address,
    _chrome_user_data_dir,
    _close_driver,
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


def test_detect_blocked_page():
    class FakeDriver:
        title = "Access Denied"
        page_source = "<html><body>Access Denied</body></html>"

        def find_element(self, *_args):
            class Body:
                text = "You don't have permission to access this server."

            return Body()

    marker, body_sample = _detect_blocked_page(FakeDriver())
    assert marker == "access denied"
    assert "permission" in body_sample


def test_detect_blocked_page_ignores_source_only_captcha():
    class FakeDriver:
        title = "Homes for Sale"
        page_source = "<html><script>captchaToken = '';</script><body>Valid listings</body></html>"

        def find_element(self, *_args):
            class Body:
                text = "Valid listings"

            return Body()

    marker, body_sample = _detect_blocked_page(FakeDriver())
    assert marker is None
    assert body_sample == ""


def test_build_filters_defaults_to_unfiltered_market():
    args = build_parser().parse_args(["--market", "chesterfield-mo"])
    assert build_filters(args) == ""


def test_build_filters_only_includes_explicit_query_filters():
    args = build_parser().parse_args(
        ["--market", "chesterfield-mo", "--price-max", "700000"]
    )
    assert build_filters(args) == "?price-max=700000"


def test_build_filters_supports_explicit_path_filters():
    args = build_parser().parse_args(
        [
            "--market",
            "chesterfield-mo",
            "--property-type",
            "houses-for-sale",
            "--listing-type",
            "resale",
            "--bed-min",
            "4",
            "--bed-max",
            "5",
            "--price-max",
            "700000",
        ]
    )
    assert build_filters(args) == "houses-for-sale/resale/4-to-5-bedroom/?price-max=700000"


def test_chrome_profile_env(monkeypatch, tmp_path):
    profile_path = tmp_path / "chrome-profile"
    monkeypatch.setenv("CHROME_USER_DATA_DIR", str(profile_path))
    monkeypatch.setenv("CHROME_PROFILE_DIRECTORY", "Default")

    assert _chrome_user_data_dir() == str(profile_path)
    assert _chrome_profile_directory() == "Default"


def test_chrome_debugger_address_env(monkeypatch):
    monkeypatch.setenv("CHROME_DEBUGGER_ADDRESS", "127.0.0.1:9222")
    assert _chrome_debugger_address() == "127.0.0.1:9222"


def test_write_property_urls(tmp_path):
    output_path = tmp_path / "urls.txt"
    _write_property_urls(["https://example.com/a", "https://example.com/b"], output_path)
    assert output_path.read_text(encoding="utf-8") == (
        "https://example.com/a\nhttps://example.com/b\n"
    )


def test_cleanup_property_urls(tmp_path):
    output_path = tmp_path / "urls.txt"
    output_path.write_text("https://example.com/a\n", encoding="utf-8")
    _cleanup_property_urls(output_path)
    assert not output_path.exists()


def test_close_driver_skips_quit_in_debugger_attach_mode(monkeypatch):
    class FakeDriver:
        quit_called = False

        def quit(self):
            self.quit_called = True

    driver = FakeDriver()
    monkeypatch.setenv("CHROME_DEBUGGER_ADDRESS", "127.0.0.1:9222")
    _close_driver(driver)
    assert not driver.quit_called


def test_close_driver_quits_owned_browser(monkeypatch):
    class FakeDriver:
        quit_called = False

        def quit(self):
            self.quit_called = True

    driver = FakeDriver()
    monkeypatch.delenv("CHROME_DEBUGGER_ADDRESS", raising=False)
    _close_driver(driver)
    assert driver.quit_called


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
