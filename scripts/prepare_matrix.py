import sys
import json
import math
import os
import base64
import re
import time
import uuid
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    # 1. Accounts parsing (prioritize repository accounts.json)
    accounts_file = os.path.join("scraper", "accounts.json")
    accounts = []
    if os.path.exists(accounts_file) and os.path.getsize(accounts_file) > 10:
        try:
            with open(accounts_file, "r", encoding="utf-8") as f:
                accounts = json.load(f)
        except Exception as e:
            print(f"Warning loading {accounts_file}: {e}")

    if not accounts:
        accounts_b64 = os.environ.get("ACCOUNTS_BASE64", "")
        if accounts_b64 and len(accounts_b64.strip()) > 10:
            try:
                accounts = json.loads(base64.b64decode(accounts_b64).decode("utf-8"))
            except Exception as e:
                print(f"Warning decoding ACCOUNTS_BASE64: {e}")

    total = len(accounts)
    per_vm_str = os.environ.get("INPUT_ACCOUNTS_PER_VM") or os.environ.get("ACCOUNTS_PER_VM") or "75"
    try:
        per_vm = int(per_vm_str)
    except Exception:
        per_vm = 75

    shards = math.ceil(total / per_vm) if total > 0 else 1
    matrix_data = {"shard": list(range(shards))}
    run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    print(f"Total cuentas: {total}, Shards generados: {shards}, Run ID: {run_id}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"matrix={json.dumps(matrix_data)}\n")
            f.write(f"total_shards={shards}\n")
            f.write(f"run_id={run_id}\n")

    # 2. Telegram initial notification with solid fallbacks
    token = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

    is_valid_token = bool(re.match(r"^\d+:[A-Za-z0-9_-]+$", token)) and token.lower() not in ("none", "null", "***", "undefined", "")
    is_valid_chat = False
    if chat_id and chat_id.lower() not in ("none", "null", "***", "undefined", ""):
        try:
            int(chat_id)
            is_valid_chat = True
        except ValueError:
            pass

    if not is_valid_token or not is_valid_chat:
        token = None
        chat_id = None

    msg = (
        f"🚀 <b>Iniciando verificación Alcampo Multi-VM</b>\n\n"
        f"📋 Cuentas a procesar: {total}\n"
        f"⚙️ Matriz: {shards} VMs en paralelo (Cola Dinámica Firebase)\n\n"
        f"👀 <b>Ver Monitor en Vivo en tiempo real:</b>\n"
        f"https://script-alcampo.vercel.app/#live"
    )

    if token and chat_id:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                timeout=15
            )
            print(f"[TELEGRAM START] Notificación enviada. Status: {r.status_code}")
        except Exception as e:
            print(f"Error enviando notificación de inicio a Telegram: {e}")
    else:
        print("[TELEGRAM START] Token o Chat ID omitidos. Saltando envío de inicio.")

    # 3. Inicializar /progress.json global en Firebase con el total exacto
    firebase_url = os.environ.get("FIREBASE_DB_URL") or "https://monitor-alcampo-default-rtdb.europe-west1.firebasedatabase.app/"
    if firebase_url:
        try:
            fb_base = firebase_url.strip().rstrip("/")
            init_payload = {
                "run_id": run_id,
                "total": total,
                "processed": 0,
                "success": 0,
                "money": 0,
                "zero": 0,
                "error": 0,
                "total_balance": 0.0,
                "start_time": time.time(),
                "status": "running",
                "is_finished": False,
                "vms": {},
                "threads": {}
            }
            requests.put(f"{fb_base}/progress.json", json=init_payload, timeout=10)
            requests.put(f"{fb_base}/live_accounts.json", json={}, timeout=10)
            print(f"[FIREBASE START] /progress.json inicializado con {total} cuentas (run_id={run_id}).")
        except Exception as fe:
            print(f"Warning inicializando Firebase progress: {fe}")

if __name__ == "__main__":
    main()
