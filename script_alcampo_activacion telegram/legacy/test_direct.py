import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from webdriver_manager.chrome import ChromeDriverManager

try:
    print("Installing ChromeDriver...")
    driver_path = ChromeDriverManager().install()
    print(f"ChromeDriver installed at: {driver_path}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = "eager"

    print("Starting driver...")
    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    driver.set_page_load_timeout(30)
    
    try:
        print("Navigating to login page...")
        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
        time.sleep(4)
        
        print("Looking for input fields...")
        try:
            uname = driver.find_element(By.ID, "uname1")
            print("✔ Found username input field.")
        except Exception as e:
            print(f"❌ Failed to find username field: {e}")
            print(f"Current page URL: {driver.current_url}")
            # Print page source to see if we got blocked
            source = driver.page_source
            print(f"Page source length: {len(source)}")
            if "blocked" in source.lower() or "challenge" in source.lower():
                print("🚨 BOT DETECTION DETECTED (Cloudflare / Salesforce Shield block)!")
            raise e
            
        pwd = driver.find_element(By.ID, "pwd1")
        
        print("Entering credentials...")
        uname.send_keys("nflmadrid2004@yahoo.es")
        pwd.send_keys("Cibona69")
        pwd.send_keys(Keys.ENTER)
        
        print("Waiting 6 seconds for redirect...")
        time.sleep(6)
        print(f"Current URL: {driver.current_url}")
        
        print("Navigating to loyalty page...")
        driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
        time.sleep(3)
        print(f"Loyalty URL: {driver.current_url}")
        
        try:
            el = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/main/div[2]/div[2]/div/div/span")
            print(f"✔ Initial text read: '{el.text}'")
        except Exception as e:
            print(f"❌ Initial read failed: {e}")
            
        print("Refreshing loyalty page (Salesforce session sync)...")
        driver.refresh()
        time.sleep(4)
        
        try:
            el = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/main/div[2]/div[2]/div/div/span")
            print(f"✔ Post-refresh text read: '{el.text}'")
        except Exception as e:
            print(f"❌ Post-refresh read failed: {e}")
            
    finally:
        print("Quitting driver...")
        driver.quit()

except Exception as e:
    print(f"CRITICAL ERROR in test: {e}")
