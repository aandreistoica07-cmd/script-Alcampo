# -*- coding: utf-8 -*-
"""
Alcampo Scraper - Runner para Google Colab (Ejecución Puntual y Manual)
========================================================================
Reutiliza la lógica validada del scraper (login por #btnSubmit_login con JS click,
redirección directa a /settings/loyalty, ritmo adaptativo, canario de IP,
circuit breaker y cola dinámica en Firebase).

Estructura en 7 secciones equivalentes a las celdas del notebook:
1. Instalación y Entorno
2. Configuración y Modo
3. Secretos y Validación de Cuentas (512)
4. Canario de IP Pública
5. Ejecución con Cola Dinámica (Worker COLAB_1)
6. Guardado Persistente en Google Drive
7. Resumen Final y Notificación Telegram
"""

# @section: Colab-EnvironmentAndInstall

import sys
import os
import re
import time
import json
import base64
import gzip
import random
import shutil
import subprocess
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Asegurar codificación UTF-8 en salida estándar
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def cleanup_orphan_chrome():
    """Limpia procesos Chrome y ChromeDriver huérfanos al arrancar y finalizar."""
    if os.name != "nt":
        try:
            subprocess.run(["pkill", "-9", "-f", "chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["pkill", "-9", "-f", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass


def detect_system_resources():
    """Detecta CPUs y memoria RAM disponible para recomendar número óptimo de hilos."""
    cpus = os.cpu_count() or 2
    ram_gb = 12.0
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    print(f"🖥️ Entorno detectado: {cpus} CPUs | {ram_gb:.1f} GB RAM")
    # En el plan gratuito de Google Colab (típicamente 2 vCPUs y ~12.7 GB RAM):
    # - 2 hilos: ÓPTIMO RECOMENDADO (1 hilo por core, sin contención de CPU y latencia predecible).
    # - 3 hilos: MÁXIMO SEGURO (posible pico de CPU durante arranques simultáneos de Chrome).
    if cpus <= 2:
        recomendacion = 2
    else:
        recomendacion = min(3, cpus)
    print(f"💡 Hilos recomendados para Colab: {recomendacion} hilos (máximo permitido: 3)\n")
    return cpus, ram_gb, recomendacion


def ensure_chrome_and_chromedriver():
    """Verifica e instala Google Chrome y ChromeDriver asegurando versiones mayores idénticas."""
    cleanup_orphan_chrome()
    
    # 1. Comprobar o instalar Google Chrome en sistemas Debian/Ubuntu (Colab)
    if os.name != "nt":
        chrome_exists = shutil.which("google-chrome") or shutil.which("chromium-browser")
        if not chrome_exists:
            print("⬇️ Google Chrome no encontrado. Instalando paquete oficial deb...")
            try:
                subprocess.run(
                    ["wget", "-q", "-O", "/tmp/chrome.deb", "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"],
                    check=True, timeout=90
                )
                subprocess.run(["apt-get", "update", "-qq"], check=True, timeout=60)
                subprocess.run(["apt-get", "install", "-y", "-qq", "/tmp/chrome.deb"], check=True, timeout=120)
                if os.path.exists("/tmp/chrome.deb"):
                    os.remove("/tmp/chrome.deb")
                print("✔ Google Chrome instalado con éxito.")
            except Exception as e:
                raise RuntimeError(f"❌ Fallo instalando Google Chrome en Colab: {e}")

    # 2. Obtener versión mayor de Google Chrome
    v_chrome = None
    chrome_cmd = "google-chrome" if shutil.which("google-chrome") else ("chromium-browser" if shutil.which("chromium-browser") else None)
    if chrome_cmd:
        try:
            out = subprocess.check_output([chrome_cmd, "--version"], text=True)
            m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
            if m:
                v_chrome = int(m.group(1))
                print(f"🌐 Google Chrome detectado: v{v_chrome} ({out.strip()})")
        except Exception as e:
            print(f"⚠️ Advertencia al consultar versión de Chrome: {e}")

    # 3. Resolver ChromeDriver y comprobar versión mayor
    v_driver = None
    driver_path = shutil.which("chromedriver")
    if not driver_path:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
        except Exception:
            pass

    if driver_path and os.path.exists(driver_path):
        try:
            out_d = subprocess.check_output([driver_path, "--version"], text=True)
            m_d = re.search(r"(\d+)\.\d+\.\d+\.\d+", out_d)
            if m_d:
                v_driver = int(m_d.group(1))
                print(f"🚗 ChromeDriver detectado: v{v_driver} ({out_d.strip()})")
        except Exception as e:
            print(f"⚠️ Advertencia al consultar versión de ChromeDriver: {e}")

    # 4. Validación estricta de versión mayor
    if v_chrome and v_driver:
        if v_chrome != v_driver:
            raise RuntimeError(
                f"❌ ERROR CRÍTICO DE ENTORNO: Desajuste de versión mayor entre Google Chrome (v{v_chrome}) "
                f"y ChromeDriver (v{v_driver}). Se requiere la misma versión mayor para evitar fallos de sesión."
            )
        print(f"✅ Versiones sincronizadas: Chrome v{v_chrome} y ChromeDriver v{v_driver} coinciden.")
    else:
        print("ℹ️ Selenium Manager gestionará automáticamente la descarga del ChromeDriver coincidente.")

# @end: Colab-EnvironmentAndInstall


# @section: Colab-Configuration

# Variables de Configuración de la Sesión en Colab
MODO = "continuar"             # "nueva": reinicia cola (con backup previo) | "continuar": reanuda cuentas pendientes
HILOS = 2                      # 2 recomendado (óptimo para 2 vCPUs de Colab), máximo 3
TEST_LIMIT = None              # None = 512 completas | 4 = Nivel 1 (saldo conocido) | 25 = Nivel 2
GUARDAR_CADA_N = 10            # Guarda checkpoint en Drive cada N cuentas procesadas
DRIVE_MOUNT = True             # True: guardar resultados directamente en Google Drive
DRIVE_FOLDER = "/content/drive/MyDrive/Alcampo_Resultados"
MAX_HOURS = 11.0               # Límite preventivo propio (~11h) antes del corte de runtime de Colab


def setup_drive_storage(enabled=True, folder_path="/content/drive/MyDrive/Alcampo_Resultados"):
    """Monta Google Drive si está habilitado y prepara el directorio de guardado persistente."""
    if not enabled:
        local_dir = Path("/content/resultados")
        local_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Almacenamiento local activado: {local_dir}")
        return local_dir

    try:
        from google.colab import drive
        drive_root = Path("/content/drive")
        if not (drive_root / "MyDrive").exists():
            print("🔄 Montando Google Drive para persistencia de resultados...")
            drive.mount("/content/drive")
        
        target = Path(folder_path)
        target.mkdir(parents=True, exist_ok=True)
        print(f"✔ Carpeta persistente de Drive lista: {target}")
        return target
    except Exception as e:
        fallback = Path("./resultados_colab")
        fallback.mkdir(parents=True, exist_ok=True)
        print(f"⚠️ No se pudo montar Drive ({e}). Usando carpeta local de respaldo: {fallback}")
        return fallback

# @end: Colab-Configuration


# @section: Colab-SecretsAndData

def get_secret(key, default=None):
    """Obtiene un secreto de Colab Secrets (google.colab.userdata) o de variables de entorno."""
    try:
        from google.colab import userdata
        val = userdata.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get(key, default)


def mask_email(email):
    """Enmascara correos para evitar exponer PII en salidas de consola."""
    if not email or "@" not in str(email):
        return "***"
    local, domain = str(email).split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***{local[-1]}@{domain}"


def mask_ip(ip_str):
    """Enmascara una dirección IP pública (ej. 34.123.***.***)."""
    if not ip_str or "." not in ip_str:
        return "***.***.***.***"
    parts = ip_str.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return f"{ip_str[:len(ip_str)//2]}***"


def locate_or_clone_repository(github_token=None, repo_slug=None):
    """Verifica la existencia del repositorio o lo clona en /content/script-Alcampo usando token."""
    # 1. Si ya estamos dentro del directorio del repo
    if Path("./script_alcampo_activacion telegram").exists():
        repo_dir = Path(".").resolve()
        script_dir = repo_dir / "script_alcampo_activacion telegram"
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        return repo_dir

    # 2. Si ya está clonado en /content/script-Alcampo
    colab_repo = Path("/content/script-Alcampo")
    if (colab_repo / "script_alcampo_activacion telegram").exists():
        script_dir = colab_repo / "script_alcampo_activacion telegram"
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        return colab_repo

    # 3. Clonar con GITHUB_TOKEN si está disponible
    if github_token:
        slug = repo_slug or os.environ.get("GITHUB_REPOSITORY") or "aandreistoica07-cmd/script-Alcampo"
        clone_url = f"https://x-access-token:{github_token}@github.com/{slug}.git"
        print("📦 Clonando repositorio privado en /content/script-Alcampo...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", clone_url, str(colab_repo)], check=True, timeout=45)
            script_dir = colab_repo / "script_alcampo_activacion telegram"
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))
            print("✔ Repositorio clonado correctamente.")
            return colab_repo
        except Exception as e:
            print(f"⚠️ Advertencia al clonar con git ({e}).")

    return None


def load_and_validate_accounts(secret_b64, expected_count=512, drive_backup_file=None):
    """
    Decodifica ACCOUNTS_BASE64 (soporta Gzip+Base64 y Base64 plano).
    Valida estrictamente que contenga exactamente expected_count (512) cuentas.
    Si el secreto no cabe o está vacío, intenta leer desde un archivo privado en Drive.
    """
    raw_bytes = None
    cleaned = (secret_b64 or "").strip()

    if cleaned:
        try:
            raw_bytes = base64.b64decode(cleaned)
        except Exception as e:
            raise ValueError(f"❌ Fallo decodificando Base64 en ACCOUNTS_BASE64: {e}")
        
        # Descomprimir si es Gzip (0x1f 0x8b)
        if len(raw_bytes) >= 2 and raw_bytes[0] == 0x1F and raw_bytes[1] == 0x8B:
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except Exception as e:
                raise ValueError(f"❌ Fallo descomprimiendo Gzip en ACCOUNTS_BASE64: {e}")

    # Fallback a archivo en Google Drive o /content si no vino por secreto
    backup_rutas = [
        drive_backup_file,
        "/content/drive/MyDrive/Alcampo_Resultados/accounts.json",
        "/content/drive/MyDrive/accounts.json",
        "/content/accounts.json"
    ]
    for r in backup_rutas:
        if (not raw_bytes or len(raw_bytes) < 10) and r and Path(r).exists():
            print(f"📂 Cargando cuentas desde archivo: {r}")
            raw_bytes = Path(r).read_bytes()
            break

    if not raw_bytes:
        raise ValueError(
            "❌ ERROR CRÍTICO: No se proporcionaron cuentas en Colab Secrets (ACCOUNTS_BASE64) "
            "ni se encontró archivo 'accounts.json' en Drive ni en /content."
        )

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"❌ El contenido de cuentas no es un JSON UTF-8 válido: {e}")

    if not isinstance(data, list):
        raise ValueError("❌ El JSON de cuentas no contiene una lista de objetos.")

    total_cuentas = len(data)
    if expected_count is not None and total_cuentas != expected_count:
        raise ValueError(
            f"❌ ERROR DE VALIDACIÓN: Se esperaban exactamente {expected_count} cuentas, "
            f"pero el dataset decodificado contiene {total_cuentas} cuentas."
        )

    print(f"✔ Dataset validado con éxito: {total_cuentas} cuentas cargadas (integridad 100%).")
    return data

# @end: Colab-SecretsAndData


# @section: Colab-IPCanary

def get_public_ip():
    """Obtiene la IP pública de la máquina de Colab."""
    import requests
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]
    for url in services:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and r.text.strip():
                return r.text.strip()
        except Exception:
            pass
    return "0.0.0.0"


def run_colab_ip_canary():
    """
    Ejecuta el canario de IP al arrancar.
    Muestra la IP pública enmascarada y prueba conexión con el portal de Alcampo.
    Si detecta bloqueo Cloudflare/403/429, detiene la ejecución inmediatamente sin gastar cuentas.
    """
    import requests
    ip_raw = get_public_ip()
    ip_masked = mask_ip(ip_raw)
    print(f"🌐 IP Pública asignada por Colab: {ip_masked}")

    url_test = "https://www.compraonline.alcampo.es/login"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        res = requests.get(url_test, headers=headers, timeout=12)
        if res.status_code in (403, 429, 503):
            print(f"🐤 [CANARIO IP] ❌ BLOQUEO DETECTADO: HTTP {res.status_code} desde IP {ip_masked}.")
            print("🛑 ACCIÓN REQUERIDA:")
            print("   La IP de centro de datos asignada por Google Colab está bloqueada por Alcampo.")
            print("   1. Ve al menú superior de Colab: 'Entorno de ejecución' -> 'Desconectar y eliminar entorno de ejecución'.")
            print("   2. Vuelve a ejecutar todo para obtener una nueva máquina con otra IP.")
            return False, ip_masked

        body_low = res.text[:4000].lower()
        if "blocked by cloudflare" in body_low or "access denied" in body_low or "challenge-platform" in body_low:
            print(f"🐤 [CANARIO IP] ❌ BLOQUEO CLOUDFLARE/WAF DETECTADO desde IP {ip_masked}.")
            print("🛑 ACCIÓN REQUERIDA: Reinicia el entorno de ejecución en Colab para cambiar de IP.")
            return False, ip_masked

        print(f"🐤 [CANARIO IP] ✔ Conexión limpia con Alcampo (HTTP {res.status_code}). IP {ip_masked} autorizada.")
        return True, ip_masked
    except Exception as e:
        print(f"🐤 [CANARIO IP] ⚠️ Advertencia de red en canario ({e}). Continuando con precaución...")
        return True, ip_masked

# @end: Colab-IPCanary


# @section: Colab-CoreExecution

def backup_firebase_state(firebase_url, output_dir):
    """
    Descarga una copia de seguridad completa del estado actual de Firebase Realtime DB
    (/queue, /results, /progress) antes de reiniciar la cola.
    """
    import requests
    url = firebase_url.strip().rstrip('/')
    backup = {
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queue": None,
        "results": None,
        "progress": None
    }
    for node in ["queue", "results", "progress"]:
        try:
            r = requests.get(f"{url}/{node}.json", timeout=10)
            if r.status_code == 200:
                backup[node] = r.json()
        except Exception as e:
            backup[node] = {"error": str(e)}

    ts_str = time.strftime("%Y%m%d_%H%M%S")
    backup_file = Path(output_dir) / f"firebase_backup_{ts_str}.json"
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    print(f"💾 [FIREBASE BACKUP] Copia de seguridad guardada en: {backup_file}")
    return backup_file


def init_colab_queue(firebase_url, accounts):
    """Inicializa la cola compartida en Firebase Realtime DB para una ejecución nueva."""
    import requests
    url = firebase_url.strip().rstrip('/')
    now = time.time()
    queue_data = {}
    for acc in accounts:
        key = acc["email"].replace('.', '_').replace('@', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_')
        queue_data[key] = {
            "email": acc["email"],
            "password": acc["password"],
            "status": "pending",
            "claimed_by": None,
            "retries": 0,
            "timestamp": now
        }
    requests.put(f"{url}/queue.json", json=queue_data, timeout=12)
    requests.delete(f"{url}/results.json", timeout=12)
    requests.delete(f"{url}/threads.json", timeout=12)
    init_progress = {
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
    requests.put(f"{url}/progress.json", json=init_progress, timeout=12)
    print(f"📦 [COLA INICIALIZADA] {len(accounts)} cuentas registradas en Firebase /queue.")


def recover_in_flight_accounts(firebase_url):
    """
    Para modo 'continuar': devuelve las cuentas con estado 'in_progress' o leases vencidos
    a 'pending' con claimed_by=None, respetando las cuentas ya completadas exitosamente.
    """
    import requests
    url = firebase_url.strip().rstrip('/')
    res = requests.get(f"{url}/queue.json", timeout=10)
    if not res.ok or not isinstance(res.json(), dict):
        print("⚠️ No se encontró cola activa en Firebase para reanudar.")
        return 0, 0, 0

    queue = res.json()
    res_node = requests.get(f"{url}/results.json", timeout=10)
    completed_keys = set(res_node.json().keys()) if res_node.ok and isinstance(res_node.json(), dict) else set()

    recovered = 0
    already_ok = 0
    pending = 0
    now = time.time()

    for key, item in queue.items():
        if not isinstance(item, dict):
            continue
        st = item.get("status")
        if key in completed_keys or st == "success":
            already_ok += 1
        elif st == "in_progress":
            item["status"] = "pending"
            item["claimed_by"] = None
            item["lease_until"] = None
            item["timestamp"] = now
            requests.put(f"{url}/queue/{key}.json", json=item, timeout=8)
            recovered += 1
            pending += 1
        elif st == "pending":
            pending += 1

    print(f"🔄 [REANUDACIÓN COLA] Cuentas ya completadas: {already_ok} | En vuelo recuperadas: {recovered} | Pendientes: {pending}")
    return already_ok, recovered, pending


def run_colab_orchestrator(
    firebase_url,
    accounts,
    output_dir,
    modo="continuar",
    threads=2,
    max_hours=11.0,
    save_every_n=10,
    telegram_token=None,
    telegram_chat_id=None
):
    """
    Orquestador principal para Google Colab:
    - Worker ID: COLAB_1
    - Hilos dinámicos: 2 (por defecto, máx 3)
    - Reutilización del motor de scraping validado en script_optimizado.py
    - Autoguardado periódico en Google Drive
    - Guardarraíl de ~11 horas
    """
    import requests
    import pandas as pd
    try:
        import script_optimizado as engine
    except ImportError:
        # Fallback si se ejecuta desde raíz o módulo
        from importlib import import_module
        engine = import_module("script_optimizado")

    worker_label = "COLAB_1"
    num_threads = max(1, min(int(threads), 3))
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Preparar la cola según el modo
    if modo == "nueva":
        backup_firebase_state(firebase_url, output_dir)
        init_colab_queue(firebase_url, accounts)
    else:
        recover_in_flight_accounts(firebase_url)

    # 2. Cargar resultados previos si existen para no perder progreso
    prog_excel = out_path / "alcampo_saldos_progreso.xlsx"
    prog_json = out_path / "results.json"
    resultados_totales = []
    if modo == "continuar" and prog_json.exists():
        try:
            with open(prog_json, "r", encoding="utf-8") as f:
                resultados_totales = json.load(f)
            print(f"📖 Cargados {len(resultados_totales)} resultados previos desde Drive.")
        except Exception:
            pass

    print(f"\n🚀 [WORKER {worker_label}] Iniciando ejecución con {num_threads} hilos dinámicos...")
    print(f"⏱️ Guardarraíl de tiempo activo: máximo {max_hours:.1f} horas.\n")

    start_time = time.time()
    results_lock = threading.Lock()
    active_in_flight = {}

    def worker_thread(thread_idx):
        driver = None
        acc_count = 0
        current_email = None

        def init_driver():
            nonlocal driver
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            driver = engine._create_chrome_driver()
            return driver

        try:
            while True:
                # Comprobar Circuit Breaker global
                if engine.circuit_breaker.triggered:
                    print(f"[{worker_label} t{thread_idx}] 🛑 Circuit Breaker activado ({engine.circuit_breaker.trigger_reason}). Deteniendo hilo.")
                    break

                # Comprobar Guardarraíl de 11h
                elapsed_h = (time.time() - start_time) / 3600.0
                if elapsed_h >= max_hours:
                    print(f"[{worker_label} t{thread_idx}] ⏱️ Límite de tiempo de Colab ({max_hours:.1f}h) alcanzado. Cerrando limpiamente...")
                    break

                # Reclamar cuenta de la cola dinámica
                worker_tid = f"{worker_label}_t{thread_idx}"
                acc = engine.claim_account_from_queue(worker_tid)
                if not acc:
                    print(f"[{worker_label} t{thread_idx}] 🎉 No quedan más cuentas pendientes en la cola.")
                    break

                current_email = acc["email"]
                with results_lock:
                    active_in_flight[thread_idx] = current_email

                # Ritmo adaptativo con jitter entre cuentas
                if acc_count > 0 and engine.OPT_ADAPTIVE_PACING:
                    engine.adaptive_pacer.wait()

                acc_count += 1
                email = acc["email"]
                password = acc["password"]
                label = f"[{worker_label} t{thread_idx} #{acc_count}]"

                # Ejecutar scraping con reutilización de navegador
                driver, res_item = engine._scrape_account_with_driver(driver, init_driver, email, password, label)
                err_type = res_item.get("error_type", "ok")

                if err_type == "ok":
                    engine.adaptive_pacer.record_success(res_item.get("total_s", 10.0))
                    engine.circuit_breaker.record_result(False, error_type="ok")
                    with results_lock:
                        resultados_totales.append(res_item)
                        active_in_flight.pop(thread_idx, None)
                    current_email = None
                    engine.update_progress(thread_idx, email, "success", res_item["saldo"], worker_name=worker_label)
                elif err_type == "ip_error":
                    engine.adaptive_pacer.record_pressure(res_item.get("saldo", ""))
                    # Devolver cuenta a la cola si retries < 2
                    released = engine.release_account_to_queue(email, reason=res_item.get("saldo", "ip_error"))
                    with results_lock:
                        active_in_flight.pop(thread_idx, None)
                    current_email = None
                    if not released:
                        with results_lock:
                            resultados_totales.append(res_item)
                        engine.update_progress(thread_idx, email, "error", res_item["saldo"], worker_name=worker_label)
                    
                    triggered, trigger_reason = engine.circuit_breaker.record_result(True, reason=res_item.get("saldo", ""), error_type="ip_error")
                    if triggered:
                        print(f"🚨 [CIRCUIT BREAKER] {trigger_reason}. Poniendo {worker_label} en pausa.")
                        break
                else:
                    # Error permanente de credenciales (account_error) o bloqueo humano (needs_attention)
                    engine.circuit_breaker.record_result(False, error_type=err_type)
                    with results_lock:
                        resultados_totales.append(res_item)
                        active_in_flight.pop(thread_idx, None)
                    current_email = None
                    st = "needs_attention" if err_type == "needs_attention" else "error"
                    engine.update_progress(thread_idx, email, st, res_item["saldo"], worker_name=worker_label)

                # Autoguardado periódico en Drive cada save_every_n cuentas
                with results_lock:
                    count_now = len(resultados_totales)
                if count_now > 0 and count_now % save_every_n == 0:
                    with results_lock:
                        snapshot = list(resultados_totales)
                    try:
                        pd.DataFrame(snapshot).to_excel(prog_excel, index=False)
                        with open(prog_json, "w", encoding="utf-8") as f:
                            json.dump(snapshot, f, indent=2, ensure_ascii=False)
                        print(f"💾 [AUTO-GUARDADO] Progreso ({count_now} cuentas) guardado en Drive.")
                    except Exception as e:
                        print(f"⚠️ Error en auto-guardado ({e})")

        finally:
            if current_email:
                try:
                    engine.release_account_to_queue(current_email, reason="worker_abort_or_timeout")
                except Exception:
                    pass
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    # Lanzar pool de hilos
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_thread, i + 1) for i in range(num_threads)]
        for f in as_completed(futures):
            f.result()

    duration = time.time() - start_time
    cleanup_orphan_chrome()
    return resultados_totales, duration

# @end: Colab-CoreExecution


# @section: Colab-ResultsPersistence

def save_final_results(resultados, output_dir):
    """Guarda los archivos finales de resultados en Excel y JSON en Google Drive."""
    import pandas as pd
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    excel_final = out_path / "alcampo_saldos_final.xlsx"
    json_final = out_path / "results.json"

    # Exportar Excel
    df = pd.DataFrame(resultados)
    df.to_excel(excel_final, index=False)

    # Exportar JSON
    with open(json_final, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Resultados finales consolidados en:")
    print(f"   • Excel: {excel_final}")
    print(f"   • JSON:  {json_final}")
    return excel_final, json_final

# @end: Colab-ResultsPersistence


# @section: Colab-SummaryAndReporting

def limpiar_saldo(saldo_str):
    """Extrae el valor numérico del saldo en formato float."""
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


def generate_and_display_summary(
    resultados,
    duration_s,
    telegram_token=None,
    telegram_chat_id=None,
    excel_path=None
):
    """
    Genera la tabla final con conteo OK / needs_attention / account_error / ip_error,
    saldo total, Top 10 cuentas y tiempos, enviando notificación a Telegram en try/except.
    """
    total = len(resultados)
    ok_count = sum(1 for r in resultados if r.get("error_type") == "ok")
    attention_count = sum(1 for r in resultados if r.get("error_type") == "needs_attention")
    account_err_count = sum(1 for r in resultados if r.get("error_type") == "account_error")
    ip_err_count = sum(1 for r in resultados if r.get("error_type") == "ip_error")

    tiempos = [r.get("total_s", 0.0) for r in resultados if r.get("total_s")]
    avg_s = (sum(tiempos) / len(tiempos)) if tiempos else 0.0
    sorted_t = sorted(tiempos)
    p95_s = sorted_t[min(len(sorted_t) - 1, int(len(sorted_t) * 0.95))] if sorted_t else 0.0

    saldo_total = 0.0
    cuentas_con_dinero = []
    saldo_cero = 0

    for r in resultados:
        val = limpiar_saldo(r.get("saldo"))
        if val is not None:
            saldo_total += val
            if val > 0:
                cuentas_con_dinero.append((val, r.get("email", "")))
            elif val == 0.0 and r.get("error_type") == "ok":
                saldo_cero += 1

    cuentas_con_dinero.sort(key=lambda x: x[0], reverse=True)
    top_10 = cuentas_con_dinero[:10]

    top_10_str = "\n".join(
        f"   {i+1}. {mask_email(email)}: {val:.2f} €"
        for i, (val, email) in enumerate(top_10)
    ) if top_10 else "   (Sin cuentas con saldo > 0)"

    tabla_resumen = (
        f"\n======================================================================\n"
        f"📊 RESUMEN FINAL EJECUCIÓN GOOGLE COLAB (Worker: COLAB_1)\n"
        f"======================================================================\n"
        f"• Total Cuentas Procesadas: {total}\n"
        f"• Clasificación de Estados:\n"
        f"    ✅ OK (Éxito):                           {ok_count}\n"
        f"    🟡 Needs Attention (Call Center / Reset): {attention_count}\n"
        f"    🔴 Account Error (Credenciales erróneas): {account_err_count}\n"
        f"    ⚠️ IP Error (Bloqueo / Red / Timeout):    {ip_err_count}\n"
        f"----------------------------------------------------------------------\n"
        f"• Saldo Total Acumulado: {saldo_total:.2f} €\n"
        f"    💎 Con dinero (> 0 €): {len(cuentas_con_dinero)}\n"
        f"    💤 Saldo cero (0.00 €): {saldo_cero}\n"
        f"• Tiempos de Ejecución:\n"
        f"    ⏱️ Duración Total: {duration_s/60:.2f} min ({duration_s:.1f} s)\n"
        f"    ⚡ Media por cuenta: {avg_s:.2f} s | p95: {p95_s:.2f} s\n"
        f"----------------------------------------------------------------------\n"
        f"🏆 Top 10 Cuentas con Mayor Saldo:\n{top_10_str}\n"
        f"======================================================================\n"
    )

    print(tabla_resumen)

    # Notificación a Telegram protegida contra fallos
    if telegram_token and telegram_chat_id:
        try:
            import html
            import requests
            tg_text = (
                f"📊 <b>RESUMEN ALCAMPO - GOOGLE COLAB (COLAB_1)</b>\n\n"
                f"• Total Procesadas: <b>{total}</b>\n"
                f"• ✅ OK: <b>{ok_count}</b>\n"
                f"• 🟡 Needs Attention: <b>{attention_count}</b>\n"
                f"• 🔴 Account Error: <b>{account_err_count}</b>\n"
                f"• ⚠️ IP Error: <b>{ip_err_count}</b>\n\n"
                f"💰 <b>Saldo Total:</b> <code>{saldo_total:.2f} €</code>\n"
                f"⏱️ <b>Tiempo:</b> {duration_s/60:.2f} min (media: {avg_s:.1f}s | p95: {p95_s:.1f}s)\n\n"
                f"🏆 <b>Top Cuentas:</b>\n" +
                ("\n".join(f"• <code>{mask_email(em)}</code>: {v:.2f} €" for v, em in top_10[:5]) if top_10 else "• Ninguna")
            )
            api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            requests.post(api_url, json={"chat_id": telegram_chat_id, "text": tg_text, "parse_mode": "HTML"}, timeout=15)
            
            if excel_path and Path(excel_path).exists():
                doc_url = f"https://api.telegram.org/bot{telegram_token}/sendDocument"
                with open(excel_path, "rb") as f:
                    requests.post(doc_url, data={"chat_id": telegram_chat_id, "caption": "📊 Reporte Excel Alcampo Colab"}, files={"document": f}, timeout=30)
            print("✔ Resumen y reporte enviados a Telegram.")
        except Exception as tg_err:
            print(f"⚠️ Error no bloqueante al enviar a Telegram ({tg_err}). La ejecución finalizó correctamente.")

# @end: Colab-SummaryAndReporting
