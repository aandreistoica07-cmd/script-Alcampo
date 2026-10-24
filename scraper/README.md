# 🛒 Alcampo Scraper & Telegram Activation System

Sistema optimizado de scraping multihilo con Selenium en headless mode para consultar saldos y tarjetas del Club Alcampo, servidor web local con Dashboard interactivo y notificaciones automáticas a Telegram.

---

## 📁 Estructura del Proyecto (Rutas Relativas)

```
Programacion1/
├── .github/
│   └── workflows/
│       ├── alcampo_2pass_matrix.yml        # Multi-VM matrix pipeline
│       ├── alcampo_optimized_workflow.yml  # Daily cron & manual trigger
│       ├── check_account.yml               # Manual trigger for single-account verification
│       └── build_apk.yml                   # Android APK build
├── dashboard/                              # Frontend del Dashboard
│   ├── index.html                          # Dashboard web UI
│   ├── css/style.css                       # Hojas de estilo
│   ├── history.json                        # Base de datos histórica
│   ├── top_accounts.json                   # Ranking Top 10
│   ├── account_status.json                 # Estado y cooldown
│   └── progreso.json                       # Estado en vivo del scraping
├── scraper/                                # Motor Principal Python
│   ├── __init__.py                         # Package marker
│   ├── README.md                           # Documentación técnica
│   ├── accounts.json                       # Base de datos de credenciales
│   ├── script_optimizado.py                # SCRIPT PRINCIPAL ACTIVO
│   ├── account_cooldown_manager.py         # Cooldown manager
│   ├── Alcampo_Scraper_Colab.ipynb         # Versión en Google Colab
│   └── legacy/                             # Versiones legadas y pruebas
├── scripts/                                # Scripts de soporte
│   ├── local_test.py                       # CLI de pruebas local
│   ├── prepare_matrix.py                   # Matriz CI/CD
│   ├── merge_and_retry.py                  # Consolidación final
│   ├── server.py                           # Servidor HTTP local
│   └── update_history.py                   # Compilador de historial
└── tests/                                  # Suite de tests unitarios
```

---

## 🚀 Requisitos e Instalación

### Dependencias
- **Python 3.10+**
- **Google Chrome** instalado en el sistema

Instala las dependencias necesarias ejecutando:
```bash
pip install -r requirements.txt
```

Dependencias requeridas:
- `selenium`
- `webdriver-manager`
- `requests`
- `pandas`
- `openpyxl`

---

## ⚙️ Uso y Modos de Ejecución

### 1. Ejecución Completa con Notificación a Telegram
Para procesar todas las cuentas de `accounts.json` y enviar el resumen y el archivo Excel a Telegram:
```bash
python script_optimizado.py --threads 6 --send-telegram
```

### 2. Comprobación Individual de una Cuenta
Para consultar rápidamente el saldo y número de tarjeta de una sola cuenta sin procesar toda la lista:
```bash
python script_optimizado.py --check-single "usuario@ejemplo.com" "Contraseña123"
```

### 3. Modo Prueba Limitado
Para ejecutar únicamente sobre las primeras $N$ cuentas:
```bash
python script_optimizado.py --threads 4 --limit 5
```

### 4. Servidor Web Local (Dashboard)
Para iniciar el servidor local que sirve el Dashboard web y permite consultar cuentas en tiempo real:
```bash
python server.py
```
Abre en tu navegador la dirección local que se indica en consola (por defecto `http://localhost:8000/`).

### 5. Actualización del Historial
Tras una ejecución, compila las estadísticas en `docs/history.json` ejecutando:
```bash
python update_history.py --version optimizada
```

### 6. Cola dinámica y bloqueos

Cuando se usa `--use-queue`, cada cuenta se reclama mediante ETags de Firebase
(comparación condicional). Así, dos VMs no pueden procesar la misma cuenta por
una carrera entre lecturas y escrituras. Las cuentas cuyo trabajador deja de
responder se recuperan después de 180 segundos:

```bash
set QUEUE_LEASE_SECONDS=180
python script_optimizado.py --use-queue --threads 3
```

El progreso global se publica como máximo cada tres segundos, mientras que el
resultado individual de cada cuenta se conserva inmediatamente. Esto evita
lecturas repetitivas de toda la colección `/results` que podían saturar
Firebase y dejar trabajadores esperando durante el análisis.

---

## 📲 Configuración de Telegram

El script envía notificaciones al bot configurado. Las variables se pueden definir mediante entorno o usar los valores por defecto del sistema:

- **TELEGRAM_TOKEN**: Token del Bot de Telegram (ej. `8041531688:AAHif...`)
- **TELEGRAM_CHAT_ID**: ID del Chat o Grupo de destino (ej. `-5049278431`)

En **GitHub Actions**, estos valores se configuran en **Repository Secrets** como `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`.

---

## 🛠️ Automatización en GitHub Actions

El repositorio cuenta con dos automatizaciones listas:
1. `.github/workflows/alcampo_optimized_workflow.yml`: Ejecución programada diaria a las 04:36 UTC y ejecutable manualmente desde la pestaña Actions.
2. `.github/workflows/check_account.yml`: Permite consultar el saldo de una cuenta específica mediante `workflow_dispatch`.
