import sys
import time
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scraper"))

from scraper.script_optimizado import create_stealth_driver, submit_login_form
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = create_stealth_driver(headless=True)
try:
    print("Iniciando login...")
    driver.get("https://www.compraonline.alcampo.es/login?destination=%2Fsettings%2Floyalty")
    wait = WebDriverWait(driver, 20)
    u = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
    p = wait.until(EC.presence_of_element_located((By.ID, "pwd1")))
    u.send_keys("noelia_gll@hotmail.com")
    p.send_keys("Paseohernani5")
    submit_login_form(driver)
    
    time.sleep(10)
    if "settings/loyalty" not in driver.current_url:
        driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
        time.sleep(4)
        
    print("URL en settings/loyalty:", driver.current_url)
    
    # Check if loyalty-manage-button exists
    btns = driver.find_elements(By.CSS_SELECTOR, "a[data-test='loyalty-manage-button']")
    if btns:
        href = btns[0].get_attribute("href")
        aria = btns[0].get_attribute("aria-label")
        print("Encontrado botón con href:", href)
        print("Aria-label:", aria)
        
        # Navigate to href
        print("Navegando a la URL del Club Alcampo...")
        driver.get(href)
        time.sleep(8)
        print("URL final tras navegar a miportal:", driver.current_url)
        driver.save_screenshot("screenshots/noelia_miportal.png")
        
        portal_html = driver.page_source or ""
        with open("dump_miportal.html", "w", encoding="utf-8") as f:
            f.write(portal_html)
        print("Dump de miportal guardado. Tamaño:", len(portal_html))
        
        # Check patterns in miportal
        for pat in [r"[\d,.]+\s*€", r"saldo", r"puntos", r"400200\d{7}"]:
            m = re.findall(pat, portal_html, re.IGNORECASE)
            print(f"Miportal patrón '{pat}': {len(m)} -> {m[:10]}")
    else:
        print("No se encontró loyalty-manage-button")
        
finally:
    driver.quit()
