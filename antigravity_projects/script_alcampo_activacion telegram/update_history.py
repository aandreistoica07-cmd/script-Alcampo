import os
import re
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

# Reconfigure stdout/stderr to UTF-8 for Windows terminal
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # In case of older python version without reconfigure


def parse_args():
    parser = argparse.ArgumentParser(description="Compile Alcampo Scraper execution stats to history.json")
    parser.add_argument(
        "--version",
        choices=["optimizada", "antigua"],
        default="optimizada",
        help="Script version used ('optimizada' or 'antigua')"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Execution duration in seconds (optional)"
    )
    return parser.parse_args()

def limpiar_saldo(saldo_str):
    if pd.isna(saldo_str) or saldo_str is None:
        return None
    texto = str(saldo_str).strip()
    if not texto or "Error" in texto or "No encontrado" in texto:
        return None
    # Match numbers with decimal point or comma
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
    
    # Paths
    script_dir = Path(__file__).resolve().parent
    excel_path = script_dir / "saldos_alcampo.xlsx"
    progreso_path = script_dir / "progreso.json"
    
    # Path to docs/history.json relative to this script
    docs_dir = script_dir.parent.parent / "docs"
    history_path = docs_dir / "history.json"
    
    # Ensure docs directory exists
    docs_dir.mkdir(exist_ok=True)
    
    print(f"📊 Compilando estadísticas de ejecución...")
    
    # 1. Load Excel file
    if not excel_path.exists():
        print(f"❌ Error: No se encuentra el archivo Excel en {excel_path}")
        return
        
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"❌ Error al leer el archivo Excel: {e}")
        return
        
    total_accounts = len(df)
    total_balance = 0.0
    cuentas_con_dinero = 0
    cuentas_cero = 0
    cuentas_error = 0
    
    # Parse each account's balance
    for _, row in df.iterrows():
        saldo_raw = row.get("saldo", "")
        valor = limpiar_saldo(saldo_raw)
        
        if valor is None:
            cuentas_error += 1
        elif valor > 0:
            total_balance += valor
            cuentas_con_dinero += 1
        else:
            cuentas_cero += 1
            
    # Calculate success rate
    successes = cuentas_con_dinero + cuentas_cero
    success_rate = (successes / total_accounts * 100) if total_accounts > 0 else 0.0
    
    # 2. Determine duration
    duration = args.duration
    if duration is None:
        # Try to read from progreso.json
        if progreso_path.exists():
            try:
                with open(progreso_path, "r", encoding="utf-8") as f:
                    progress_data = json.load(f)
                    duration = progress_data.get("elapsed")
            except Exception:
                pass
        
    if duration is None:
        duration = 0.0
        
    # 3. Load existing history or initialize
    history_data = []
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                if not isinstance(history_data, list):
                    history_data = []
        except Exception as e:
            print(f"⚠️ No se pudo leer history.json existente, se creará uno nuevo. Error: {e}")
            
    # 4. Create new entry
    version_label = "Optimized Script" if args.version == "optimizada" else "Old Script"
    
    # Calculate ID based on existing entries
    next_id = 1
    if history_data:
        try:
            next_id = max(entry.get("id", 0) for entry in history_data) + 1
        except Exception:
            next_id = len(history_data) + 1

    new_entry = {
        "id": next_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": version_label,
        "duration": round(duration, 2),
        "checked": total_accounts,
        "success": total_accounts - cuentas_error,
        "zero": cuentas_cero,
        "error": cuentas_error,
        "success_rate": round(success_rate, 2),
        "total_balance": round(total_balance, 2)
    }
    
    history_data.append(new_entry)
    
    # Limit history to last 100 entries to prevent files from growing too large
    if len(history_data) > 100:
        history_data = history_data[-100:]
        
    # 5. Write history back
    try:
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4)
        print(f"✔ Historial guardado correctamente en {history_path}")
        print(f"   Balance Total: {total_balance:.2f} € | Cuentas con Dinero: {cuentas_con_dinero} | Errores: {cuentas_error}")
    except Exception as e:
        print(f"❌ Error al escribir en history.json: {e}")

if __name__ == "__main__":
    main()
