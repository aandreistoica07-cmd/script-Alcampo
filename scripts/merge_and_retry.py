import os
import glob
import json
import re
import argparse
import pandas as pd
import requests

def parse_args():
    parser = argparse.ArgumentParser(description="Merge and Retry Helper for Alcampo GitHub Actions Pipeline")
    parser.add_argument("--mode", choices=["check-timeouts", "final-merge"], required=True)
    parser.add_argument("--input-dir", default="./all_shards", help="Directory containing shard Excel files")
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

def enviar_telegram(token, chat_id, texto, excel_path):
    try:
        url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url_msg, data={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}, timeout=10)
        
        url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
        with open(excel_path, "rb") as f:
            requests.post(url_doc, data={"chat_id": chat_id, "caption": "📊 Reporte Maestro Consolidado de Saldos Alcampo"}, files={"document": f}, timeout=15)
        print("🎉 Telegram notificado con éxito.")
    except Exception as e:
        print(f"⚠️ Error enviando a Telegram: {e}")

def main():
    args = parse_args()
    
    if args.mode == "check-timeouts":
        files = glob.glob(os.path.join(args.input_dir, "**", "*.xlsx"), recursive=True)
        print(f"🔎 Inspeccionando {len(files)} archivos de la Pasada 1...")
        
        failed_accounts = []
        for f in files:
            try:
                df = pd.read_excel(f)
                for _, row in df.iterrows():
                    saldo = str(row.get("saldo", ""))
                    causa = str(row.get("causa_error", ""))
                    if "Bloqueo/Timeout" in saldo or "Timeout" in causa:
                        failed_accounts.append({
                            "email": str(row["email"]).strip(),
                            "password": str(row["password"]).strip()
                        })
            except Exception as e:
                print(f"Error leyendo {f}: {e}")
                
        print(f"🔴 Cuentas con timeout detectadas para reintento: {len(failed_accounts)}")
        
        has_timeouts = "true" if len(failed_accounts) > 0 else "false"
        if len(failed_accounts) > 0:
            with open(args.failed_json, "w", encoding="utf-8") as f:
                json.dump(failed_accounts, f, ensure_ascii=False, indent=2)
            print(f"💾 Cuentas fallidas guardadas en {args.failed_json}")
            
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
                # Mark priority: retry shards get higher priority
                if "retry" in f.lower():
                    df["_priority"] = 2
                else:
                    df["_priority"] = 1
                dfs.append(df)
            except Exception as e:
                print(f"Error leyendo {f}: {e}")
                
        if not dfs:
            print("❌ No se encontraron archivos para consolidar.")
            return

        df_all = pd.concat(dfs, ignore_index=True)
        # Sort by priority so retry non-error results overwrite pass 1 timeouts
        df_all.sort_values(by=["_priority"], inplace=True)
        df_all.drop_duplicates(subset=["email"], keep="last", inplace=True)
        df_all.drop(columns=["_priority"], errors="ignore", inplace=True)
        
        # Build multi-sheet master excel
        df_success = df_all[df_all["saldo"].astype(str).str.contains("Tu Saldo es", na=False)].copy()
        df_callcenter = df_all[df_all["saldo"].astype(str).str.contains("Call Center", na=False)].copy()
        df_errors = df_all[~df_all["email"].isin(df_success["email"]) & ~df_all["email"].isin(df_callcenter["email"])].copy()

        with pd.ExcelWriter(args.output_excel, engine="openpyxl") as writer:
            df_all.to_excel(writer, sheet_name="Todas las Cuentas", index=False)
            df_success.to_excel(writer, sheet_name="Exitosas con Saldo", index=False)
            df_callcenter.to_excel(writer, sheet_name="Bloqueadas Call Center", index=False)
            df_errors.to_excel(writer, sheet_name="Error Credenciales", index=False)

        print(f"💾 Reporte consolidado final guardado en {args.output_excel}")
        
        # Calculate summary metrics
        total = len(df_all)
        saldo_total = 0.0
        cuentas_dinero = 0
        cuentas_cero = 0
        cuentas_error = len(df_errors) + len(df_callcenter)
        ranked = []

        for _, row in df_success.iterrows():
            val = limpiar_saldo(row.get("saldo"))
            if val is not None:
                saldo_total += val
                if val > 0:
                    cuentas_dinero += 1
                    ranked.append((val, str(row.get("email", ""))))
                else:
                    cuentas_cero += 1

        ranked.sort(key=lambda x: x[0], reverse=True)
        top_10 = ranked[:10]
        top_10_str = "\n".join([f"   {i+1}. {email} ({val:.2f} €)" for i, (val, email) in enumerate(top_10)]) if top_10 else "   N/A"

        msg = (
            f"📊 <b>RESUMEN CONSOLIDADO FINAL (2 PASADAS MATRIZ)</b>\n\n"
            f"✅ Cuentas totales: {total}\n"
            f"💰 <b>Saldo Total Extraído:</b> {saldo_total:.2f} €\n"
            f"💎 Cuentas con dinero: {cuentas_dinero}\n"
            f"💤 Cuentas con saldo 0: {cuentas_cero}\n"
            f"⚠️ Cuentas con error / Call Center: {cuentas_error}\n\n"
            f"🏆 <b>Top 10 Cuentas con Mayor Saldo:</b>\n{top_10_str}"
        )

        token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if token and chat_id:
            enviar_telegram(token, chat_id, msg, args.output_excel)

if __name__ == "__main__":
    main()
