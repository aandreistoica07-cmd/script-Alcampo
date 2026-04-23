import json
import sys
import time
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

ROOT = Path(__file__).resolve().parent
ACCOUNTS_FILE = ROOT / "accounts.json"
FAIL_FILE = ROOT / "cuentas_fail.json"
EXCEL_FILE = ROOT / "saldos_alcampo_v2.xlsx"


def load_accounts(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de cuentas: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_failed_accounts(failed_accounts, path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(failed_accounts, f, indent=2, ensure_ascii=False)


def enviar_telegram_texto(token: str, chat_id: int, mensaje: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensaje}
    try:
        response = requests.post(url, data=data)
        print(f"📡 Enviando a Telegram: {response.status_code}")
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error CRÍTICO enviando a Telegram: {e}")


def enviar_telegram_documento(token: str, chat_id: int, path: Path, caption=""):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with path.open("rb") as file:
            data = {"chat_id": chat_id, "caption": caption}
            response = requests.post(url, data=data, files={"document": file})
            print(f"📁 Enviando documento a Telegram: {response.status_code}")
            response.raise_for_status()
    except Exception as e:
        print(f"❌ Error CRÍTICO enviando documento a Telegram: {e}")


def configure_driver(chrome_driver_path: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(chrome_driver_path), options=chrome_options)


def obtener_chrome_driver_path():
    try:
        return ChromeDriverManager().install()
    except Exception as e:
        print(f"Error installing ChromeDriver with webdriver_manager: {e}")
        return "/usr/bin/chromedriver"


def procesar_cuenta(email: str, password: str, chrome_driver_path: str):
    print(f"\n→→ Procesando cuenta: {email}")
    intentos_max = 3
    for intento in range(1, intentos_max + 1):
        driver = None
        try:
            if intento > 1:
                print(f"⚠️ Reintentando {email} (Intento {intento}/{intentos_max})...")
            driver = configure_driver(chrome_driver_path)
            driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
            time.sleep(3)
            email_field = driver.find_element(By.ID, "uname1")
            password_field = driver.find_element(By.ID, "pwd1")
            email_field.send_keys(email)
            password_field.send_keys(password)
            password_field.send_keys(Keys.ENTER)
            time.sleep(5)
            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
            time.sleep(2)
            driver.refresh()
            time.sleep(3)
            saldo = "No encontrado"
            try:
                elemento = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/main/div[2]/div[2]/div/div/span"
                )
                saldo = elemento.text.strip()
            except Exception:
                pass
            print(f"✔ {email} → SALDO: {saldo}")
            return {"email": email, "password": password, "saldo": saldo}
        except Exception as e:
            print(f"❌ Error en {email} (Intento {intento}): {e}")
            if intento == intentos_max:
                return {"email": email, "password": password, "saldo": f"Error: {e}"}
            time.sleep(3)
        finally:
            if driver:
                driver.quit()


def limpiar_saldo(saldo_str):
    if saldo_str is None:
        return None
    texto = str(saldo_str).strip()
    if not texto:
        return None
    if "Error" in texto or "No encontrado" in texto:
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", texto)
    if not match:
        return None
    limpio = match.group(0).replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


def main():
    accounts = load_accounts(ACCOUNTS_FILE)
    chrome_driver_path = obtener_chrome_driver_path()
    resultados = []
    print(f"Cargando {len(accounts)} cuentas desde {ACCOUNTS_FILE}")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(procesar_cuenta, acc["email"], acc["password"], chrome_driver_path) for acc in accounts]
        for future in as_completed(futures):
            resultados.append(future.result())
    df = pd.DataFrame(resultados)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"\n💾 Datos guardados en: {EXCEL_FILE}")
    failed = [r for r in resultados if isinstance(r.get("saldo"), str) and r["saldo"].startswith("Error")]
    if failed:
        save_failed_accounts(failed, FAIL_FILE)
        print(f"⚠️ Guardadas {len(failed)} cuentas fallidas en: {FAIL_FILE}")
    else:
        print("✅ No hay cuentas fallidas para guardar.")
    saldo_total = 0.0
    cuentas_con_saldo = 0
    cuentas_saldo_cero = 0
    cuentas_error = 0
    cuenta_top = {"email": "N/A", "saldo_val": 0.0}
    for r in resultados:
        valor = limpiar_saldo(r.get("saldo"))
        if valor is None:
            cuentas_error += 1
            continue
        saldo_total += valor
        if valor > 0:
            cuentas_con_saldo += 1
        elif valor == 0:
            cuentas_saldo_cero += 1
        if valor > cuenta_top["saldo_val"]:
            cuenta_top = {"email": r["email"], "saldo_val": valor}
    mensaje_resumen = (
        f"📊 **RESUMEN ALCAMPO v2**\n\n"
        f"✅ Cuentas procesadas: {len(resultados)}\n"
        f"💰 **Saldo Total:** {saldo_total:.2f} €\n"
        f"💎 Cuentas con dinero: {cuentas_con_saldo}\n"
        f"💤 Cuentas con saldo 0: {cuentas_saldo_cero}\n"
        f"⚠️ Cuentas sin saldo válido: {cuentas_error}\n"
        f"🏆 **Top Cuenta:** {cuenta_top['email']} ({cuenta_top['saldo_val']:.2f} €)"
    )
    print("\n" + mensaje_resumen)
    # enviar_telegram_texto(TELEGRAM_TOKEN, CHAT_ID, mensaje_resumen)
    # enviar_telegram_documento(TELEGRAM_TOKEN, CHAT_ID, EXCEL_FILE, caption="📊 Reporte de saldos de cuentas Alcampo v2")


if __name__ == "__main__":
    main()
