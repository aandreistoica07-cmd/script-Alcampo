# 🚀 Guía de Ejecución en Google Colab (Alcampo Scraper)

Esta guía detalla cómo ejecutar el scraper de Alcampo de forma **puntual y manual** en el plan gratuito de Google Colab, sin consumir minutos de GitHub Actions ni recursos de tu ordenador.

---

## 🔑 1. Secretos a Configurar en Colab Secrets

En la barra lateral izquierda de Google Colab, pulsa el icono de la **llave** (🔑 *Secrets*) y añade los siguientes secretos:

| Secreto | Obligatorio | Descripción |
|---|:---:|---|
| `ACCOUNTS_BASE64` | **SÍ** | Las 512 cuentas en formato Gzip + Base64 (o Base64 estándar). Se valida estrictamente integridad de 512 cuentas. |
| `FIREBASE_DB_URL` | **SÍ** | URL de tu Firebase Realtime Database (ej. `https://tu-proyecto.firebaseio.com/`). |
| `GITHUB_TOKEN` | Opcional / Recomendado | Token Fine-Grained de GitHub con permiso de **solo lectura** (*Contents: Read*) sobre el repo `script-Alcampo` para clonar el código. |
| `TELEGRAM_TOKEN` | Opcional | Token de tu bot de Telegram para recibir alertas y reportes Excel. |
| `TELEGRAM_CHAT_ID` | Opcional | ID numérico del chat/canal de Telegram donde recibir los reportes. |

> [!IMPORTANT]
> **Activa el interruptor "Acceso al notebook"** en cada secreto dentro del panel de Colab para que `google.colab.userdata` pueda leerlos.

---

## 🖱️ 2. Cómo Ejecutar (Paso a Paso)

1. Abre Google Colab (https://colab.research.google.com).
2. Sube el archivo `colab/alcampo_colab.ipynb` (o selecciónalo desde tu Google Drive).
3. Revisa la **Celda 2 (Configuración)**:
   - `MODO`:
     - `"nueva"`: Realiza una **copia de seguridad previa** de Firebase en Drive y reinicia la cola desde cero con las 512 cuentas.
     - `"continuar"`: Reanuda la ejecución respetando las cuentas ya finalizadas con éxito (`status: ok`).
   - `HILOS`: **2** (recomendado para los 2 vCPUs de Colab) o **3** (máximo).
   - `DRIVE_MOUNT`: `True` para guardar automáticamente el Excel y `results.json` en tu carpeta privada de Drive.
4. En el menú superior de Colab, pulsa **Entorno de ejecución → Ejecutar todo** (o `Ctrl + F9`).

---

## 🔄 3. Cómo Reanudar si se Corta la Sesión

Google Colab desconecta el entorno tras inactividad prolongada o límite de sesión (~12 h). El scraper incluye un guardarraíl propio de ~11 h que libera limpiamente las cuentas antes del corte.

Si la sesión se corta antes de finalizar:
1. Vuelve a abrir el cuaderno en Colab.
2. En la **Celda 2**, asegúrate de que `MODO = "continuar"`.
3. Pulsa **Entorno de ejecución → Ejecutar todo**.
4. **Comportamiento automático**:
   - Las cuentas completadas con éxito (`status == "success"`) **NO se repiten**.
   - Las cuentas que estaban en vuelo (`status == "in_progress"` o con lease vencido) **vuelven automáticamente a pendientes**.
   - El progreso previo se lee desde Google Drive y continúa donde se quedó.

---

## 🛡️ 4. Anti-Bloqueo y Canario de IP

Las IPs asignadas por Colab pertenecen a centros de datos de Google y cambian en cada sesión. La **Celda 4 (Canario de IP)** verifica antes de procesar cuentas si la IP está limpia:
- Si el canario devuelve **HTTP 200**: Continúa la ejecución normalmente.
- Si detecta bloqueo Cloudflare, HTTP 403 o 429: Detiene la ejecución inmediatamente sin consumir cuentas.
  - **Qué hacer si falla el canario**: Ve al menú superior: **Entorno de ejecución → Desconectar y eliminar entorno de ejecución**. Espera 10 segundos y vuelve a pulsar "Ejecutar todo" para que Google te asigne una nueva máquina con otra IP.

---

## 🔒 5. Cómo Guardar el Cuaderno sin Datos Sensibles

Para evitar que se guarden en el historial del `.ipynb` datos sensibles o salidas de ejecución:
1. En la barra de menús de Colab, pulsa **Editar → Borrar todos los resultados**.
2. Guarda el cuaderno con **Archivo → Guardar** (o `Ctrl + S`).
3. Todas las salidas de consola enmascaran automáticamente los correos (ej. `us***1@gmail.com`) y ocultan contraseñas.

---

## 🧪 6. Protocolo de Verificación por Niveles

Ejecuta las pruebas en orden en Google Colab para validar el entorno antes del lote masivo:

### Nivel 1: Prueba de 4 Cuentas (Saldo Conocido)
- En **Celda 2**, configura: `TEST_LIMIT = "4"`, `MODO = "nueva"`, `HILOS = 2`.
- Pulsa **Ejecutar todo**.
- **Qué copiar y pegar**: Pega la tabla resumen final de la **Celda 7** (con los tiempos por paso y el saldo verificado para contrastarlo con el saldo conocido local).

### Nivel 2: Prueba de 20-30 Cuentas (2 Hilos vs 3 Hilos)
- En **Celda 2**, configura: `TEST_LIMIT = "25"`, `HILOS = 2` (y luego relanza con `HILOS = 3`).
- **Qué copiar y pegar**: Pega la tasa de éxito, tiempos medios por cuenta y si surgió alguna activación del circuit breaker.

### Nivel 3: Ejecución Completa (512 Cuentas)
- En **Celda 2**, configura: `TEST_LIMIT = "None"`, `MODO = "nueva"` (o `"continuar"` si se venía de una previa).
- **Qué copiar y pegar**: Pega la tabla final de 512 cuentas, duración total y confirmación del archivo `alcampo_saldos_final.xlsx` en Google Drive.
