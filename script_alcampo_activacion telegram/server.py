import os
import sys
import json
import webbrowser
import http.server
import socketserver
import socket
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Configure UTF-8 encoding for standard output/error to prevent encoding crashes on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Script directory
SCRIPT_DIR = Path(__file__).resolve().parent
# Add script directory to sys.path to import script_optimizado
sys.path.append(str(SCRIPT_DIR))

# Project root directory
ROOT_DIR = SCRIPT_DIR.parent
os.chdir(ROOT_DIR)

DEFAULT_PORT = 8000

class ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler that routes dashboard requests and implements API endpoints."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def log_message(self, format, *args):
        # Disable verbose console logs to keep console output clean
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        # Route mapping
        if path == "/" or path == "/index.html":
            self.path = "/docs/index.html"
            return super().do_GET()
        elif path in ("/css/style.css", "/css/styles.css"):
            self.path = "/docs/css/style.css"
            return super().do_GET()
        elif path == "/progreso.json":
            self.path = "/script_alcampo_activacion telegram/progreso.json"
            return super().do_GET()
        elif path == "/consola.log":
            self.path = "/script_alcampo_activacion telegram/consola.log"
            return super().do_GET()
        elif path == "/top_accounts.json":
            self.path = "/docs/top_accounts.json"
            return super().do_GET()
        elif path == "/history.json":
            self.path = "/docs/history.json"
            return super().do_GET()
        elif path == "/account_status.json":
            self.path = "/script_alcampo_activacion telegram/account_status.json"
            return super().do_GET()
            
        # API endpoint for checking a single account balance & card
        elif path == "/api/check_account":
            email = query.get("email", [None])[0]
            password = query.get("password", [None])[0]
            if not email or not password:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Faltan parámetros email o password"}).encode("utf-8"))
                return
            
            print(f"🔎 [Servidor Local] Solicitando comprobación en tiempo real para: {email}")
            try:
                from script_optimizado import check_single_account
                res = check_single_account(email, password, scrape_card=True)
                
                # Sync with AccountCooldownManager
                try:
                    from account_cooldown_manager import AccountCooldownManager
                    cd_mgr = AccountCooldownManager()
                    is_ok = (res.get("status") == "success" and res.get("balance") is not None)
                    cd_res = cd_mgr.record_result(email, is_ok, error_msg=res.get("error"))
                    cd_mgr.save()
                    print(f"📋 [Servidor Local] Cooldown Manager actualizado: {cd_res}")
                except Exception as c_err:
                    print(f"Warning actualizando Cooldown Manager: {c_err}")
                
                # If success, update local top_accounts.json file so it persists
                if res.get("status") == "success":
                    try:
                        top_local_path = ROOT_DIR / "docs" / "top_accounts.json"
                        if top_local_path.exists():
                            with open(top_local_path, "r", encoding="utf-8") as f:
                                top_accounts = json.load(f)
                            if isinstance(top_accounts, list):
                                updated = False
                                for acc in top_accounts:
                                    if acc.get("email") == email:
                                        acc["balance"] = res["balance"]
                                        if res.get("card_number"):
                                            acc["card_number"] = res["card_number"]
                                        updated = True
                                        break
                                if updated:
                                    # Sort again by balance descending
                                    top_accounts.sort(key=lambda x: x.get("balance", 0.0), reverse=True)
                                    with open(top_local_path, "w", encoding="utf-8") as f:
                                        json.dump(top_accounts, f, indent=4)
                                    print(f"✔ [Servidor Local] top_accounts.json local actualizado y reordenado.")
                    except Exception as ex:
                        print(f"Error actualizando top_accounts.json desde servidor: {ex}")
            except Exception as e:
                res = {"status": "error", "balance": None, "card_number": None, "error": str(e)}
                
            print(f"✔ [Servidor Local] Comprobación terminada para: {email} | Resultado: {res}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return
            
        else:
            return super().do_GET()

def find_free_port(start_port):
    """Finds the next available TCP port starting from start_port using a clean socket bind check."""
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            port += 1
    return port

def main():
    port = find_free_port(DEFAULT_PORT)
    server_address = ("", port)
    
    print("\n" + "="*60)
    print(">>> SERVIDOR DASHBOARD ALCAMPO INICIADO <<<")
    print(f"Dirección local: http://localhost:{port}/")
    print("Panel en la Nube: https://alcampo.vercel.app/")
    print("Abre la dirección anterior en tu navegador para ver el dashboard.")
    print("Presiona Ctrl+C para detener este servidor web en cualquier momento.")
    print("="*60 + "\n")
    
    # Open default browser to the dashboard page
    try:
        webbrowser.open(f"http://localhost:{port}/")
    except Exception as e:
        print(f"No se pudo abrir el navegador automáticamente: {e}")

    try:
        with ThreadingHTTPServer(server_address, CustomHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor web detenido.")
        sys.exit(0)

if __name__ == "__main__":
    main()
