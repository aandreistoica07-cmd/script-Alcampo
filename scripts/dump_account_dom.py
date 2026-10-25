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
    
    # Wait for redirect
    for _ in range(30):
        time.sleep(1)
        cur = driver.current_url or ""
        if "settings/loyalty" in cur and "login" not in cur and "authorization" not in cur:
            print("Redirigido a:", cur)
            break
    
    if "settings/loyalty" not in driver.current_url:
        print("Navegando directamente a /settings/loyalty...")
        driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
    
    time.sleep(4)
    
    # Try closing cookie banner if present
    try:
        cookie_btns = driver.find_elements(By.CSS_SELECTOR, "button")
        for b in cookie_btns:
            txt = (b.text or "").lower()
            if "aceptar" in txt or "rechazar" in txt:
                driver.execute_script("arguments[0].click();", b)
                print(f"Botón de cookies pulsado: {txt}")
                break
    except Exception as ce:
        print("Cookie click ex:", ce)
    
    time.sleep(3)
    driver.save_screenshot("screenshots/noelia_post_cookie.png")
    
    html = driver.page_source or ""
    with open("dump_loyalty.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML guardado con éxito. Tamaño:", len(html))
    
    # Regex search
    patterns = [
        r"Tu Saldo es\s*[\d,.]+",
        r"[\d,.]+\s*€",
        r"Mi cuenta Club Alcampo",
        r"400200\d{7}",
    ]
    for pat in patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        print(f"Patrón '{pat}': encontrados {len(matches)} -> {matches[:10]}")
        
finally:
    driver.quit()
