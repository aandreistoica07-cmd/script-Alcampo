# 🛒 Alcampo Telegram Bot & Dashboard (Repositorio Independiente)

Repositorio independiente listo para ser publicado en GitHub. Contiene el sistema completo de scraping multihilo de cuentas del Club Alcampo con notificaciones automáticas a Telegram y servidor local para el Dashboard web.

---

## 📁 Estructura del Repositorio

```
alcampo_telegram_bot/
├── .github/
│   └── workflows/
│       ├── alcampo_optimized_workflow.yml  # Automatización diaria en GitHub Actions
│       └── check_account.yml               # Verificación manual de una sola cuenta
├── docs/                                   # Frontend Dashboard Web (GitHub Pages o local)
│   ├── index.html                          # Dashboard interfaz principal
│   ├── css/style.css                       # Hojas de estilo
│   ├── history.json                        # Registro histórico de ejecuciones
│   ├── progreso.json                       # Estado de scraping en vivo
│   └── consola.log                         # Log de consola en tiempo real
├── script_alcampo_activacion telegram/     # Núcleo del Motor Python
│   ├── script_optimizado.py               # SCRIPT PRINCIPAL ACTIVO
│   ├── server.py                      # Servidor HTTP local con Dashboard y API
│   ├── update_history.py                  # Script para compilar historial en docs/
│   ├── accounts.json                       # Base de datos de cuentas y contraseñas
│   ├── requirements.txt                    # Lista de paquetes pip necesarios
│   ├── Alcampo_Scraper_Colab.ipynb        # Versión en Google Colab
│   └── legacy/                            # Versiones legadas y pruebas
│       ├── script.py
│       ├── script_v2.py
│       ├── script_mejorado.py
│       ├── ultima_version_beta.py
│       ├── test_direct.py
│       └── test_beta_subset.py
├── .gitignore                              # Archivos ignorados por Git
└── README.md                               # Guía del proyecto
```

---

## 🚀 Cómo Crear e Inicializar este Repositorio en GitHub

Abre una terminal PowerShell en esta carpeta y ejecuta:

```bash
cd "C:\Users\Estudiante\Downloads\alcampo_telegram_bot"

# 1. Inicializar Git
git init
git branch -M main

# 2. Añadir todos los archivos y hacer commit inicial
git add .
git commit -m "🚀 Initial commit: Alcampo Telegram Bot & Dashboard System"

# 3. Vincular con tu nuevo repositorio en GitHub
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITO_ALCAMPO.git

# 4. Subir los cambios a GitHub
git push -u origin main
```

---

## ⚡ Comandos Rápidos de Ejecución Local

### Instalar dependencias:
```bash
pip install -r "script_alcampo_activacion telegram/requirements.txt"
```

### Ejecutar scraping completo + notificar a Telegram:
```bash
python "script_alcampo_activacion telegram/script_optimizado.py" --threads 6 --send-telegram
```

### Iniciar servidor web local con Dashboard:
```bash
python "script_alcampo_activacion telegram/server.py"
```

---

## 🔐 Configuración de Notificaciones (Secrets en GitHub)

En tu nuevo repositorio de GitHub, dirígete a **Settings > Secrets and variables > Actions** y añade:
- **`TELEGRAM_TOKEN`**: Token de tu bot de Telegram.
- **`TELEGRAM_CHAT_ID`**: ID del chat o grupo donde quieres recibir reportes.
- **`FIREBASE_DB_URL`** (Opcional): URL de Firebase Realtime Database si usas el estado en vivo.
