import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def open_chrome_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    # Add more options to simulate human behavior
    options.add_argument("--disable-blink-features=AutomationControlled")
    return uc.Chrome(options=options)


def get_property_urls(base_url, market="", filters=""):
    url = f"{base_url}/{market}/{filters}"

    driver = open_chrome_driver()
    driver.get(url)

    time.sleep(10)

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
                next_button.click()
                time.sleep(3)  # Allow time for page transition

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


def get_property_details(property_urls):
    listing_data = []

    driver = open_chrome_driver()

    try:
        for prop in property_urls:
            try:
                print(f"Navigating to: {prop}")
                driver.get(prop)

                time.sleep(10)

                # Extract data you need (example: title, price, etc.)
                price = driver.find_element(By.CLASS_NAME, "property-info-price").text

                st_num = driver.find_element(
                    By.CLASS_NAME, "property-info-address-main"
                ).text
                city_state_zip = driver.find_element(
                    By.CLASS_NAME, "property-info-address-citystatezip"
                ).text
                address = f"{st_num} {city_state_zip}"

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

                prop_desc = driver.find_element(
                    By.CLASS_NAME, "ldp-description-text"
                ).text

                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "mortgage-0"))
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'end'});", next_button
                )
                time.sleep(5)
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'end'});", next_button
                )
                driver.execute_script("window.scrollBy(0, 300);")

                next_button.click()

                time.sleep(5)

                try:
                    rows = driver.find_elements(
                        By.CLASS_NAME, "property-history-drawer-row"
                    )

                    mortgage_data = {}

                    # Extract key-value pairs
                    for row in rows:
                        cols = row.find_elements(
                            By.CLASS_NAME, "property-history-drawer-col"
                        )
                        key = None  # Initialize key variable

                        for col in cols:
                            try:
                                title_elem = col.find_element(
                                    By.CLASS_NAME,
                                    "property-history-drawer-col-title",
                                )
                                value_elem = col.find_element(
                                    By.CLASS_NAME,
                                    "property-history-drawer-col-text",
                                )

                                key = title_elem.text.strip()
                                value = value_elem.text.strip()

                                if key and value:
                                    mortgage_data[key] = value

                            except Exception:
                                continue  # Skip elements that do not match
                except Exception:
                    print("Mortgage data not found")
                    continue

                listing_data.append(
                    [
                        prop,
                        address,
                        price,
                        features_list,
                        bd_bth_sqft_data.get("Beds", ""),
                        bd_bth_sqft_data.get("Baths", ""),
                        bd_bth_sqft_data.get("Sq Ft", ""),
                        prop_desc,
                        mortgage_data.get("Loan Type", ""),
                        mortgage_data.get("Loan Term", ""),
                        mortgage_data.get("Date", ""),
                        mortgage_data.get("Status", ""),
                        mortgage_data.get("Total Amount", ""),
                        mortgage_data.get("Outstanding Balance", ""),
                        mortgage_data.get("Interest Rate", ""),
                    ]
                )

            except Exception as exc:
                print(f"Error processing {prop}: {exc}")
                continue

    finally:
        driver.quit()

    return listing_data
