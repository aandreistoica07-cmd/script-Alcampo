# 🛒 Alcampo Telegram Bot & Dashboard (Repositorio Independiente)

Repositorio independiente listo para ser publicado en GitHub. Contiene el sistema completo de scraping multihilo de cuentas del Club Alcampo con notificaciones automáticas a Telegram y servidor local para el Dashboard web.

---

## 📁 Estructura del Repositorio

```
Programacion1/
├── .github/
│   └── workflows/
│       ├── alcampo_2pass_matrix.yml        # Pipeline multi-VM en GitHub Actions
│       ├── alcampo_optimized_workflow.yml  # Automatización diaria en GitHub Actions
│       ├── check_account.yml               # Verificación manual de una sola cuenta
│       └── build_apk.yml                   # Compilación Android APK
├── dashboard/                              # Frontend Dashboard Web (Vercel y APK)
│   ├── index.html                          # Dashboard interfaz principal
│   ├── css/style.css                       # Hojas de estilo
│   ├── history.json                        # Registro histórico de ejecuciones
│   ├── top_accounts.json                   # Ranking Top 10 de saldos
│   ├── account_status.json                 # Estado y cooldown de cuentas
│   └── progreso.json                       # Estado de scraping en vivo
├── scraper/                                # Núcleo del Motor Python
│   ├── __init__.py                         # Módulo Python
│   ├── script_optimizado.py                # SCRIPT PRINCIPAL ACTIVO
│   ├── account_cooldown_manager.py         # Gestor de cooldown y rotación
│   ├── accounts.json                       # Base de datos de cuentas
│   └── legacy/                             # Versiones legadas y pruebas
├── scripts/                                # Scripts de Automatización y Pruebas
│   ├── local_test.py                       # CLI de pruebas locales (1/N cuentas, headful/headless)
│   ├── prepare_matrix.py                   # Generación de matriz CI/CD y sync Firebase
│   ├── merge_and_retry.py                  # Consolidación final y reportes Telegram
│   ├── update_history.py                   # Script para compilar historial en dashboard/
│   └── server.py                           # Servidor HTTP local con Dashboard y API
├── tests/                                  # Suite de Pruebas Unitarias
│   ├── __init__.py
│   ├── test_scraper_utils.py
│   ├── test_circuit_breaker.py
│   ├── test_cooldown_manager.py
│   ├── test_matrix_calc.py
│   └── test_merge_and_retry.py
├── requirements.txt                        # Lista de paquetes pip necesarios
└── README.md                               # Guía del proyecto
```

---

## ⚡ Comandos Rápidos de Ejecución Local

### Instalar dependencias:
```bash
pip install -r requirements.txt
```

### Probar cuentas en local (CLI de pruebas):
```bash
python scripts/local_test.py --email "usuario@ejemplo.com" --password "clave" --headful
```

### Ejecutar scraping completo + notificar a Telegram:
```bash
python scraper/script_optimizado.py --threads 6 --send-telegram
```

### Iniciar servidor web local con Dashboard:
```bash
python scripts/server.py
```

---

## 🔐 Configuración de Notificaciones (Secrets en GitHub)

En tu nuevo repositorio de GitHub, dirígete a **Settings > Secrets and variables > Actions** y añade:
- **`TELEGRAM_TOKEN`**: Token de tu bot de Telegram.
- **`TELEGRAM_CHAT_ID`**: ID del chat o grupo donde quieres recibir reportes.
- **`FIREBASE_DB_URL`** (Opcional): URL de Firebase Realtime Database si usas el estado en vivo.
