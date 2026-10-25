#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Test Runner for Alcampo Scraper
-------------------------------------
Standalone CLI tool for testing single or batch accounts locally with step-by-step
console instrumentation, headful/headless browser modes, and zero external dependencies
on GitHub Actions or Firebase RTDB.
"""

import os
import sys
import time
import re
import argparse
import json
from pathlib import Path
from datetime import datetime

# Configure standard streams for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure repository root and scraper directory are importable
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
SCRAPER_DIR = ROOT_DIR / "scraper"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRAPER_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPER_DIR))

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    webdriver = None

from scraper.script_optimizado import (
    create_stealth_driver,
    mask_email,
    limpiar_saldo,
    CircuitBreaker,
    _verify_and_hydrate_session,
    _extract_loyalty_balance,
    _handle_pwreset_relogin,
    capture_screenshot,
)


def extraer_tarjeta(html_content):
    """Extrae el número de tarjeta Alcampo (13 dígitos) desde el código fuente HTML."""
    if not html_content or not str(html_content).strip():
        return None
    try:
        # 1. Canvas o parámetro query clif (?clif=4003009301402)
        m = re.search(r'[?&]clif=(400\d{10}|280\d{10})', html_content)
        if m:
            return m.group(1).strip()

        # 2. Selector específico de clase Sana Sans / S1 Subtitle de Alcampo
        m = re.search(r'class="[^"]*(?:sana-sans-alt|s1-subtitle)[^"]*">\s*(?:&nbsp;|\s)*(400\d{10}|280\d{10})\s*(?:&nbsp;|\s)*</(?:span|div|p)>', html_content)
        if m:
            return m.group(1).strip()

        # 3. Claves JSON en __NEXT_DATA__ o scripts
        m = re.search(r'"(?:cardNumber|loyaltyCardNumber|barcode|loyaltyNumber)"\s*:\s*"(400\d{10}|280\d{10})"', html_content)
        if m:
            return m.group(1).strip()

        # 4. En elementos HTML delimitados cerrados por etiqueta de cierre o entidad (</tag> o &lt;)
        m = re.search(r'(?:>|&gt;)\s*(?:&nbsp;|\s)*(400200\d{7}|400300\d{7}|400\d{10}|280\d{10})\s*(?:&nbsp;|\s)*(?:</|&lt;)', html_content)
        if m:
            return m.group(1).strip()

        # 5. En texto plano contextualizado por mención de tarjeta / club
        m = re.search(r'(?:tarjeta|asociad[oa]|club)\D{1,30}\b(400200\d{7}|400300\d{7}|400\d{10}|280\d{10})\b', html_content, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None


OAUTH_DESTINATION_URL = "https://www.compraonline.alcampo.es/login?destination=%2Fsettings%2Floyalty"
LOYALTY_SETTINGS_URL = "https://www.compraonline.alcampo.es/settings/loyalty"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="🛒 Alcampo Scraper - Herramienta CLI de Pruebas Locales (Standalone)"
    )
    # Account input
    parser.add_argument("--email", type=str, help="Correo de la cuenta a probar")
    parser.add_argument("--password", type=str, help="Contraseña de la cuenta a probar")
    parser.add_argument(
        "--input-file",
        type=str,
        help="Ruta a archivo de cuentas (.json, .xlsx, .csv) para prueba por lotes",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Límite máximo de cuentas a procesar desde el archivo de entrada",
    )

    # Browser visibility
    parser.add_argument(
        "--headful",
        "--visible",
        action="store_true",
        dest="visible",
        help="Ejecutar Chrome en modo visible (GUI en ventana interactiva)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Forzar ejecución headless (por defecto, a menos que se indique --headful/--visible)",
    )

    # Timing & Debugging
    parser.add_argument(
        "--slowmo",
        type=float,
        default=0.0,
        help="Pausa en segundos entre pasos para inspección visual paso a paso (ej: --slowmo 1.5)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=25,
        help="Tiempo máximo de espera para elementos y redirecciones en segundos (default: 25)",
    )

    # Output
    parser.add_argument(
        "--output-excel",
        type=str,
        default=None,
        help="Ruta de archivo Excel (.xlsx) donde guardar los resultados de la prueba",
    )
    parser.add_argument(
        "--screenshot-dir",
        type=str,
        default="screenshots",
        help="Directorio donde guardar capturas de pantalla automáticas ante errores o confirmaciones de saldo",
    )

    return parser.parse_args()


def load_accounts_from_file(file_path, limit=None):
    """Carga credenciales desde JSON, Excel (.xlsx) o CSV."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo de cuentas no encontrado: {file_path}")

    accounts = []
    suffix = p.suffix.lower()

    if suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                accounts = data
            elif isinstance(data, dict):
                # En caso de diccionario con lista en alguna clave
                for v in data.values():
                    if isinstance(v, list):
                        accounts = v
                        break
    elif suffix in (".xlsx", ".xls"):
        if pd is None:
            raise RuntimeError("pandas y openpyxl requeridos para leer archivos Excel.")
        df = pd.read_excel(p)
        accounts = df.to_dict(orient="records")
    elif suffix == ".csv":
        if pd is None:
            raise RuntimeError("pandas requerido para leer archivos CSV.")
        df = pd.read_csv(p)
        accounts = df.to_dict(orient="records")
    else:
        raise ValueError(f"Formato no soportado: {suffix} (use .json, .xlsx, o .csv)")

    # Normalizar claves a 'email' y 'password'
    normalized = []
    for item in accounts:
        em = item.get("email") or item.get("usuario") or item.get("user") or item.get("Email")
        pw = item.get("password") or item.get("contraseña") or item.get("pass") or item.get("Password")
        if em and pw:
            normalized.append({"email": str(em).strip(), "password": str(pw).strip()})

    if limit is not None and limit > 0:
        normalized = normalized[:limit]

    return normalized


def capture_screenshot(driver, email, label, screenshot_dir="screenshots"):
    """Guarda una captura de pantalla fechada para auditoría visual forense."""
    if not driver:
        return None
    try:
        if not hasattr(driver, "save_screenshot"):
            return None
        os.makedirs(screenshot_dir, exist_ok=True)
        safe_email = re.sub(r'[^a-zA-Z0-9]', '_', str(email) if email else "anon")[:48]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot_path = os.path.join(screenshot_dir, f"{safe_email}_{label}_{ts}.png")
        driver.save_screenshot(shot_path)
        print(f"            📸 [CAPTURA GUARDADA] {shot_path}")
        return shot_path
    except Exception as e:
        print(f"            ⚠️ No se pudo guardar captura: {e}")
        return None


def test_single_account(driver, email, password, timeout=25, slowmo=0.0, screenshot_dir="screenshots"):
    """
    Ejecuta el ciclo de autenticación y extracción paso a paso con registro detallado en consola.
    Retorna un diccionario con el resultado.
    """
    start_time = time.time()
    masked = mask_email(email)
    cb = CircuitBreaker()

    print("\n" + "=" * 70)
    print(f"▶ [TEST START] Probando cuenta: {masked}")
    print("=" * 70)

    result = {
        "email": email,
        "masked_email": masked,
        "password": password,
        "status": "pending",
        "balance": None,
        "balance_str": None,
        "card_number": None,
        "error_type": None,
        "error_reason": None,
        "duration": 0.0,
    }

    try:
        # Paso 1: Navegación al destino OAuth
        print(f" [Paso 1/6] Navegando a OAuth destino:")
        print(f"            {OAUTH_DESTINATION_URL}")
        driver.get(OAUTH_DESTINATION_URL)
        if slowmo > 0:
            time.sleep(slowmo)

        # Paso 2: Detección del formulario de Salesforce
        print(f" [Paso 2/6] Esperando formulario de autenticación Salesforce (#uname1, #pwd1)...")
        wait = WebDriverWait(driver, timeout)
        try:
            uname_input = wait.until(EC.presence_of_element_located((By.ID, "uname1")))
            pwd_input = wait.until(EC.presence_of_element_located((By.ID, "pwd1")))
            print(f"            ✔ Campos de login detectados correctamente en el DOM.")
        except Exception as e:
            # Capturar posibles firmas de Cloudflare, rate limiting o bloqueo
            page_src = driver.page_source or ""
            err_type, err_reason = cb.classify_error(page_source=page_src, error_msg=str(e))
            result["status"] = "failed"
            result["error_type"] = err_type
            result["error_reason"] = f"Timeout esperando inputs de login ({err_reason})"
            print(f"            ❌ Fallo detectando inputs: {result['error_reason']}")
            if err_type == "ip_error" or any(k in page_src.lower() for k in ["cloudflare", "ray id", "challenge-platform", "access denied", "blocked by cloudflare", "waf", "too many requests"]):
                capture_screenshot(driver, email, "err_waf", screenshot_dir)
            else:
                capture_screenshot(driver, email, "err_inputs", screenshot_dir)
            result["duration"] = round(time.time() - start_time, 2)
            return result

        # Paso 3: Inyección de credenciales
        print(f" [Paso 3/6] Inyectando credenciales para {masked}...")
        uname_input.clear()
        uname_input.send_keys(email)
        pwd_input.clear()
        pwd_input.send_keys(password)
        if slowmo > 0:
            time.sleep(slowmo)

        # Paso 4: Clic en botón submit mediante JS para evitar bloqueo Visualforce noenter
        print(f" [Paso 4/6] Localizando #btnSubmit_login y disparando clic vía JS...")
        try:
            submit_btn = driver.find_element(By.ID, "btnSubmit_login")
            driver.execute_script("arguments[0].click();", submit_btn)
            print(f"            ✔ Clic disparado exitosamente en #btnSubmit_login.")
        except Exception as e:
            # Fallback buscando botón type=submit
            print(f"            ⚠️ #btnSubmit_login no encontrado directamente, buscando fallback...")
            submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            driver.execute_script("arguments[0].click();", submit_btn)
            print(f"            ✔ Clic disparado mediante selector fallback.")

        if slowmo > 0:
            time.sleep(slowmo)

        # Paso 5: Sondeo de redirección fuera de Salesforce
        print(f" [Paso 5/6] Sondeando redirección OAuth post-login (máx {timeout}s)...")
        poll_interval = 0.5
        elapsed_poll = 0.0
        redirected = False

        while elapsed_poll < timeout:
            curr_url = driver.current_url or ""
            curr_title = driver.title or ""
            page_src = driver.page_source or ""
            page_src_low = page_src.lower()

            # Si ya no estamos en la página de autorización de Salesforce
            if "my.site.com" not in curr_url and ("compraonline.alcampo.es" in curr_url or "alcampo.es" in curr_url):
                if "/login" not in curr_url and "/authorization" not in curr_url:
                    redirected = True
                    print(f"            ✔ Redirección confirmada a: {curr_url}")
                    break

            # Comprobar si apareció botón de reseteo de contraseña btnPwReset
            has_pwreset = False
            if "btnpwreset" in page_src_low:
                try:
                    res_els = driver.find_elements(By.ID, "btnPwReset")
                    has_pwreset = any(e.is_displayed() for e in res_els)
                except Exception:
                    has_pwreset = True

            if has_pwreset:
                print(f"            🔄 Detectado #btnPwReset en {masked}. Reintentando login con credenciales...")
                capture_screenshot(driver, email, "err_needs_attention", screenshot_dir)
                relogin_ok, relogin_msg = _handle_pwreset_relogin(driver, email, password)
                if relogin_ok:
                    redirected = True
                    print(f"            ✔ Re-login convalidado exitosamente tras btnPwReset.")
                    break
                else:
                    err_type = "needs_attention"
                    err_reason = relogin_msg or "Error: Requiere restablecer contraseña (btnPwReset)"
                    result["status"] = "failed"
                    result["error_type"] = err_type
                    result["error_reason"] = err_reason
                    print(f"            ❌ Re-login fallido tras btnPwReset: {err_reason}")
                    result["duration"] = round(time.time() - start_time, 2)
                    return result

            # Comprobar si apareció mensaje de error de credenciales o bloqueo de cuenta
            if any(err_msg in page_src_low for err_msg in [
                "usuario o contraseña incorrectos", "credenciales incorrectas",
                "tu cuenta ha sido bloqueada", "call center"
            ]):
                err_type, err_reason = cb.classify_error(page_source=page_src)
                result["status"] = "failed"
                result["error_type"] = err_type
                result["error_reason"] = err_reason
                print(f"            ❌ Autenticación fallida: {err_reason} ({err_type})")
                if "call center" in page_src_low or "cuenta ha sido bloqueada" in page_src_low:
                    capture_screenshot(driver, email, "err_call_center", screenshot_dir)
                elif err_type == "ip_error":
                    capture_screenshot(driver, email, "err_waf", screenshot_dir)
                else:
                    capture_screenshot(driver, email, f"err_{err_type}", screenshot_dir)
                result["duration"] = round(time.time() - start_time, 2)
                return result

            time.sleep(poll_interval)
            elapsed_poll += poll_interval

        if not redirected:
            page_src = driver.page_source or ""
            err_type, err_reason = cb.classify_error(page_source=page_src, error_msg="Timeout en redirección OAuth")
            result["status"] = "failed"
            result["error_type"] = err_type
            result["error_reason"] = err_reason
            print(f"            ❌ Timeout en redirección OAuth: {err_reason}")
            capture_screenshot(driver, email, "err_oauth_timeout", screenshot_dir)
            result["duration"] = round(time.time() - start_time, 2)
            return result

        # Paso 6: Extracción de saldo y tarjeta en /settings/loyalty
        print(f" [Paso 6/6] Validando sesión y extrayendo saldo / tarjeta Alcampo...")
        saldo_raw, card_num = _verify_and_hydrate_session(driver, timeout_s=12.0, email=email)
        val_saldo = limpiar_saldo(saldo_raw)

        result["balance"] = val_saldo
        result["balance_str"] = f"{val_saldo:.2f} €" if val_saldo is not None else (saldo_raw if saldo_raw else "0.00 € (o no detectado)")
        result["card_number"] = card_num or "No detectada"
        result["status"] = "success" if val_saldo is not None else ("no_balance" if saldo_raw == "No encontrado" else "failed")
        if result["status"] == "failed":
            result["error_type"] = "session_or_hydration_error"
            result["error_reason"] = saldo_raw
        else:
            result["error_type"] = "none"

        print(f"            ✔ Saldo extraído:  {result['balance_str']}")
        print(f"            ✔ Tarjeta Alcampo: {result['card_number']}")
        if val_saldo is not None and val_saldo > 0:
            shot_label = "saldo_positivo"
        elif val_saldo == 0:
            shot_label = "saldo_cero_verificado" if card_num else "saldo_cero_compraonline"
        else:
            shot_label = "saldo_no_detectado"
        capture_screenshot(driver, email, shot_label, screenshot_dir)

    except Exception as e:
        page_src = ""
        try:
            page_src = driver.page_source or ""
        except Exception:
            pass
        err_type, err_reason = cb.classify_error(page_source=page_src, error_msg=str(e))
        result["status"] = "error"
        result["error_type"] = err_type
        result["error_reason"] = f"{err_reason} ({type(e).__name__}: {e})"
        print(f"            ❌ Error inesperado: {result['error_reason']}")
        capture_screenshot(driver, email, "err_unexpected", screenshot_dir)

    result["duration"] = round(time.time() - start_time, 2)
    return result


def print_summary_table(results):
    """Imprime una tabla resumen limpia en la consola."""
    print("\n" + "=" * 90)
    print("📋 RESUMEN DE PRUEBAS LOCALES (LOCAL TEST RUNNER)")
    print("=" * 90)
    header = f"{'EMAIL':<30} | {'SALDO':<12} | {'TARJETA':<18} | {'ESTADO':<10} | {'DUR (s)':<7}"
    print(header)
    print("-" * 90)

    total_balance = 0.0
    success_count = 0

    for r in results:
        email_display = r["masked_email"]
        bal_display = f"{r['balance']:.2f} €" if r["balance"] is not None else "---"
        card_display = r["card_number"] if r["card_number"] else "---"
        status_display = r["status"]
        dur_display = f"{r['duration']:.1f}"

        if r["balance"] is not None:
            total_balance += r["balance"]
        if r["status"] == "success":
            success_count += 1

        print(f"{email_display:<30} | {bal_display:<12} | {card_display:<18} | {status_display:<10} | {dur_display:<7}")

    print("-" * 90)
    print(f"Total Cuentas: {len(results)} | Éxitos: {success_count} | Saldo Acumulado: {total_balance:.2f} €")
    print("=" * 90 + "\n")


def export_to_excel(results, output_path):
    """Guarda los resultados en un archivo Excel .xlsx."""
    if pd is None:
        print("⚠️ Advertencia: pandas no está disponible, no se pudo guardar el archivo Excel.")
        return

    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    df_data = []
    for r in results:
        df_data.append({
            "email": r["email"],
            "password": r["password"],
            "saldo": f"{r['balance']:.2f} €" if r["balance"] is not None else "0,00 €",
            "card_number": r["card_number"],
            "status": r["status"],
            "error_type": r["error_type"],
            "error_reason": r["error_reason"],
            "duration_seconds": r["duration"],
            "timestamp": datetime.now().isoformat(),
        })

    df = pd.DataFrame(df_data)
    df.to_excel(out_p, index=False)
    print(f"✔ Resultados exportados exitosamente a Excel: {out_p}")


def main():
    args = parse_arguments()

    # Determinar cuentas a probar
    accounts = []
    if args.email and args.password:
        accounts.append({"email": args.email, "password": args.password})
    elif args.input_file:
        try:
            accounts = load_accounts_from_file(args.input_file, limit=args.limit)
            print(f"✔ {len(accounts)} cuentas cargadas desde {args.input_file}")
        except Exception as e:
            print(f"❌ Error cargando archivo de entrada: {e}")
            sys.exit(1)
    else:
        # Fallback: intentar cargar scraper/accounts.json si existe
        default_acc = SCRAPER_DIR / "accounts.json"
        if default_acc.exists():
            limit = args.limit or 1
            print(f"ℹ️ No se especificó --email ni --input-file. Usando {limit} cuenta(s) de {default_acc}...")
            accounts = load_accounts_from_file(default_acc, limit=limit)
        else:
            print("❌ Debe proporcionar --email y --password, o un archivo con --input-file.")
            print("   Ejemplo: python scripts/local_test.py --email user@example.com --password secret --headful")
            sys.exit(1)

    if not accounts:
        print("❌ No se encontraron cuentas válidas para probar.")
        sys.exit(1)

    # Determinar modo de Chrome (visible vs headless)
    is_headless = True
    if args.visible:
        is_headless = False
    elif args.headless:
        is_headless = True

    mode_str = "VISUAL (Headful GUI)" if not is_headless else "HEADLESS"
    print("\n" + "=" * 70)
    print(f"🚀 INICIANDO LOCAL TEST RUNNER ({mode_str})")
    print(f"   Cuentas a procesar: {len(accounts)}")
    print(f"   Pausa slowmo:       {args.slowmo}s")
    print(f"   Timeout por paso:   {args.timeout}s")
    print("=" * 70)

    # Inicializar WebDriver con create_stealth_driver
    print("🔧 Inicializando ChromeDriver con CDP stealth...")
    try:
        driver = create_stealth_driver(headless=is_headless, timeout=args.timeout)
        print("✔ Navegador iniciado correctamente.")
    except Exception as e:
        print(f"❌ No se pudo inicializar ChromeDriver: {e}")
        sys.exit(1)

    results = []
    try:
        for idx, acc in enumerate(accounts, 1):
            res = test_single_account(
                driver=driver,
                email=acc["email"],
                password=acc["password"],
                timeout=args.timeout,
                slowmo=args.slowmo,
                screenshot_dir=args.screenshot_dir,
            )
            results.append(res)
    finally:
        try:
            driver.quit()
            print("🛑 Navegador cerrado correctamente.")
        except Exception:
            pass

    # Mostrar tabla resumen
    print_summary_table(results)

    # Exportar a Excel si fue solicitado
    if args.output_excel:
        export_to_excel(results, args.output_excel)


if __name__ == "__main__":
    main()
