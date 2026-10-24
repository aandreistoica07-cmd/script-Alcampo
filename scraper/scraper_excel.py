#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alcampo Scraper - Versión Independiente y Rápida para Excel
100% limpio: sin circuit breaker, sin cuelgues, sin Firebase.
"""
import sys
import time
import re
import json
import argparse
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
EXCEL_OUTPUT = ROOT / "saldos_alcampo.xlsx"

# Instalar o detectar ChromeDriver
try:
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
except Exception:
    CHROME_DRIVER_PATH = "/usr/bin/chromedriver"


def limpiar_saldo(saldo_str):
    if not saldo_str:
        return None
    texto = str(saldo_str).strip()
    if "Error" in texto or "No encontrado" in texto:
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", texto)
    if not match:
        return None
    try:
        return float(match.group(0).replace(',', '.'))
    except ValueError:
        return None


def cargar_cuentas(filepath=None):
    target = None
    if filepath:
        for p in [Path(filepath), ROOT / filepath, Path.cwd() / filepath]:
            if p.exists() and p.is_file():
                target = p
                break
    if not target:
        for cand in [ROOT / "credenciales_limpias.xlsx", Path("credenciales_limpias.xlsx"), ROOT / "accounts.json"]:
            if cand.exists() and cand.is_file():
                target = cand
                break

    if not target or not target.exists():
        print("❌ Error: No se encontró el archivo de cuentas (credenciales_limpias.xlsx)")
        sys.exit(1)

    print(f"📂 Leyendo cuentas desde: {target.name}")
    ext = target.suffix.lower()

    if ext == ".json":
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("accounts", [])

    df = pd.read_excel(target, engine="odf" if ext == ".ods" else None)
    cols = {str(c).strip().lower(): c for c in df.columns}
    
    email_col = next((cols[c] for c in ["email", "correo", "usuario", "account", "mail", "user"] if c in cols), df.columns[0])
    pass_col = next((cols[c] for c in ["password", "pass", "contraseña", "clave", "pwd"] if c in cols), df.columns[1] if len(df.columns) > 1 else None)

    accounts = []
    for _, row in df.iterrows():
        email_val = str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
        pass_val = str(row[pass_col]).strip() if pass_col and pd.notna(row[pass_col]) else ""
        if email_val and "@" in email_val and not email_val.lower().startswith("email"):
            accounts.append({"email": email_val, "password": pass_val})

    print(f"✔ Total: {len(accounts)} cuentas cargadas.")
    return accounts


def procesar_cuenta(acc, thread_idx, total_accs, current_idx):
    email = acc["email"]
    password = acc["password"]
    print(f"[Hilo {thread_idx}] → Procesando ({current_idx}/{total_accs}): {email}")
    
    driver = None
    saldo = "Error: Desconocido"
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.page_load_strategy = "eager"
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=chrome_options)
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(1)

        # 1. Login
        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
        wait = WebDriverWait(driver, 10)
        email_field = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
        password_field = driver.find_element(By.ID, "pwd1")

        email_field.send_keys(email)
        password_field.send_keys(password)
        password_field.send_keys(Keys.ENTER)

        # 2. Esperar redirección
        try:
            WebDriverWait(driver, 10).until(
                lambda d: ("compraonline.alcampo.es" in d.current_url and "login" not in d.current_url) or "my.site.com" in d.current_url
            )
        except Exception:
            pass

        page_src = driver.page_source.lower()
        curr_url = driver.current_url.lower()

        # Filtro de errores inmediato
        if "call center" in page_src or "bloqueada" in page_src or "913 687 857" in page_src:
            saldo = "Error: Cuenta bloqueada (Call Center)"
            print(f"[Hilo {thread_idx}] 🔴 {email} → {saldo}")
            return {"email": email, "password": password, "saldo": saldo}

        if "incorrect" in page_src or "credenciales" in page_src or "login" in curr_url or "my.site.com" in curr_url:
            saldo = "Error: Credenciales incorrectas o bloqueo"
            print(f"[Hilo {thread_idx}] ⚠️ {email} → {saldo}")
            return {"email": email, "password": password, "saldo": saldo}

        # 3. Petición HTTP rápida para obtener saldo
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            try:
                session.cookies.set(cookie['name'], cookie['value'])
            except Exception:
                pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3"
        }
        res = session.get("https://www.compraonline.alcampo.es/settings/loyalty", headers=headers, timeout=10)
        
        match = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", res.text)
        if match:
            saldo = f"Tu Saldo es {match.group(1)} €"
        else:
            cleaned = re.sub(r'<[^>]+>', ' ', res.text)
            match_alt = re.search(r"Saldo\s*:\s*([\d,.]+)", cleaned, re.IGNORECASE)
            saldo = f"Tu Saldo es {match_alt.group(1)} €" if match_alt else "Saldo: 0.00 €"

        print(f"[Hilo {thread_idx}] ✔ {email} → SALDO: {saldo}")

    except Exception as e:
        saldo = f"Error: {str(e)[:50]}"
        print(f"[Hilo {thread_idx}] ❌ {email} → {saldo}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return {"email": email, "password": password, "saldo": saldo}


def main():
    parser = argparse.ArgumentParser(description="Scraper Alcampo - Versión Simple Excel")
    parser.add_argument("archivo", nargs="?", default="credenciales_limpias.xlsx", help="Archivo Excel")
    parser.add_argument("--threads", type=int, default=2, help="Número de hilos (default: 2)")
    parser.add_argument("--limit", type=int, default=None, help="Límite de cuentas")
    args = parser.parse_args()

    accounts = cargar_cuentas(args.archivo)
    if args.limit:
        accounts = accounts[:args.limit]

    num_threads = min(args.threads, len(accounts)) if accounts else 1
    print(f"\n🚀 Iniciando extracción con {len(accounts)} cuentas en {num_threads} hilos...\n")

    start_time = time.time()
    resultados = []

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(procesar_cuenta, acc, (i % num_threads) + 1, len(accounts), i + 1): acc
            for i, acc in enumerate(accounts)
        }
        for future in as_completed(futures):
            try:
                resultados.append(future.result())
            except Exception:
                pass

    duration = time.time() - start_time

    # Guardar en Excel
    df = pd.DataFrame(resultados)
    df.to_excel(EXCEL_OUTPUT, index=False)
    print(f"\n💾 Excel guardado exitosamente en: {EXCEL_OUTPUT}")
    print(f"⏱️ Tiempo total: {duration:.2f} segundos")

    # Resumen
    saldo_total = 0.0
    con_saldo = 0
    saldo_cero = 0
    errores = 0

    for r in resultados:
        val = limpiar_saldo(r.get("saldo"))
        if val is None:
            errores += 1
        elif val > 0:
            saldo_total += val
            con_saldo += 1
        else:
            saldo_cero += 1

    print("\n" + "="*40)
    print("📊 RESUMEN FINAL")
    print("="*40)
    print(f"✅ Total procesadas: {len(resultados)}")
    print(f"💰 Saldo Total: {saldo_total:.2f} €")
    print(f"💎 Cuentas con saldo: {con_saldo}")
    print(f"💤 Cuentas saldo cero: {saldo_cero}")
    print(f"⚠️ Cuentas con error / bloqueadas: {errores}")
    print("="*40 + "\n")


if __name__ == "__main__":
    main()
