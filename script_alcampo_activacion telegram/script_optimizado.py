# @section: Config-And-AntiBan

import sys
import time
import re
import json
import argparse
import os
import html
import random
import subprocess
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
ACCOUNTS_FILENAME = os.environ.get("ALCAMPO_ACCOUNTS_FILE", "accounts.json")
ACCOUNTS_FILE = ROOT / ACCOUNTS_FILENAME
EXCEL_FILE = ROOT / "saldos_alcampo.xlsx"

# --- FEATURE FLAGS (REVERSIBLE OPTIMIZATIONS & ANTI-BAN GUARDS) ---
OPT_DIRECT_LOYALTY_REDIRECT = os.environ.get("OPT_DIRECT_LOYALTY_REDIRECT", "1") == "1"
OPT_DYNAMIC_WAIT = os.environ.get("OPT_DYNAMIC_WAIT", "1") == "1"
OPT_EAGER_LIGHT_CHROME = os.environ.get("OPT_EAGER_LIGHT_CHROME", "1") == "1"
OPT_ADAPTIVE_PACING = os.environ.get("OPT_ADAPTIVE_PACING", "1") == "1"
OPT_IP_CANARY = os.environ.get("OPT_IP_CANARY", "1") == "1"
MAX_EXECUTION_MINUTES = float(os.environ.get("MAX_EXECUTION_MINUTES", "13.5"))


def mask_email(email):
    """Masks email addresses in console/CI logs to prevent leaking PII in GitHub Actions logs."""
    if not email or "@" not in str(email):
        return "***"
    local, domain = str(email).split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***{local[-1]}@{domain}"


def cleanup_orphan_chrome():
    """Cleans up orphan chromedriver processes on Linux CI runners at start/end."""
    if os.name != "nt" and os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["pkill", "-f", "chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass


def decode_accounts_secret_payload(b64_str, expected_count=None, write_path=None):
    """Decodes ACCOUNTS_BASE64 (supports both gzip+base64 starting with 0x1f 0x8b and plain base64).
    Validates JSON list and expected_count without printing sensitive data."""
    import base64
    import gzip
    cleaned = (b64_str or "").strip()
    if not cleaned:
        print("❌ ERROR CRÍTICO: Secret ACCOUNTS_BASE64 está vacío.")
        sys.exit(1)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for line in cleaned.splitlines():
            if line.strip():
                original_print(f"::add-mask::{line.strip()}", flush=True)
    try:
        raw_bytes = base64.b64decode(cleaned)
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: Fallo al decodificar Base64 en ACCOUNTS_BASE64 ({type(e).__name__}).")
        sys.exit(1)
    if len(raw_bytes) >= 2 and raw_bytes[0] == 0x1F and raw_bytes[1] == 0x8B:
        try:
            raw_bytes = gzip.decompress(raw_bytes)
        except Exception as e:
            print(f"❌ ERROR CRÍTICO: Fallo al descomprimir Gzip (0x1f 0x8b) en ACCOUNTS_BASE64 ({type(e).__name__}).")
            sys.exit(1)
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: El contenido de ACCOUNTS_BASE64 no es un JSON UTF-8 válido ({type(e).__name__}).")
        sys.exit(1)
    if not isinstance(data, list):
        print("❌ ERROR CRÍTICO: El JSON de ACCOUNTS_BASE64 no contiene una lista de cuentas.")
        sys.exit(1)
    if expected_count is not None and len(data) != int(expected_count):
        print(f"❌ ERROR CRÍTICO: ACCOUNTS_BASE64 contiene {len(data)} cuentas tras decodificar, pero se esperaban exactamente {expected_count}.")
        sys.exit(1)
    if write_path is not None:
        Path(write_path).write_bytes(raw_bytes)
    return data


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
    
    if file is None or file == sys.stdout or file == sys.stderr:
        msg = sep.join(str(arg) for arg in args)
        kwargs['flush'] = True
        with log_lock:
            original_print(*args, **kwargs)
            try:
                with open(ROOT / "consola.log", "a", encoding="utf-8") as f:
                    f.write(msg + end)
            except Exception:
                pass
    else:
        original_print(*args, **kwargs)

builtins.print = print_and_log


# --- ADAPTIVE PACER (ANTI-RATE-LIMIT & BACKOFF) ---
class AdaptivePacer:
    """Ritmo adaptativo por máquina: aplica pausa base con jitter aleatorio entre cuentas.
    Si detecta presión (lentitud, timeout, authenticationError, 429/403), sube la pausa
    con backoff exponencial; si encadena éxitos rápidos, la reduce gradualmente hasta el mínimo seguro."""
    def __init__(self, base_delay=0.65, min_delay=0.35, max_delay=10.0):
        self.lock = threading.Lock()
        self.current_delay = base_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.consecutive_ok = 0

    def wait(self):
        if not OPT_ADAPTIVE_PACING:
            return
        with self.lock:
            delay = self.current_delay
        jitter = random.uniform(0.10, 0.45)
        time.sleep(delay + jitter)

    def record_success(self, elapsed_s):
        with self.lock:
            self.consecutive_ok += 1
            if elapsed_s > 20.0:
                # Respuesta lenta del servidor -> subir ligeramente el ritmo
                self.current_delay = min(self.max_delay, self.current_delay * 1.25)
            elif self.consecutive_ok >= 3:
                self.current_delay = max(self.min_delay, self.current_delay * 0.90)

    def record_pressure(self, reason=""):
        with self.lock:
            self.consecutive_ok = 0
            self.current_delay = min(self.max_delay, max(1.5, self.current_delay * 1.85))
            new_d = self.current_delay
        print(f"⚠️ [PACER] Señal de presión detectada ({reason}). Pausa adaptativa incrementada a {new_d:.2f}s")

adaptive_pacer = AdaptivePacer()


# --- CIRCUIT BREAKER (SERVER DOWN / CLOUDFLARE / IP BAN GUARD) ---
class CircuitBreaker:
    """Interruptor de Seguridad: distingue 'account_error' (credenciales) y 'needs_attention'
    (Call Center / reset password) de 'ip_error' (429, Cloudflare, captcha, timeout).
    Solo dispara la cuarentena de la máquina ante errores reales de IP/servidor."""
    def __init__(self, max_consecutive_failures=4, max_failure_ratio=0.45, min_processed_threshold=6):
        self.lock = threading.Lock()
        self.consecutive_server_errors = 0
        self.total_server_errors = 0
        self.total_processed = 0
        self.max_consecutive = max_consecutive_failures
        self.max_ratio = max_failure_ratio
        self.min_threshold = min_processed_threshold
        self.triggered = False
        self.trigger_reason = ""

    def classify_error(self, status_code=None, page_source="", error_msg=""):
        """Returns ('needs_attention' | 'account_error' | 'ip_error', reason_str)."""
        combined = f"{page_source} {error_msg}".lower()

        # 1. Permanent account blocks requiring human / Call Center intervention (DO NOT RETRY, NOT AN IP ERROR)
        if "call center" in combined or "tu cuenta ha sido bloqueada" in combined or "btnpwreset" in combined or "restablecer contraseña" in combined:
            return "needs_attention", "Cuenta bloqueada (Call Center / Password Reset)"

        # 2. Invalid credentials (DO NOT RETRY, NOT AN IP ERROR)
        if "credenciales incorrectas" in combined or "usuario o contraseña incorrectos" in combined:
            return "account_error", "Credenciales incorrectas"

        # 3. Server / Cloudflare / IP rate-limit / Timeout errors
        if status_code and (500 <= status_code <= 599 or status_code in (403, 429, 520, 521, 522, 523, 524, 525, 526)):
            return "ip_error", f"HTTP Status {status_code}"

        cf_signatures = [
            "error 522", "error 524", "error 520", "error 502", "error 503", "error 504",
            "502 bad gateway", "503 service unavailable", "504 gateway time-out",
            "connection timed out", "host error", "cloudflare ray id", "origin unreachable",
            "captcha", "challenge-platform"
        ]
        for sig in cf_signatures:
            if sig in combined:
                return "ip_error", f"Firma Cloudflare/Captcha: '{sig}'"

        ip_block_signatures = [
            "authenticationerror", "bloqueo/timeout",
            "too many requests", "rate limit", "429 too many requests",
            "access denied", "access forbidden", "blocked by cloudflare"
        ]
        for sig in ip_block_signatures:
            if sig in combined:
                return "ip_error", f"IP Rate-Limit / Timeout: '{sig}'"

        maint_signatures = [
            "mantenimiento", "estamos realizando tareas de mantenimiento",
            "sitio en mantenimiento", "servidor no disponible", "web temporalmente fuera de servicio"
        ]
        for sig in maint_signatures:
            if sig in combined:
                return "ip_error", f"Banner Mantenimiento: '{sig}'"

        return "ip_error", "Timeout / Red"

    def is_server_down_error(self, status_code=None, page_source="", error_msg=""):
        err_type, reason = self.classify_error(status_code, page_source, error_msg)
        return (err_type == "ip_error"), reason

    def record_result(self, is_server_error, reason="", error_type="ok"):
        with self.lock:
            self.total_processed += 1
            if is_server_error and error_type == "ip_error":
                self.consecutive_server_errors += 1
                self.total_server_errors += 1
            else:
                self.consecutive_server_errors = 0

            ratio = (self.total_server_errors / self.total_processed) if self.total_processed > 0 else 0.0

            if self.consecutive_server_errors >= self.max_consecutive:
                self.triggered = True
                self.trigger_reason = f"🚨 {self.consecutive_server_errors} errores IP/servidor consecutivos ({reason})"
            elif self.total_processed >= self.min_threshold and ratio > self.max_ratio:
                self.triggered = True
                self.trigger_reason = f"🚨 {ratio*100:.1f}% de errores IP/servidor en {self.total_processed} cuentas"

            return self.triggered, self.trigger_reason

circuit_breaker = CircuitBreaker(max_consecutive_failures=4, max_failure_ratio=0.45, min_processed_threshold=6)


def run_ip_canary(worker_label="Worker"):
    """Canario por IP: verifica antes de reclamar cuentas de la cola que la IP de la máquina
    puede alcanzar el portal de login sin bloqueo 403/429/Cloudflare."""
    if not OPT_IP_CANARY:
        return True
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        res = requests.get("https://www.compraonline.alcampo.es/login", headers=headers, timeout=12)
        if res.status_code in (403, 429, 503):
            print(f"🐤 [CANARIO IP] ❌ {worker_label} bloqueado con HTTP {res.status_code}. Máquina en cuarentena.")
            return False
        low_body = res.text[:4000].lower()
        if "blocked by cloudflare" in low_body or "access denied" in low_body:
            print(f"🐤 [CANARIO IP] ❌ {worker_label} detectó bloqueo Cloudflare/WAF. Máquina en cuarentena.")
            return False
        print(f"🐤 [CANARIO IP] ✔ {worker_label} IP verificada sana (HTTP {res.status_code}).")
        return True
    except Exception as e:
        print(f"🐤 [CANARIO IP] ⚠️ {worker_label} advertencia de red en canario ({e}), continuando con precaución...")
        return True


def get_firebase_url():
    if os.environ.get("DISABLE_FIREBASE_SYNC") == "1":
        return None
    url = (os.environ.get("FIREBASE_DB_URL") or "").strip()
    if not url or url.lower() in ("none", "null", "***", "undefined") or not url.startswith("http"):
        return "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
    return url


def get_telegram_config():
    token = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    
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

# @end: Config-And-AntiBan


# @section: Progress-And-FirebaseSync

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

results_lock = threading.Lock()
local_results = {}

def update_progress(thread_idx, email, status, saldo_str, worker_name="Worker"):
    """Thread-safely updates progress metrics, saves to progreso.json, and pushes deduplicated results & thread state to Firebase."""
    global progress_state, local_results
    
    saldo_val = limpiar_saldo(saldo_str)
    worker_id = f"{worker_name}_t{thread_idx}"
    email_key = email.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
    now = time.time()
    
    result_entry = {
        "email": email,
        "status": status,
        "saldo": saldo_str,
        "balance": saldo_val,
        "timestamp": now
    }
    thread_payload = {
        "worker": worker_name,
        "thread": thread_idx,
        "last_account": mask_email(email),
        "last_status": status,
        "timestamp": now
    }
    
    with log_lock:
        with results_lock:
            local_results[email_key] = result_entry
            progress_state["threads"][worker_id] = thread_payload
            
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
                elif st in ("error", "needs_attention"):
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
                prefix = os.environ.get("FIREBASE_QUEUE_PREFIX", "")
                url = firebase_url.strip().rstrip('/')
                firebase_session.put(f"{url}/{prefix}results/{email_key}.json", json=result_entry, timeout=8)
                firebase_session.patch(f"{url}/{prefix}queue/{email_key}.json", json={
                    "status": status,
                    "saldo": saldo_str,
                    "balance": saldo_val,
                    "claimed_by": worker_id,
                    "finished_at": now,
                    "timestamp": now
                }, timeout=8)
                firebase_session.put(f"{url}/{prefix}threads/{worker_id}.json", json=thread_payload, timeout=8)
                
                res = firebase_session.get(f"{url}/{prefix}results.json", timeout=8)
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
                    elif st in ("error", "needs_attention"):
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
                    "is_finished": fb_processed >= fb_total and fb_total > 0,
                    "threads": progress_state.get("threads", {}),
                    "timestamp": time.time()
                }
                
                with log_lock:
                    progress_state.update(prog_snap)
                    
                firebase_session.put(f"{url}/{prefix}progress.json", json=prog_snap, timeout=8)
                
                try:
                    log_path = ROOT / "consola.log"
                    if log_path.exists():
                        with open(log_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        filtered = [l for l in lines if not (l.strip().startswith('#') and '0x' in l)
                                    and 'Stacktrace:' not in l and '(Session info:' not in l and '<unknown>' not in l]
                        latest_logs = "".join(filtered[-100:])
                        firebase_session.put(f"{url}/{prefix}logs.json", json=latest_logs, timeout=8)
                except Exception:
                    pass
            except Exception:
                pass
                
        threading.Thread(target=push_to_firebase, daemon=True).start()

# @end: Progress-And-FirebaseSync


# @section: Firebase-DynamicQueue

queue_lock = threading.Lock()
firebase_session = requests.Session()
fb_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
firebase_session.mount("https://", fb_adapter)
firebase_session.mount("http://", fb_adapter)

def init_firebase_queue(accounts):
    """Initializes the shared work-stealing queue and clears old results and threads on Firebase Realtime DB."""
    firebase_url = get_firebase_url()
    if not firebase_url:
        return False
    prefix = os.environ.get("FIREBASE_QUEUE_PREFIX", "")
    try:
        url = firebase_url.strip().rstrip('/')
        queue_data = {}
        now = time.time()
        for acc in accounts:
            email_key = acc["email"].replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
            queue_data[email_key] = {
                "email": acc["email"],
                "password": acc["password"],
                "status": "pending",
                "claimed_by": None,
                "retries": 0,
                "timestamp": now
            }
        firebase_session.put(f"{url}/{prefix}queue.json", json=queue_data, timeout=10)
        firebase_session.delete(f"{url}/{prefix}results.json", timeout=10)
        firebase_session.delete(f"{url}/{prefix}threads.json", timeout=10)
        
        init_progress_data = {
            "total": len(accounts),
            "processed": 0,
            "success": 0,
            "money": 0,
            "zero": 0,
            "error": 0,
            "total_balance": 0.0,
            "elapsed": 0.0,
            "start_time": now,
            "is_finished": False,
            "threads": {},
            "timestamp": now
        }
        firebase_session.put(f"{url}/{prefix}progress.json", json=init_progress_data, timeout=10)
        firebase_session.put(f"{url}/{prefix}logs.json", json="🚀 [SISTEMA] Iniciando Alcampo Scraper v2.1 (Cola Dinámica + Anti-Ban)...\n", timeout=10)
        print(f"📦 [FIREBASE QUEUE] Cola '{prefix}queue' inicializada con {len(accounts)} cuentas pendientes (progress=0, is_finished=False).")
        return True
    except Exception as e:
        print(f"⚠️ Error inicializando cola dinámica en Firebase: {e}")
        return False

def claim_account_from_queue(worker_id):
    """Atomically claims the next pending or stale (>75s lease) account from the shared Firebase queue."""
    firebase_url = get_firebase_url()
    if not firebase_url:
        return None
    prefix = os.environ.get("FIREBASE_QUEUE_PREFIX", "")
    
    with queue_lock:
        try:
            url = firebase_url.strip().rstrip('/') + f"/{prefix}queue.json"
            res = firebase_session.get(url, timeout=8)
            if not res.ok:
                return None
            queue_data = res.json()
            if not isinstance(queue_data, dict):
                return None

            now = time.time()
            # Phase 1: Try claiming a pending account
            for key, item in queue_data.items():
                if isinstance(item, dict) and item.get("status") == "pending":
                    claim_url = firebase_url.strip().rstrip('/') + f"/{prefix}queue/{key}.json"
                    item["status"] = "in_progress"
                    item["claimed_by"] = str(worker_id)
                    item["claimed_at"] = now
                    item["lease_until"] = now + 75.0
                    item["timestamp"] = now
                    firebase_session.put(claim_url, json=item, timeout=8)
                    return {"email": item["email"], "password": item["password"]}

            # Phase 2: Stale lease recovery (work stealing for accounts in_progress > 75s without completion)
            for key, item in queue_data.items():
                if isinstance(item, dict) and item.get("status") == "in_progress":
                    last_time = item.get("timestamp") or item.get("claimed_at") or 0
                    retries = int(item.get("retries") or 0)
                    if now - last_time > 75.0 and retries < 2:
                        print(f"🏴‍☠️ [WORK STEAL] Reclamando cuenta con lease expirado {mask_email(item.get('email', ''))} de {item.get('claimed_by')}.")
                        claim_url = firebase_url.strip().rstrip('/') + f"/{prefix}queue/{key}.json"
                        item["status"] = "in_progress"
                        item["claimed_by"] = str(worker_id)
                        item["claimed_at"] = now
                        item["lease_until"] = now + 75.0
                        item["retries"] = retries + 1
                        item["timestamp"] = now
                        firebase_session.put(claim_url, json=item, timeout=8)
                        return {"email": item["email"], "password": item["password"]}

            return None
        except Exception as e:
            print(f"Warning claiming account from queue: {e}")
            return None


def release_account_to_queue(email, reason="ip_error"):
    """Returns an account to 'pending' in Firebase queue when an IP/network error occurs,
    provided it has not exceeded max_retries (2), so another healthy VM can process it."""
    firebase_url = get_firebase_url()
    if not firebase_url:
        return False
    prefix = os.environ.get("FIREBASE_QUEUE_PREFIX", "")
    with queue_lock:
        try:
            email_key = email.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
            item_url = firebase_url.strip().rstrip('/') + f"/{prefix}queue/{email_key}.json"
            res = firebase_session.get(item_url, timeout=8)
            if not res.ok or not isinstance(res.json(), dict):
                return False
            item = res.json()
            retries = int(item.get("retries") or 0)
            if retries >= 2:
                return False
            item["status"] = "pending"
            item["claimed_by"] = None
            item["retries"] = retries + 1
            item["last_error"] = str(reason)[:100]
            item["timestamp"] = time.time()
            firebase_session.put(item_url, json=item, timeout=8)
            print(f"🔄 [QUEUE RELEASE] Cuenta {mask_email(email)} devuelta a cola ('pending', retry {retries + 1}/2) por error IP/red.")
            return True
        except Exception as e:
            print(f"Warning releasing account to queue: {e}")
            return False


def claim_accounts_from_queue(worker_id, count=1):
    """Wrapper for batch claiming compatibility."""
    acc = claim_account_from_queue(worker_id)
    return [acc] if acc else []


# Default system ChromeDriver path (Selenium Manager is primary in _create_chrome_driver)
CHROME_DRIVER_PATH = "/usr/bin/chromedriver"


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
        requests.put(url, json=payload, timeout=8)
    except Exception as e:
        print(f"Error actualizando progreso en Firebase: {e}")

# @end: Firebase-DynamicQueue


# @section: SingleAccount-And-CLI

def check_single_account(email, password, scrape_card=True, existing_card_number=None):
    """Logs in and checks the balance (and optionally card number) of a single account.
    If existing_card_number is provided, skips the card scraping entirely.
    Returns: {"status": "success"/"error", "balance": float/None, "card_number": str/None, "error": str/None}
    """
    driver = None
    try:
        update_single_check_progress(email, "running", "Iniciando...", 20)
        driver = _create_chrome_driver()
        
        # 1. Login directly towards /settings/loyalty
        update_single_check_progress(email, "running", "Cargando...", 35)
        login_url = (
            "https://www.compraonline.alcampo.es/login?destination=%2Fsettings%2Floyalty"
            if OPT_DIRECT_LOYALTY_REDIRECT
            else "https://www.compraonline.alcampo.es/login?destination=%2F"
        )
        driver.get(login_url)
        wait = WebDriverWait(driver, 18)
            
        email_field = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
        password_field = driver.find_element(By.ID, "pwd1")
        email_field.clear()
        email_field.send_keys(email)
        password_field.clear()
        password_field.send_keys(password)
        
        update_single_check_progress(email, "running", "Logueando...", 50)
        _submit_login_form(driver)
        
        outcome = "pending"
        outcome_msg = ""
        poll_start = time.time()
        while time.time() - poll_start < 15.0:
            outcome, outcome_msg = _check_login_outcome(driver)
            if outcome in ("logged_in", "error"):
                break
            time.sleep(0.25)

        if outcome != "logged_in":
            raise Exception(outcome_msg or "Login rechazado o timeout en autorización")
        
        update_single_check_progress(email, "running", "Saldo...", 70)
        saldo_str = _extract_loyalty_balance(driver, timeout_s=12.0)
        balance = limpiar_saldo(saldo_str)
        if balance is None:
            raise Exception(f"No se pudo determinar el saldo: {saldo_str}")
            
        # 4. Optional: scrape card number
        card_number = existing_card_number if existing_card_number else None
        if scrape_card and not card_number:
            update_single_check_progress(email, "running", "Tarjeta...", 85)
            try:
                if "settings/loyalty" not in driver.current_url:
                    driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                card_wait = WebDriverWait(driver, 10)
                
                try:
                    accept_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar cookies') or contains(text(), 'Aceptar')]")
                    accept_btn.click()
                except Exception:
                    pass
                
                btn = card_wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Mi cuenta Club Alcampo')]/.. | //a[contains(text(), 'Mi cuenta Club Alcampo')]")))
                main_handle = driver.current_window_handle
                btn.click()
                
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
                    try:
                        WebDriverWait(driver, 12).until(
                            lambda d: re.search(r'\b\d{13}\b', d.page_source) or re.search(r'value="\?clif=(\d+)"', d.page_source)
                        )
                    except Exception:
                        pass
                    portal_html = driver.page_source
                    
                    match_clif = re.search(r'value="\?clif=(\d+)"', portal_html)
                    if match_clif:
                        card_number = match_clif.group(1)
                    else:
                        match_13 = re.search(r'\b\d{13}\b', portal_html)
                        if match_13:
                            card_number = match_13.group(0)
            except Exception as e:
                print(f"Advertencia: No se pudo extraer número de tarjeta: {e}")
        elif card_number:
            print("✔ Reutilizando número de tarjeta existente (sin scraping)")
                
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
            except Exception:
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
        default=2, 
        help="Number of concurrent threads per VM (default: 2 for optimal anti-ban safety)"
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


def _sanitize_telegram_error(err, token=None):
    msg = type(err).__name__
    raw = str(err)
    if token and token in raw:
        raw = raw.replace(token, "***")
    raw = re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot***", raw)
    return f"{msg}: {raw[:140]}" if raw else msg


def enviar_telegram_texto(token, chat_id, mensaje):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=15)
        print(f"📡 Enviando a Telegram: {response.status_code}")
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error sending to Telegram ({_sanitize_telegram_error(e, token)})")
        return False


def enviar_telegram_documento(token, chat_id, path, caption=""):
    if not token or not chat_id or not path:
        return False
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(path, "rb") as file:
            data = {"chat_id": chat_id, "caption": caption}
            response = requests.post(url, data=data, files={"document": file}, timeout=15)
            print(f"📁 Enviando documento a Telegram: {response.status_code}")
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"❌ Error enviando documento a Telegram ({_sanitize_telegram_error(e, token)})")
        return False


def enviar_telegram(token, chat_id, texto, excel_path=None):
    ok = enviar_telegram_texto(token, chat_id, texto)
    if excel_path and os.path.exists(excel_path):
        ok = enviar_telegram_documento(token, chat_id, excel_path, caption="📊 Reporte de saldos de cuentas Alcampo") and ok
    return ok

# @end: SingleAccount-And-CLI


# @section: Core-ScraperEngine

def _build_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    if OPT_EAGER_LIGHT_CHROME:
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.page_load_strategy = "eager"
    else:
        chrome_options.page_load_strategy = "normal"
    return chrome_options


def _create_chrome_driver():
    opts = _build_chrome_options()
    try:
        drv = webdriver.Chrome(options=opts)
    except Exception:
        drv = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=opts)
    drv.set_page_load_timeout(25)
    drv.implicitly_wait(0)
    return drv


def _submit_login_form(driver):
    """Submits the Salesforce Visualforce login form by clicking #btnSubmit_login via JS,
    bypassing onkeyup='return noenter(event)' that blocks Keys.ENTER."""
    submit_btns = driver.find_elements(
        By.CSS_SELECTOR,
        "#btnSubmit_login, input[id*='btnSubmit'], input[type='submit'], button[type='submit']"
    )
    if submit_btns:
        driver.execute_script("arguments[0].click();", submit_btns[0])
    else:
        pwd_el = driver.find_element(By.ID, "pwd1")
        pwd_el.send_keys(Keys.ENTER)


def _check_login_outcome(driver):
    """Inspects current URL and visible error modals on Salesforce authorization page.
    Returns: ('logged_in', '') | ('error', saldo_error_msg) | ('pending', '')"""
    try:
        curr_url = driver.current_url
    except Exception:
        return "pending", ""

    curr_low = curr_url.lower()
    if (
        "compraonline.alcampo.es" in curr_low
        and "login" not in curr_low
        and "oauth" not in curr_low
        and "callback" not in curr_low
        and "my.site.com" not in curr_low
        and "authorization" not in curr_low
        and "authenticationerror" not in curr_low
        and (not OPT_DIRECT_LOYALTY_REDIRECT or "settings/loyalty" in curr_low)
    ):
        return "logged_in", ""

    if "authenticationerror" in curr_low:
        return "error", "Error: authenticationError"

    try:
        reset_els = driver.find_elements(By.ID, "btnPwReset")
        if any(el.is_displayed() for el in reset_els):
            return "error", "Error: Requiere restablecer contraseña (btnPwReset)"
    except Exception:
        pass

    try:
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal.show, .modal-body, #errorNotifyBlockWarning")
        for m in modals:
            txt = (m.text or "").strip()
            if not txt:
                continue
            txt_low = txt.lower()
            if "call center" in txt_low or "bloqueada" in txt_low:
                return "error", "Error: Cuenta bloqueada (Call Center 913 687 857)"
            if "incorrect" in txt_low or "credenciales" in txt_low or "contraseña" in txt_low or "usuario" in txt_low:
                return "error", "Error: Credenciales incorrectas"
            if "demasiados intentos" in txt_low or "too many" in txt_low:
                return "error", "Error: 429 Too Many Requests"
    except Exception:
        pass

    return "pending", ""


def _extract_loyalty_balance(driver, timeout_s=10.0):
    """Waits dynamically for SPA hydration of 'Tu Saldo es X,XX €' on /settings/loyalty."""
    if "settings/loyalty" not in driver.current_url:
        try:
            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
        except Exception:
            pass

    pattern = re.compile(r"Tu Saldo es\s*([\d,.]+)\s*(?:&nbsp;|\s)*€?", re.IGNORECASE)
    if OPT_DYNAMIC_WAIT:
        start_w = time.time()
        while time.time() - start_w < timeout_s:
            try:
                html_src = driver.page_source
                m = pattern.search(html_src)
                if m:
                    return f"Tu Saldo es {m.group(1)} €"
                cleaned = " ".join(re.sub(r"<[^>]+>", " ", html_src).split())
                m2 = pattern.search(cleaned)
                if m2:
                    return f"Tu Saldo es {m2.group(1)} €"
            except Exception:
                pass
            time.sleep(0.25)
    else:
        time.sleep(3.5)
        html_src = driver.page_source
        m = pattern.search(html_src)
        if m:
            return f"Tu Saldo es {m.group(1)} €"

    return "No encontrado"


def _scrape_account_with_driver(driver, init_driver_fn, email, password, label_prefix):
    """Executes login + balance extraction for one account with timing instrumentation and error classification."""
    t_account_start = time.time()
    t_chrome = 0.0
    t_login = 0.0
    t_loyalty = 0.0
    saldo = "Error: Desconocido"
    err_type = "ip_error"
    intentos_max = 2

    login_url = (
        "https://www.compraonline.alcampo.es/login?destination=%2Fsettings%2Floyalty"
        if OPT_DIRECT_LOYALTY_REDIRECT
        else "https://www.compraonline.alcampo.es/login?destination=%2F"
    )

    for intento in range(1, intentos_max + 1):
        try:
            if driver is None:
                t0 = time.time()
                driver = init_driver_fn()
                t_chrome += time.time() - t0
            elif intento > 1:
                try:
                    driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
                    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
                except Exception:
                    pass

            t_log0 = time.time()
            try:
                driver.get(login_url)
            except Exception:
                pass
            wait = WebDriverWait(driver, 15)

            try:
                email_field = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
            except Exception as wait_err:
                cur_u = ""
                try:
                    cur_u = driver.current_url
                except Exception:
                    pass
                raise Exception(f"Timeout esperando #uname1 en URL={cur_u[:90]}") from wait_err
            password_field = driver.find_element(By.ID, "pwd1")
            email_field.clear()
            email_field.send_keys(email)
            password_field.clear()
            password_field.send_keys(password)
            _submit_login_form(driver)

            outcome = "pending"
            outcome_msg = ""
            poll_start = time.time()
            while time.time() - poll_start < 14.0:
                outcome, outcome_msg = _check_login_outcome(driver)
                if outcome in ("logged_in", "error"):
                    break
                time.sleep(0.25)

            # Fallback if authenticationError occurred on first redirect: check if session cookies work or retry once
            if outcome == "error" and "authenticationError" in outcome_msg:
                try:
                    driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
                    time.sleep(1.0)
                    if "settings/loyalty" in driver.current_url and "login" not in driver.current_url and "authenticationError" not in driver.current_url:
                        outcome = "logged_in"
                        outcome_msg = ""
                except Exception:
                    pass

            t_login += time.time() - t_log0

            if outcome != "logged_in":
                page_html = ""
                try:
                    page_html = driver.page_source or ""
                except Exception:
                    pass
                if outcome_msg:
                    saldo = outcome_msg
                elif "Tu cuenta ha sido bloqueada" in page_html or "Call Center" in page_html:
                    saldo = "Error: Cuenta bloqueada (Call Center 913 687 857)"
                elif "Usuario o contraseña incorrectos" in page_html or "Credenciales incorrectas" in page_html:
                    saldo = "Error: Credenciales incorrectas"
                else:
                    saldo = "Error: Bloqueo/Timeout"

                err_type, reason = circuit_breaker.classify_error(page_source=page_html, error_msg=saldo)
                print(f"{label_prefix} 🔴 {mask_email(email)} → {saldo} [{err_type}] (login={t_login:.2f}s)")

                # Do not retry permanent account or Call Center errors
                if err_type in ("account_error", "needs_attention"):
                    break
                # If IP/timeout error on attempt 1, clear cookies and retry once after backoff
                if intento < intentos_max:
                    adaptive_pacer.record_pressure(reason or saldo)
                    time.sleep(1.5)
                    continue
                break

            # Logged in: extract loyalty balance
            t_loy0 = time.time()
            saldo = _extract_loyalty_balance(driver, timeout_s=10.0)
            t_loyalty += time.time() - t_loy0

            if "Tu Saldo es" in saldo:
                err_type = "ok"
                total_s = time.time() - t_account_start
                print(
                    f"{label_prefix} ✔ {mask_email(email)} → {saldo} "
                    f"(total={total_s:.2f}s | chrome={t_chrome:.2f}s | login={t_login:.2f}s | saldo={t_loyalty:.2f}s)"
                )
                break
            else:
                saldo = "Error: Saldo no hidratado en DOM"
                err_type = "ip_error"
                if intento < intentos_max:
                    continue

        except Exception as e:
            err_str = str(e).splitlines()[0] if str(e) else "Excepción WebDriver"
            print(f"{label_prefix} ❌ Error en {mask_email(email)} (Intento {intento}/{intentos_max}): {err_str}")
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
            if intento == intentos_max:
                saldo = f"Error: Bloqueo/Timeout ({err_str[:80]})"
                err_type, _ = circuit_breaker.classify_error(error_msg=saldo)

    # Clear browser session via CDP for fast reuse on next account
    if driver:
        try:
            driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
            driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception:
            try:
                driver.quit()
            except Exception:
                pass
            driver = None

    total_s = round(time.time() - t_account_start, 2)
    return driver, {
        "email": email,
        "password": password,
        "saldo": saldo,
        "error_type": err_type,
        "chrome_s": round(t_chrome, 2),
        "login_s": round(t_login, 2),
        "loyalty_s": round(t_loyalty, 2),
        "total_s": total_s
    }

# @end: Core-ScraperEngine


# @section: Worker-Blocks

def procesar_bloque(accounts_chunk, thread_idx, job_start_time=None):
    resultados = []
    driver = None
    job_start = job_start_time or time.time()

    def init_driver():
        nonlocal driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        driver = _create_chrome_driver()
        return driver

    try:
        for idx, acc in enumerate(accounts_chunk):
            if circuit_breaker.triggered:
                print(f"[Hilo {thread_idx}] 🛑 Circuit Breaker activado. Abortando resto del bloque.")
                break
            if (time.time() - job_start) / 60.0 >= MAX_EXECUTION_MINUTES:
                print(f"[Hilo {thread_idx}] ⏱️ Guardarraíl de tiempo ({MAX_EXECUTION_MINUTES} min) alcanzado. Cerrando limpio.")
                break

            if idx > 0 and OPT_ADAPTIVE_PACING:
                adaptive_pacer.wait()

            email = acc["email"]
            password = acc["password"]
            label = f"[Hilo {thread_idx} ({idx+1}/{len(accounts_chunk)})]"

            driver, res_item = _scrape_account_with_driver(driver, init_driver, email, password, label)
            resultados.append(res_item)

            err_type = res_item.get("error_type", "ok")
            if err_type == "ok":
                adaptive_pacer.record_success(res_item.get("total_s", 10.0))
                circuit_breaker.record_result(False, error_type="ok")
            elif err_type == "ip_error":
                adaptive_pacer.record_pressure(res_item.get("saldo", ""))
                triggered, trigger_reason = circuit_breaker.record_result(True, reason=res_item.get("saldo", ""), error_type="ip_error")
                if triggered:
                    print(f"🚨 [CIRCUIT BREAKER DISPARADO] {trigger_reason}. Abortando hilo {thread_idx}.")
                    break
            else:
                # account_error or needs_attention -> not an IP error
                circuit_breaker.record_result(False, error_type=err_type)

            status = "success" if err_type == "ok" else ("needs_attention" if err_type == "needs_attention" else "error")
            update_progress(thread_idx, email, status, res_item["saldo"], worker_name=f"Chunk_{thread_idx}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return resultados


def procesar_bloque_dinamico(worker_name, thread_idx, job_start_time=None):
    resultados = []
    driver = None
    job_start = job_start_time or time.time()

    def init_driver():
        nonlocal driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        driver = _create_chrome_driver()
        return driver

    acc_index = 0
    current_claimed_email = None
    try:
        while True:
            if circuit_breaker.triggered:
                print(f"[{worker_name} Hilo {thread_idx}] 🛑 Circuit Breaker activado. Dejando cuentas restantes en la cola.")
                break
            if (time.time() - job_start) / 60.0 >= MAX_EXECUTION_MINUTES:
                print(f"[{worker_name} Hilo {thread_idx}] ⏱️ Guardarraíl de tiempo ({MAX_EXECUTION_MINUTES} min) alcanzado. Cerrando limpio.")
                break

            acc = claim_account_from_queue(f"{worker_name}_t{thread_idx}")
            if not acc:
                print(f"[{worker_name} Hilo {thread_idx}] 🎉 No quedan más cuentas pendientes en la cola dinámica.")
                break

            current_claimed_email = acc["email"]
            if acc_index > 0 and OPT_ADAPTIVE_PACING:
                adaptive_pacer.wait()

            acc_index += 1
            email = acc["email"]
            password = acc["password"]
            label = f"[{worker_name} Hilo {thread_idx} #{acc_index}]"

            driver, res_item = _scrape_account_with_driver(driver, init_driver, email, password, label)
            err_type = res_item.get("error_type", "ok")

            if err_type == "ok":
                adaptive_pacer.record_success(res_item.get("total_s", 10.0))
                circuit_breaker.record_result(False, error_type="ok")
                resultados.append(res_item)
                update_progress(thread_idx, email, "success", res_item["saldo"], worker_name=worker_name)
                current_claimed_email = None
            elif err_type == "ip_error":
                adaptive_pacer.record_pressure(res_item.get("saldo", ""))
                # Return account to queue (if retries < 2) so another healthy VM can process it
                released = release_account_to_queue(email, reason=res_item.get("saldo", "ip_error"))
                current_claimed_email = None
                if not released:
                    resultados.append(res_item)
                    update_progress(thread_idx, email, "error", res_item["saldo"], worker_name=worker_name)
                triggered, trigger_reason = circuit_breaker.record_result(True, reason=res_item.get("saldo", ""), error_type="ip_error")
                if triggered:
                    print(f"🚨 [CIRCUIT BREAKER DISPARADO] {trigger_reason}. Poniendo {worker_name} en cuarentena.")
                    t_tok, t_chat = get_telegram_config()
                    if t_tok and t_chat:
                        try:
                            enviar_telegram_texto(t_tok, t_chat, f"🚨 <b>ALERTA URGENTE: Circuit Breaker por Bloqueo IP</b>\n\n• Worker: <code>{worker_name} (Hilo {thread_idx})</code>\n• Motivo: {html.escape(trigger_reason)}\n• Acción: Máquina detenida y cuentas devueltas a la cola.")
                        except Exception as e:
                            print(f"⚠️ Error no bloqueante en alerta Circuit Breaker Telegram ({_sanitize_telegram_error(e, t_tok)})")
                    break
            else:
                # Permanent account error or Call Center / password reset (needs_attention)
                circuit_breaker.record_result(False, error_type=err_type)
                resultados.append(res_item)
                st = "needs_attention" if err_type == "needs_attention" else "error"
                update_progress(thread_idx, email, st, res_item["saldo"], worker_name=worker_name)
                current_claimed_email = None
    finally:
        if current_claimed_email:
            try:
                release_account_to_queue(current_claimed_email, reason="worker_timeout_or_abort")
            except Exception:
                pass
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return resultados

# @end: Worker-Blocks


# @section: Main-Orchestrator

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
    cleanup_orphan_chrome()
    
    if args.check_single:
        email, password = args.check_single
        print(f"🔎 Iniciando comprobación de saldo individual para: {mask_email(email)}")
        existing_card = os.environ.get("EXISTING_CARD_NUMBER") or None
        if existing_card:
            print("ℹ️ Número de tarjeta ya conocido, se omitirá el scraping del portal.")
        res = check_single_account(email, password, scrape_card=True, existing_card_number=existing_card)
        print(f"Resultado: status={res.get('status')}, balance={res.get('balance')}, error={res.get('error')}")
        
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
                requests.put(url, json=payload, timeout=10)

                if res["status"] == "success":
                    top_url = firebase_url.strip().rstrip('/') + "/top_accounts.json"
                    top_res = requests.get(top_url, timeout=10)
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
                                requests.put(top_url, json=top_accounts, timeout=10)
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
                            print("✔ top_accounts.json local actualizado.")
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
                    with open(ACCOUNTS_FILE, "w", encoding="utf-8", newline="\r\n") as f:
                        json.dump(accounts, f, indent=2, ensure_ascii=False)
                        f.write("\r\n")
                    print("✔ accounts.json actualizado con número de tarjeta.")
            except Exception as e:
                print(f"Error actualizando accounts.json: {e}")
                
        sys.exit(0 if res["status"] == "success" else 1)
    
    telegram_token, chat_id = get_telegram_config()
    send_telegram = args.send_telegram and not args.no_telegram

    target_accounts_path = Path(args.input_file) if args.input_file else ACCOUNTS_FILE
    if not target_accounts_path.exists():
        b64_env = (os.environ.get("ACCOUNTS_B64") or os.environ.get("ACCOUNTS_BASE64") or "").strip()
        if b64_env and len(b64_env) > 10 and not args.input_file:
            expected_env = int(os.environ.get("EXPECTED_ACCOUNTS_COUNT") or "512")
            accounts = decode_accounts_secret_payload(b64_env, expected_count=expected_env, write_path=ACCOUNTS_FILE)
        elif args.use_queue and not args.init_queue:
            accounts = []
        else:
            print(f"❌ Error: No se encuentra {target_accounts_path}")
            sys.exit(1)
    else:
        with open(target_accounts_path, "r", encoding="utf-8") as f:
            accounts = json.load(f)

    # 1. Modo Inicialización de Cola Dinámica en Firebase
    if args.init_queue:
        print(f"📋 Cargando {len(accounts)} cuentas para inicializar Cola Dinámica en Firebase...")
        init_firebase_queue(accounts)
        sys.exit(0)

    # Startup stagger across shards to prevent simultaneous IP burst
    if args.shard_id is not None and args.shard_id > 0:
        stagger_s = min(15.0, args.shard_id * random.uniform(1.2, 2.2))
        print(f"⏳ [STAGGER] Shard {args.shard_id} esperando {stagger_s:.1f}s para escalonar arranque...")
        time.sleep(stagger_s)

    # IP Canary before claiming any work
    worker_label = f"VM_{args.shard_id}" if args.shard_id is not None else "Worker"
    if OPT_IP_CANARY and not run_ip_canary(worker_label):
        print(f"🛑 [QUARANTINE] {worker_label} descartada por canario IP fallido. Cuentas intactas en la cola.")
        if telegram_token and chat_id:
            try:
                enviar_telegram_texto(telegram_token, chat_id, f"🚨 <b>ALERTA URGENTE: Máquina en Cuarentena por Bloqueo IP</b>\n\n• Worker: <code>{worker_label}</code>\n• Causa: Canario IP detectó bloqueo 403/429/WAF al iniciar.\n• Acción: Cuentas intactas en la cola dinámica para otras VMs sanas.")
            except Exception as e:
                print(f"⚠️ Error no bloqueante en alerta urgente Telegram ({_sanitize_telegram_error(e, telegram_token)})")
        target_excel_path = Path(args.output_file) if args.output_file else EXCEL_FILE
        import pandas as pd
        pd.DataFrame([]).to_excel(target_excel_path, index=False)
        sys.exit(0)

    # 2. Modo Consumo de Cola Dinámica en Firebase (Work-Stealing)
    if args.use_queue:
        num_threads = max(1, min(args.threads, 3))
        print(f"🚀 [COLA DINÁMICA FIREBASE] {worker_label} arrancando {num_threads} hilos dinámicos con ritmo adaptativo...")
        init_progress(len(accounts))
        resultados = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                executor.submit(procesar_bloque_dinamico, worker_label, i + 1, start_time): i
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
        cleanup_orphan_chrome()
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

    init_progress(len(accounts))

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
            print(f"⚠️ Error no bloqueante enviando mensaje inicial a Telegram ({_sanitize_telegram_error(e, telegram_token)})")
            
    resultados = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(procesar_bloque, chunks[i], i + 1, start_time): i
            for i in range(num_threads)
        }
        for future in as_completed(futures):
            resultados.extend(future.result())
            
    end_time = time.time()
    duration = end_time - start_time
    
    import pandas as pd
    target_excel_path = Path(args.output_file) if args.output_file else EXCEL_FILE
    df = pd.DataFrame(resultados)
    df.to_excel(target_excel_path, index=False)
    print(f"\n💾 Resultados guardados en: {target_excel_path}")
    print(f"⏱️ Tiempo total de ejecución: {duration:.2f} segundos ({duration/60:.2f} minutos)")
    
    # Resumen y estadísticas de tiempos
    saldo_total = 0.0
    cuentas_con_saldo = 0
    cuentas_saldo_cero = 0
    cuentas_error = 0
    cuentas_attention = 0
    cuentas_ranked = []
    tiempos = [r.get("total_s", 0.0) for r in resultados if r.get("total_s")]
    avg_s = (sum(tiempos) / len(tiempos)) if tiempos else 0.0
    sorted_t = sorted(tiempos)
    p95_s = sorted_t[min(len(sorted_t) - 1, int(len(sorted_t) * 0.95))] if sorted_t else 0.0
    
    for r in resultados:
        if r.get("error_type") == "needs_attention":
            cuentas_attention += 1
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

    cuentas_ranked.sort(key=lambda x: x[0], reverse=True)
    top_10 = cuentas_ranked[:10]
    
    top_10_text = "\n".join(
        f"   {i+1}. {html.escape(mask_email(email))} ({val:.2f} €)"
        for i, (val, email, _) in enumerate(top_10)
    ) if top_10 else "   N/A"
            
    mensaje_resumen = (
        f"📊 <b>RESUMEN ALCAMPO OPTIMIZADO</b>\n\n"
        f"✅ Cuentas procesadas: {len(resultados)}\n"
        f"⏱️ Tiempo empleado: {duration/60:.2f} min ( media: {avg_s:.1f}s | p95: {p95_s:.1f}s )\n"
        f"💰 <b>Saldo Total:</b> {saldo_total:.2f} €\n"
        f"💎 Cuentas con dinero: {cuentas_con_saldo}\n"
        f"💤 Cuentas con saldo 0: {cuentas_saldo_cero}\n"
        f"⚠️ Cuentas con error/sin saldo: {cuentas_error} (Call Center/Reset: {cuentas_attention})\n\n"
        f"🏆 <b>Top 10 Cuentas:</b>\n{top_10_text}"
    )
    
    print("\n" + mensaje_resumen)
    
    if top_10:
        try:
            card_map = {acc["email"]: acc.get("card_number") for acc in accounts if "email" in acc}
            top_accounts_data = [
                {"email": email, "password": pwd, "balance": val, "card_number": card_map.get(email)}
                for val, email, pwd in top_10
            ]
            if os.environ.get("DISABLE_FIREBASE_SYNC") != "1" and not args.output_file:
                try:
                    top_local_path = ROOT.parent / "docs" / "top_accounts.json"
                    top_local_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(top_local_path, "w", encoding="utf-8") as f:
                        json.dump(top_accounts_data, f, indent=4)
                    print(f"✔ top_accounts.json local guardado en {top_local_path}")
                except Exception as e:
                    print(f"Error escribiendo top_accounts.json local: {e}")

            firebase_url = get_firebase_url()
            if firebase_url:
                url = firebase_url.strip().rstrip('/') + "/top_accounts.json"
                requests.put(url, json=top_accounts_data, timeout=10)
                print("✔ top_accounts.json enviado a Firebase.")
        except Exception as e:
            print(f"Error al exportar Top 10 cuentas: {e}")
    
    if send_telegram:
        try:
            enviar_telegram_texto(telegram_token, chat_id, mensaje_resumen)
            enviar_telegram_documento(
                telegram_token, 
                chat_id, 
                target_excel_path, 
                caption="📊 Reporte de saldos de cuentas Alcampo"
            )
            print("🎉 Proceso completo y enviado a Telegram.")
        except Exception as e:
            print(f"⚠️ Error no bloqueante en notificación final Telegram ({_sanitize_telegram_error(e, telegram_token)})")
    else:
        print("ℹ️ Envío a Telegram desactivado. Usa el script sin --no-telegram para activarlo.")

    cleanup_orphan_chrome()

# @end: Main-Orchestrator

if __name__ == "__main__":
    main()

