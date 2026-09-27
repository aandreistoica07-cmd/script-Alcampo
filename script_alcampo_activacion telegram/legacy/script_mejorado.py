import sys
import time
import random
import json
import os
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# =======================
# CARGA DE CUENTAS (JSON)
# =======================
ACCOUNTS = []
JSON_FILE = "cuentas_formateadas.json"

try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        ACCOUNTS = json.load(f)
    print(f"✅ Se han cargado {len(ACCOUNTS)} cuentas desde '{JSON_FILE}'.")
except FileNotFoundError:
    print(f"❌ ERROR: No se encontró el archivo '{JSON_FILE}'.")
    print("Asegúrate de crearlo en el mismo directorio (o configurarlo en tu entorno, ej. GitHub Actions).")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"❌ ERROR: El archivo '{JSON_FILE}' no tiene un formato JSON válido.")
    sys.exit(1)

# =======================
# TELEGRAM CONFIG
# =======================
TELEGRAM_TOKEN = "8041531688:AAHif8qa9wMZ1EAxU3MrftR-tCrEkQ2dfPU"
CHAT_ID = -5049278431   # Tu chat_id

def enviar_telegram_texto(mensaje):
    """Envía texto por Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        response = requests.post(url, data=data)
        print(f"📡 Enviando a Telegram: {response.status_code} - {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error CRÍTICO enviando a Telegram: {e}")

def enviar_telegram_documento(path, caption=""):
    """Envía un archivo por Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    try:
        with open(path, "rb") as file:
            data = {"chat_id": CHAT_ID, "caption": caption}
            response = requests.post(url, data=data, files={"document": file})
            print(f"📁 Enviando documento a Telegram: {response.status_code} - {response.text}")
            response.raise_for_status()
    except Exception as e:
        print(f"❌ Error CRÍTICO enviando documento a Telegram: {e}")


# =======================
# FUNCIONES AUXILIARES
# =======================
def espera_humana(min_segs=1.5, max_segs=3.5):
    """Genera una pausa aleatoria para evadir el bloqueo antibots simulando ser humano."""
    tiempo = random.uniform(min_segs, max_segs)
    time.sleep(tiempo)


# =======================
# FUNCION PARA PROCESAR CUENTA
# =======================
try:
    enviar_telegram_texto("🚀 Iniciando script de Alcampo (Versión Anti-Bot con undetected-chromedriver)...")
except Exception as e:
    print(f"Error enviando mensaje de inicio: {e}")

def procesar_cuenta(email, password):
    print(f"\n→→ Procesando cuenta: {email}")
    
    intentos_max = 3
    
    for intento in range(1, intentos_max + 1):
        driver = None
        try:
            if intento > 1:
                print(f"⚠️ Reintentando {email} (Intento {intento}/{intentos_max})...")

            # 1. Cambio a undetected-chromedriver
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            
            driver = uc.Chrome(options=options)

            driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
            
            # 2. Uso de pausas "humanas"
            espera_humana(3.1, 4.8)

            # ======== 3. GESTIÓN DEL BANNER DE COOKIES ========
            try:
                # Buscamos de forma flexible el botón de aceptar
                xpath_cookies = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar')]"
                btn_cookies = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_cookies))
                )
                btn_cookies.click()
                print(f"  [Cookies] Banner aceptado en la sesión de: {email}")
                espera_humana(1.2, 2.5)
            except Exception:
                # Try con otro xpath en caso de que el texto sea distinto o no aparezca interceptable
                 pass # Si falla o el banner no se muestra, capturamos silenciosamente y continuamos
            # ===================================================

            email_field = driver.find_element(By.ID, "uname1")
            password_field = driver.find_element(By.ID, "pwd1")

            # Sustituimos los time.sleep por las pausas aleatorias 
            email_field.send_keys(email)
            espera_humana(0.8, 1.5)
            
            password_field.send_keys(password)
            espera_humana(0.7, 1.4)
            
            password_field.send_keys(Keys.ENTER)
            espera_humana(4.5, 6.5)

            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
            espera_humana(2.0, 3.5)
            
            driver.refresh()
            espera_humana(3.0, 4.5)

            saldo = "No encontrado"
            try:
                elemento = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/main/div[2]/div[2]/div/div/span"
                )
                saldo = elemento.text.strip()
            except:
                pass

            print(f"✔ {email} → SALDO: {saldo}")
            return {"email": email, "password": password, "saldo": saldo}

        except Exception as e:
            print(f"❌ Error en {email} (Intento {intento}): {e}")
            if intento == intentos_max:
                return {"email": email, "password": password, "saldo": f"Error: {e}"}
            espera_humana(2.5, 4.0) # Esperar antes de reintentar

        finally:
            # 4. Manejo correcto de cierre para evitar procesos fantasma
            if driver:
                driver.quit()

# =======================
# EJECUTAR TODO EN PARALELO
# =======================
resultados = []

print("\n🔥 Ejecutando todas las cuentas en paralelo...\n")

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(procesar_cuenta, acc["email"], acc["password"]) for acc in ACCOUNTS]
    for future in as_completed(futures):
        resultados.append(future.result())

# =======================
# GUARDAR RESULTADOS EN EXCEL
# =======================
df = pd.DataFrame(resultados)
excel_path = "saldos_alcampo.xlsx"
df.to_excel(excel_path, index=False)

print("\n💾 Datos guardados en:", excel_path)

# =======================
# CALCULAR RESUMEN Y ENVIAR
# =======================
def limpiar_saldo(saldo_str):
    """Convierte texto tipo '5,30 €' a float 5.30"""
    try:
        if "Error" in saldo_str or "No encontrado" in saldo_str:
            return 0.0
        # Eliminar símbolo euro, espacios y cambiar coma por punto
        limpio = saldo_str.replace('€', '').replace(' ', '').replace(',', '.').strip()
        return float(limpio)
    except:
        return 0.0

saldo_total = 0.0
cuenta_top = {"email": "N/A", "saldo_val": 0.0}
cuentas_con_saldo = 0

for r in resultados:
    valor = limpiar_saldo(r["saldo"])
    saldo_total += valor
    if valor > 0:
        cuentas_con_saldo += 1
    if valor > cuenta_top["saldo_val"]:
        cuenta_top = {"email": r["email"], "saldo_val": valor}

mensaje_resumen = (
    f"📊 **RESUMEN ALCAMPO**\n\n"
    f"✅ Cuentas procesadas: {len(resultados)}\n"
    f"💰 **Saldo Total:** {saldo_total:.2f} €\n"
    f"💎 Cuentas con dinero: {cuentas_con_saldo}\n"
    f"🏆 **Top Cuenta:** {cuenta_top['email']} ({cuenta_top['saldo_val']:.2f} €)"
)

print("\n" + mensaje_resumen)
enviar_telegram_texto(mensaje_resumen)

# =======================
# ENVIAR UN SOLO MENSAJE CON EL EXCEL
# =======================
enviar_telegram_documento(
    excel_path,
    caption="📊 Reporte de saldos de cuentas Alcampo"
)

print("🎉 PROCESO COMPLETO Y ENVIADO A TELEGRAM\n")
