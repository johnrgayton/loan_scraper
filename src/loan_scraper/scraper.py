import os
import random
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


SLEEP_MIN_SECONDS = float(os.getenv("SCRAPER_SLEEP_MIN", "1.5"))
SLEEP_MAX_SECONDS = float(os.getenv("SCRAPER_SLEEP_MAX", "3.5"))
SCRAPER_DEBUG_DIR = os.getenv("SCRAPER_DEBUG_DIR", "/tmp/loan_scraper_debug")
DEFAULT_CHROME_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
BLOCKED_PAGE_MARKERS = (
    "access denied",
    "you don't have permission to access",
    "unusual traffic",
    "verify you are human",
    "captcha",
    "just a moment",
)


class ScraperBlockedError(RuntimeError):
    pass


def _sleep_jitter(min_seconds=SLEEP_MIN_SECONDS, max_seconds=SLEEP_MAX_SECONDS):
    if min_seconds <= 0 and max_seconds <= 0:
        return
    time.sleep(random.uniform(min_seconds, max_seconds))


def _major_version_from_text(value):
    if not value:
        return None
    match = re.search(r"\b(\d+)\.\d+\.\d+\.\d+\b", value)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d{2,})\b", value)
    return int(match.group(1)) if match else None


def _run_version_command(executable):
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return " ".join(part for part in (result.stdout, result.stderr) if part).strip()


def _resolve_executable(candidates):
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.exists(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _detect_executable_major(candidates):
    executable = _resolve_executable(candidates)
    if not executable:
        return None, None
    version_text = _run_version_command(executable)
    return executable, _major_version_from_text(version_text)


def _configured_chrome_version_main():
    raw_version = os.getenv("CHROME_VERSION_MAIN", "").strip()
    if not raw_version:
        return None
    try:
        return int(raw_version)
    except ValueError as exc:
        raise ValueError("CHROME_VERSION_MAIN must be an integer Chrome major version.") from exc


def _validate_browser_driver_versions():
    """Fail before Selenium starts when browser/driver versions are clearly incompatible."""
    expected_major = _configured_chrome_version_main()
    chrome_binary = os.getenv("CHROME_BINARY_PATH")
    chrome_candidates = (chrome_binary, *DEFAULT_CHROME_CANDIDATES)
    chrome_path, chrome_major = _detect_executable_major(chrome_candidates)
    driver_path, driver_major = _detect_executable_major(("chromedriver",))

    if expected_major and chrome_major and chrome_major != expected_major:
        raise RuntimeError(
            f"CHROME_VERSION_MAIN={expected_major} does not match Chrome "
            f"{chrome_major} at {chrome_path}."
        )

    if chrome_major and driver_major and chrome_major != driver_major:
        raise RuntimeError(
            f"Chrome major version {chrome_major} at {chrome_path} does not match "
            f"ChromeDriver major version {driver_major} at {driver_path}. "
            "Rebuild the Docker image or set CHROME_VERSION_MAIN to the installed "
            "Chrome major so undetected-chromedriver can fetch a compatible driver."
        )


def _is_headless_enabled():
    return os.getenv("SCRAPER_HEADLESS", "").strip().lower() in ("1", "true", "yes", "y")


def _chrome_user_data_dir():
    return os.getenv("CHROME_USER_DATA_DIR", "").strip()


def _chrome_profile_directory():
    return os.getenv("CHROME_PROFILE_DIRECTORY", "").strip()


def _is_debug_enabled():
    return os.getenv("SCRAPER_DEBUG", "").strip().lower() in ("1", "true", "yes", "y")


def _is_staged_navigation_enabled():
    return os.getenv("SCRAPER_STAGED_NAVIGATION", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
    )


def _market_url(base_url, market):
    return f"{base_url.rstrip('/')}/{market.strip('/')}/"


def _search_url(base_url, market, filters):
    return f"{_market_url(base_url, market)}{filters.lstrip('/')}"


def _safe_debug_name(url, label):
    parsed = urlparse(url)
    raw_path = f"{parsed.netloc}{parsed.path}".strip("/") or "page"
    safe_path = re.sub(r"[^a-zA-Z0-9._-]+", "_", raw_path).strip("_")
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{label}_{safe_path[:120]}"


def _write_debug_artifacts(driver, url, label):
    """Capture enough state to diagnose bot blocks or selector drift after a failed load."""
    if not _is_debug_enabled():
        return None

    debug_dir = Path(SCRAPER_DEBUG_DIR)
    debug_dir.mkdir(parents=True, exist_ok=True)
    base_path = debug_dir / _safe_debug_name(url, label)
    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        pass

    html_path = base_path.with_suffix(".html")
    text_path = base_path.with_suffix(".txt")
    screenshot_path = base_path.with_suffix(".png")

    html_path.write_text(driver.page_source, encoding="utf-8")
    text_path.write_text(
        "\n".join(
            [
                f"url={url}",
                f"current_url={driver.current_url}",
                f"title={driver.title}",
                "",
                body_text,
            ]
        ),
        encoding="utf-8",
    )
    try:
        driver.save_screenshot(str(screenshot_path))
    except Exception:
        screenshot_path = None

    paths = [str(html_path), str(text_path)]
    if screenshot_path:
        paths.append(str(screenshot_path))
    return paths


def _get_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return ""


def _detect_blocked_page(driver):
    title = (driver.title or "").lower()
    body_text = _get_body_text(driver)
    body_lower = body_text.lower()
    source_lower = (driver.page_source or "").lower()
    for marker in BLOCKED_PAGE_MARKERS:
        if marker in title or marker in body_lower or marker in source_lower:
            return marker, body_text[:500]
    return None, ""


def _raise_if_blocked(driver, url):
    marker, body_sample = _detect_blocked_page(driver)
    if not marker:
        return

    debug_paths = _write_debug_artifacts(driver, url, "blocked")
    details = [
        f"Scraper appears blocked while loading {url}.",
        f"Detected marker: {marker!r}.",
    ]
    if body_sample:
        details.append(f"Page text sample: {body_sample!r}.")
    if debug_paths:
        details.append(f"Debug artifacts: {', '.join(debug_paths)}.")
    raise ScraperBlockedError(" ".join(details))


def _wait_for_listing_cards(driver, url):
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "placard-container"))
        )
    except Exception as exc:
        _raise_if_blocked(driver, url)
        debug_paths = _write_debug_artifacts(driver, url, "missing_placards")
        message = (
            f"Timed out waiting for listing cards on {url}. "
            "The site markup may have changed, the page may still be loading, "
            "or the request may have been blocked without a known marker."
        )
        if debug_paths:
            message += f" Debug artifacts: {', '.join(debug_paths)}."
        raise RuntimeError(message) from exc


def _load_search_page(driver, base_url, market, filters):
    final_url = _search_url(base_url, market, filters)
    print(f"Loading search URL: {final_url}")

    if not _is_staged_navigation_enabled():
        driver.get(final_url)
        _raise_if_blocked(driver, final_url)
        return final_url

    # Staged navigation gives the browser a more normal sequence before filters apply.
    staged_urls = [base_url.rstrip("/") + "/", _market_url(base_url, market)]
    if final_url != staged_urls[-1]:
        staged_urls.append(final_url)

    for staged_url in staged_urls:
        print(f"Navigating staged URL: {staged_url}")
        driver.get(staged_url)
        _raise_if_blocked(driver, staged_url)
        _sleep_jitter(2, 4)

    return final_url


def open_chrome_driver(proxy_url=None):
    _validate_browser_driver_versions()

    options = uc.ChromeOptions()
    chrome_binary = os.getenv("CHROME_BINARY_PATH")
    if chrome_binary:
        options.binary_location = chrome_binary
    user_data_dir = _chrome_user_data_dir()
    if user_data_dir:
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={user_data_dir}")
    profile_directory = _chrome_profile_directory()
    if profile_directory:
        options.add_argument(f"--profile-directory={profile_directory}")
    if _is_headless_enabled():
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    # Add more options to simulate human behavior
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    proxy = proxy_url or os.getenv("SCRAPER_PROXY_URL")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    return uc.Chrome(options=options, version_main=_configured_chrome_version_main())


def _parse_int_text(value):
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def _parse_city_state_zip(value):
    if not value:
        return "", "", ""
    match = re.search(r"^(.*?),\s*([A-Z]{2})\s+(\d{5})", value.strip())
    if not match:
        return value.strip(), "", ""
    city, state, zip_code = match.groups()
    return city.strip(), state.strip(), zip_code.strip()


def _extract_listing_id(url):
    if not url:
        return ""
    match = re.search(r"/([^/]+)/?$", url)
    return match.group(1) if match else ""


def get_property_urls(base_url, market="", filters=""):
    driver = open_chrome_driver()
    url = _load_search_page(driver, base_url, market, filters)

    _wait_for_listing_cards(driver, url)
    _sleep_jitter(4, 7)

    property_urls = []
    page_number = 1  # Track current page

    try:
        while True:
            print(f"Scraping Page {page_number}...")

            # Extract property URLs from the current page
            listings = driver.find_elements(By.CLASS_NAME, "placard-container")
            for listing in listings:
                try:
                    link = listing.find_element(By.TAG_NAME, "a")
                    property_urls.append(link.get_attribute("href"))
                except Exception:
                    continue  # Skip if no link found

            # Store the last extracted listing URL for comparison
            last_url = property_urls[-1] if property_urls else None

            # Try to click the "Next" button
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "next.text-only"))
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView();", next_button
                )  # Scroll into view
                _sleep_jitter()
                next_button.click()
                _sleep_jitter(4, 6)

                # Wait for a new listing that wasn't on the previous page
                WebDriverWait(driver, 10).until(
                    lambda d: last_url
                    not in [
                        listing.get_attribute("href")
                        for listing in d.find_elements(By.CLASS_NAME, "placard-container")
                    ]
                )

                page_number += 1  # Increment page count

            except Exception:
                print("No more pages found.")
                break  # Exit loop if no "Next" button is found
    finally:
        driver.quit()

    return property_urls


def get_property_details(property_urls, market=""):
    listing_data = []

    driver = open_chrome_driver()
    session_id = driver.session_id

    try:
        for prop in property_urls:
            try:
                print(f"Navigating to: {prop}")
                driver.get(prop)

                wait = WebDriverWait(driver, 15)
                wait.until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "property-info-price")
                    )
                )
                _sleep_jitter(5, 8)

                # Extract data you need (example: title, price, etc.)
                raw_price = driver.find_element(
                    By.CLASS_NAME, "property-info-price"
                ).text
                price = _parse_int_text(raw_price)

                st_num = driver.find_element(
                    By.CLASS_NAME, "property-info-address-main"
                ).text
                city_state_zip = driver.find_element(
                    By.CLASS_NAME, "property-info-address-citystatezip"
                ).text
                _sleep_jitter()
                city, state, zip_code = _parse_city_state_zip(city_state_zip)
                address = st_num.strip()

                features = driver.find_elements(By.CLASS_NAME, "highlight-value")
                features_list = [feat.text for feat in features]

                bd_bth_sqft_feat = driver.find_elements(
                    By.CLASS_NAME, "property-info-feature"
                )

                bd_bth_sqft_data = {}

                for feature in bd_bth_sqft_feat:
                    try:
                        key_elem = feature.find_element(By.XPATH, "./span[2]")
                        value_elem = feature.find_element(
                            By.CLASS_NAME, "property-info-feature-detail"
                        )

                        key = key_elem.text.strip()
                        value = value_elem.text.strip()

                        bd_bth_sqft_data[key] = value  # Store in dictionary

                    except Exception:
                        continue  # Skip if elements are missing

                _sleep_jitter()
                prop_desc = driver.find_element(
                    By.CLASS_NAME, "ldp-description-text"
                ).text

                mortgage_rows = []
                try:
                    heading = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "//h2[normalize-space()='Mortgage History' or "
                                "normalize-space()='Mortgage history']",
                            )
                        )
                    )
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", heading
                    )
                    _sleep_jitter(2, 4)
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", heading
                    )
                    driver.execute_script("window.scrollBy(0, 200);")
                    _sleep_jitter(1.5, 3)

                    table = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "(//h2[normalize-space()='Mortgage History' or "
                                "normalize-space()='Mortgage history']/following::table)[1]",
                            )
                        )
                    )

                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    for row in rows:
                        cells = [
                            c.text.strip()
                            for c in row.find_elements(By.CSS_SELECTOR, "th,td")
                        ]
                        if len(cells) >= 4:
                            amount = _parse_int_text(cells[2])
                            mortgage_rows.append(
                                {
                                    "date": cells[0],
                                    "status": cells[1],
                                    "amount": amount,
                                    "loan_type": cells[3],
                                }
                            )
                except Exception:
                    print("Mortgage data not found")

                listing_data.append(
                    [
                        prop,
                        market,
                        address,
                        city,
                        state,
                        zip_code,
                        price,
                        features_list,
                        bd_bth_sqft_data.get("Beds", ""),
                        bd_bth_sqft_data.get("Baths", ""),
                        _parse_int_text(bd_bth_sqft_data.get("Sq Ft", "")),
                        prop_desc,
                        session_id,
                        mortgage_rows,
                        _extract_listing_id(prop),
                    ]
                )
                _sleep_jitter(3, 6)

            except Exception as exc:
                print(f"Error processing {prop}: {exc}")
                continue

    finally:
        driver.quit()

    return listing_data
