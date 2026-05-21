import os
import sys
import webbrowser
import http.server
import socketserver
from pathlib import Path

# Configure UTF-8 encoding for standard output/error to prevent encoding crashes on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Change directory to this script's directory so it serves files correctly
DIRECTORY = Path(__file__).resolve().parent
os.chdir(DIRECTORY)

DEFAULT_PORT = 8000

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler that disables console logging for clean stdout."""
    def log_message(self, format, *args):
        pass

def find_free_port(start_port):
    """Finds the next available TCP port starting from start_port."""
    port = start_port
    while port < 65535:
        try:
            with socketserver.TCPServer(("", port), QuietHTTPRequestHandler) as s:
                return port
        except OSError:
            port += 1
    return port

def main():
    port = find_free_port(DEFAULT_PORT)
    server_address = ("", port)
    
    print("\n" + "="*60)
    print(">>> MONITOR WEB ALCAMPO SCRAPER INICIADO <<<")
    print(f"Dirección: http://localhost:{port}/dashboard.html")
    print("Abre la dirección anterior en tu navegador para ver el progreso.")
    print("Presiona Ctrl+C para detener este servidor web en cualquier momento.")
    print("="*60 + "\n")
    
    # Open default browser to the dashboard page
    try:
        webbrowser.open(f"http://localhost:{port}/dashboard.html")
    except Exception as e:
        print(f"No se pudo abrir el navegador automáticamente: {e}")

    try:
        with socketserver.TCPServer(server_address, QuietHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor web detenido.")
        sys.exit(0)

if __name__ == "__main__":
    main()
