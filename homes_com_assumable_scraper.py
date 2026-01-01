#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 14 13:49:27 2025

@author: johngayton
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import date
import json
import csv
import os
import re

base_url = "https://www.homes.com"
market = "venice-fl"
state = re.search("-([a-z]{2})$", market).group(1)
filters = "houses-for-sale/resale/4-to-5-bedroom/?sfmin=1500&am=53,1&bath-min=2&bath-max=5&parking=2&price-max=600000"


# market_list = [
#     "islip-ny",
#     "bay-shore-ny",
#     "brightwaters-ny",
#     "west-bay-shore-ny",
#     "west-islip-ny",
#     "east-islip-ny",
#     "islip-terrace-ny",
#     ]
     
# for market in market_list:    
    
#     homes_com = "https://www.homes.com/houses-for-sale"
#     filters = "?price-max=800000"
#     state = re.search("-([a-z]{2})$", market).group(1)
    
#     first_step_data = get_property_urls(homes_com, market, filters)
#     second_step_data = get_property_details(first_step_data)
#     write_listing_data(second_step_data)   

first_step_data = get_property_urls(base_url=base_url, market=market, filters=filters)
second_step_data = get_property_details(first_step_data)
write_listing_data(second_step_data)  


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
    
    while True:
        print(f"Scraping Page {page_number}...")
    
        # Extract property URLs from the current page
        listings = driver.find_elements(By.CLASS_NAME, "placard-container")
        for listing in listings:
            try:
                link = listing.find_element(By.TAG_NAME, "a")
                property_urls.append(link.get_attribute("href"))
            except:
                continue  # Skip if no link found
    
        # Store the last extracted listing URL for comparison
        last_url = property_urls[-1] if property_urls else None
    
        # Try to click the "Next" button
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "next.text-only"))  # Ensure it's clickable
            )
    
            driver.execute_script("arguments[0].scrollIntoView();", next_button)  # Scroll into view
            next_button.click()
            time.sleep(3)  # Allow time for page transition
    
            # Wait for a new listing that wasn't on the previous page
            WebDriverWait(driver, 10).until(
                lambda d: last_url not in [listing.get_attribute("href") for listing in d.find_elements(By.CLASS_NAME, "placard-container")]
            )
    
            page_number += 1  # Increment page count
    
        except:
            print("No more pages found.")
            break  # Exit loop if no "Next" button is found
    
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
                 
                st_num = driver.find_element(By.CLASS_NAME, "property-info-address-main").text
                city_state_zip = driver.find_element(By.CLASS_NAME, "property-info-address-citystatezip").text
                address = st_num + ' ' + city_state_zip
                 
                features = driver.find_elements(By.CLASS_NAME, "highlight-value")
                features_list = [feat.text for feat in features]
                 
                bd_bth_sqft_feat = driver.find_elements(By.CLASS_NAME, "property-info-feature")
                 
                bd_bth_sqft_data = {}
                 
                for feature in bd_bth_sqft_feat:
                    try:
                        key_elem = feature.find_element(By.XPATH, "./span[2]")
                        value_elem = feature.find_element(By.CLASS_NAME, "property-info-feature-detail") 
                        
                        key = key_elem.text.strip()
                        value = value_elem.text.strip()
                
                        bd_bth_sqft_data[key] = value  # Store in dictionary
                
                    except:
                        continue  # Skip if elements are missing
                 
                prop_desc = driver.find_element(By.CLASS_NAME, "ldp-description-text").text       
                
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "mortgage-0"))  # Ensure it's clickable
                )
        
                driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", next_button)  # Scroll into view
                time.sleep(5)
                driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", next_button)
                driver.execute_script("window.scrollBy(0, 300);")  # Move up by 100 pixels
                
                next_button.click()    

                time.sleep(5)                
                
                
                try:
                    rows = driver.find_elements(By.CLASS_NAME, "property-history-drawer-row")
                    
                    mortgage_data = {}
                    
                    # Extract key-value pairs
                    for row in rows:
                        cols = row.find_elements(By.CLASS_NAME, "property-history-drawer-col")
                        key = None  # Initialize key variable
                        
                        for col in cols:
                            try:
                                title_elem = col.find_element(By.CLASS_NAME, "property-history-drawer-col-title")
                                value_elem = col.find_element(By.CLASS_NAME, "property-history-drawer-col-text")
                    
                                key = title_elem.text.strip()
                                value = value_elem.text.strip()
                    
                                if key and value:  # Ensure both key and value exist before storing
                                    mortgage_data[key] = value  
                    
                            except:
                                continue  # Skip elements that don’t match
                except Exception as e:
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
                
                            
            except Exception as e:
                print(f"Error processing {prop}: {e}")
                continue  

    finally:
        driver.quit()  

    return listing_data
            

def write_listing_data(final_data):
    
    cur_dt = date.today().strftime("%Y%m%d")
    folder_path = f"/Users/johngayton/Desktop/homes_com_scraping/{state}"
    file_path = f"{market}_{cur_dt}.csv"
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    full_file = f"{folder_path}/{file_path}"
    
    with open(full_file, "w", newline="", encoding = "utf-8") as file:
        writer = csv.writer(file)
        # header row
        writer.writerow(
            [
                "property_url",
                "address",
                "price",
                "features",
                "beds",
                "baths",
                "sq_ft",
                "description",
                "current_mortgage_type",
                "current_mortgage_term",
                "current_mortgage_start_dt",
                "current_mortgage_status",
                "current_mortgage_amount",
                "current_mortgage_balance",
                "current_mortgage_rate",
            ]
        )
        
        for dat in final_data:
            writer.writerow(dat)

        