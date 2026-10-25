# Especificación de Infraestructura y Filosofía de Pruebas: Alcampo Scraper (E2E Track)

**Documento de Arquitectura de Calidad y Verificación de Requisitos**  
**Proyecto**: Alcampo Scraper & CI/CD Pipeline Optimization  
**Ruta**: `TEST_INFRA.md` | **Fecha**: 2026-10-25 | **Versión**: 1.0.0  
**Enfoque**: Requirement-Driven, Opaque-Box, 100% Determinista y Offline  

---

## 1. Filosofía de Pruebas (Test Philosophy)

El conjunto de pruebas End-to-End (E2E) y de aceptación de requisitos se rige por cuatro principios fundamentales:

### 1.1 Opaque-Box & Requirement-Driven (Caja Opaca Basada en Requisitos)
Las pruebas validan el comportamiento observable externo del sistema frente a las especificaciones contractuales formalizadas en `PROJECT.md`, `ORIGINAL_REQUEST.md` y `requirements_spec.md`. No se acoplan a artefactos volátiles internos ni a implementaciones efímeras. Si un componente recibe una entrada específica, se verifica que su salida (código de salida, estado, Excel generado, mensaje de Telegram, tupla de saldo/tarjeta, archivo de captura de pantalla) cumpla con la especificación exacta.

### 1.2 Ejecución 100% Determinista, Aislada y Sin Red (Zero-Network, Zero-Chrome Dependency)
Para garantizar la reproducibilidad incondicional tanto en entornos locales (Windows PowerShell) como en runners de integración continua (GitHub Actions Ubuntu), las pruebas no dependen de:
- Conexiones de red en vivo ni APIs de terceros (Telegram Bot API, Firebase Realtime Database, endpoints OAuth de Salesforce o Alcampo).
- Instancias reales de Google Chrome o ChromeDriver, eliminando la fragilidad por dependencias gráficas, fallos de renderizado de GPU, bloqueos de IP o restricciones de sandbox.
- Todo comportamiento de red y DOM se simula mediante dobles de prueba (`MockStealthWebDriver`, `MockWebElement`), oráculos de validación estricta y volcados reales de DOM (`dump_loyalty.html` y `dump_miportal.html`).

### 1.3 Derivación Autorizada de Salidas Esperadas
Toda aserción matemática, de formato de cadena o de clasificación se deriva directamente de fuentes autorizadas:
- **Cuenta Testigo (`noelia_gll@hotmail.com`)**: Saldo real = `3.00 €`, Tarjeta = `4003009301402`, resolución mediante Capa 2 (`miportal.alcampo.es`).
- **Oráculo de Telegram Bot API**: Cumplimiento del límite estricto de 4096 caracteres (truncado preventivo a 3980 chars), balanceo exacto de etiquetas HTML permitidas (`<b>`, `<i>`, `<a>`, `<code>`), y sanitización de caracteres `<`, `>`, `&`.
- **Esquema de Excel de 6 Hojas**: Coherencia de columnas, enrutamiento mutuamente excluyente y desduplicación prioritaria (éxitos prevalecen sobre errores).

### 1.4 Verificación Adversarial y Resiliencia Extrema
Se inyectan escenarios límite, datos malformados, valores extremos, cadenas con caracteres de escape HTML/XML, roturas de sesión, respuestas HTTP 403/429 y caídas abruptas de microservicios para comprobar que el pipeline degrada de forma controlada y nunca falla con excepciones no controladas.

---

## 2. Inventario de Características (Feature Inventory F1 - F8)

| # | Característica | Descripción y Contrato de Requisito | Hito | Referencia Contractual |
|---|----------------|-------------------------------------|------|------------------------|
| **F1** | Visual Screenshot Instrumentation | Captura automática y fechada de pantalla ante excepciones (`err_inputs`, `err_waf`, `err_call_center`, `err_pwreset`, `err_timeout`) y anomalías de saldo (`saldo_positivo`, `saldo_cero_compraonline`, `saldo_cero_verificado`, `saldo_no_detectado`) en `screenshots/{safe_email}_{label}_{timestamp}.png`. | M1 | `ORIGINAL_REQUEST.md` (R1)<br>`PROJECT.md` § Interface Contracts |
| **F2** | Expanded Card Regex | Extracción exhaustiva de números de tarjeta de fidelidad Club Alcampo en formato EAN-13 (13 dígitos), admitiendo tanto el rango histórico `400200` como el rango activo `400300`, además de patrones generales `400\d{10}` y `280\d{10}`. | M2 | `requirements_spec.md` § 4.2<br>`PROJECT.md` F2 |
| **F3** | Dual-Layer Balance Fallback | Arquitectura en 2 capas: Si Capa 1 (`compraonline.alcampo.es/settings/loyalty`) arroja `0,00 €` sospechoso o banner `settings.loyalty.manage.alternative` existiendo `loyalty-manage-button`, conmutar mediante OAuth a Capa 2 (`miportal.alcampo.es/es/cuenta/fidelidad`) para extraer saldo y tarjeta verídicos. | M2 | `ORIGINAL_REQUEST.md` (Follow-up)<br>`PROJECT.md` F3 |
| **F4** | Synchronize `btnPwReset` Handling | Paridad funcional estricta entre `scripts/local_test.py` y `scraper/script_optimizado.py`: re-inyección de credenciales ante pantalla de cambio forzado de clave (`btnPwReset`). Si no resuelve, clasificar en `needs_attention` sin quemar el Circuit Breaker. | M2 | `PROJECT.md` F4<br>`requirements_spec.md` § 4.4 |
| **F5** | Visual Audit on Critical Samples | Verificación sobre los cuatro arquetipos de cuentas: testigo positivo (`noelia_gll@hotmail.com` con 3.00 €), saldo 0 legítimo, desafío `btnPwReset` y cuenta bloqueada por Call Center. | M3 | `ORIGINAL_REQUEST.md` (R2)<br>`requirements_spec.md` § 5.2 |
| **F6** | Cross-Agent Evidence Debate | Formalización del consenso multi-agente: timeouts adaptativos de hasta 15s para runners lentos en Ubuntu, normalización de clases CSS (`sana-sans-alt` vs contenedores genéricos), y erradicación definitiva de falsos ceros. | M3 | `ORIGINAL_REQUEST.md` (R3)<br>`requirements_spec.md` § 2 (R3) |
| **F7** | Consolidation & Retry Refactor | Refactorización de `scripts/merge_and_retry.py`: función `is_definitive_success`, distribución estricta en 6 hojas Excel, generación de cola de reintento para Pasada 2 y ranking Top 10 estrictamente limitado a 10 cuentas. | M4 | `PROJECT.md` F7<br>`requirements_spec.md` § 6.1 |
| **F8** | Empirical Verification & Baseline Comparison | Ejecución 100% verde de la suite unitaria (47 tests canónicos), validación local sin Chrome, y demostración cuantitativa de mejora respecto al baseline de la ejecución #382 (>150 € vs 17.82 € y <80 ceros vs 298). | M5 | `ORIGINAL_REQUEST.md` (R5)<br>`requirements_spec.md` § 7 |

---

## 3. Metodología de Pruebas en 4 Niveles (4-Tier Methodology)

La suite de validación E2E se estructura en 4 niveles concéntricos:

```
+---------------------------------------------------------------+
| Tier 4: Real-World Scenarios (512 batch, Top 10, Excel, TG)  |
+-------------------------------+-------------------------------+
| Tier 3: Cross-Feature Pairs   | (PwReset + C1/C2 + WAF + CB)  |
+-------------------------------+-------------------------------+
| Tier 2: Boundary & Corners    | (0.00€ vs None, EANs, Thrott) |
+-------------------------------+-------------------------------+
| Tier 1: Feature Coverage (F1-F8, >=5 tests per feature)       |
+---------------------------------------------------------------+
```

### 3.1 Tier 1: Feature Coverage (Cobertura Funcional Directa)
Exige un mínimo de **5 casos de prueba unitarios y deterministas por cada una de las 8 características (F1 a F8)**:
- **F1 (Visual Screenshots)**: Disparo en login timeout (`err_inputs`), disparo en WAF (`err_waf`), disparo en Call Center (`err_callcenter`), disparo en `btnPwReset` (`err_pwreset`), disparo en anomalía de saldo, y formato estricto de nombre de archivo con sanitización de PII.
- **F2 (Expanded Card Regex)**: Coincidencia con prefijo `400200`, coincidencia con prefijo `400300`, coincidencia con `400\d{10}` genérico, extracción desde fixture real `dump_miportal.html`, extracción desde fixture real `dump_loyalty.html`, y rechazo de EANs no válidos o de longitud incorrecta.
- **F3 (Dual-Layer Fallback)**: Activación de Capa 2 ante banner `settings.loyalty.manage.alternative`, activación ante saldo no hidratado ("No encontrado"), resolución en `miportal` con extracción de 3,00 € y tarjeta `4003009301402`, aceptación directa en Capa 1 si saldo > 0, certificación de 0,00 € legítimo, y tolerancia a fallos en navegación a Miportal.
- **F4 (btnPwReset Sync)**: Detección del elemento `#btnPwReset`, re-inyección de credenciales, redirección exitosa post-reset, clasificación como `needs_attention` ante reset no superado, y no incremento de fallos de servidor en `CircuitBreaker`.
- **F5 (Visual Audit on Samples)**: Auditoría de cuenta testigo (`noelia_gll@hotmail.com`), auditoría de cuenta saldo 0 verificado, auditoría de cuenta en reset de clave, auditoría de cuenta suspendida en Call Center, y auditoría de credenciales erróneas.
- **F6 (Cross-Agent Debate Consensus)**: Verificación de sondeo dinámico adaptativo (hasta 15s), tolerancia a diferencias CSS entre Windows y Linux Headless, preservación de cuentas positivas en Top 10 en lugar de ser enviadas a saldo cero, consistencia monotónica de métricas, y detección del microservicio desincronizado.
- **F7 (Consolidation Merge)**: Validación de `is_definitive_success`, enrutamiento en las 6 hojas de Excel, desduplicación prioritaria (Pass 2 o éxito prevalece), aislamiento de fallos reintentables para Pasada 2, y generación de ranking Top 10 descendente limitado a 10.
- **F8 (Empirical Baseline Comparison)**: Verificación de ejecución offline sin Chrome, modelado de comparativa contra Run #382 (aumento de balance extraído), erradicación de falsos ceros (<80 vs 298), aislamiento de cooldown transitorio, y umbrales de seguridad del circuit breaker (`failures=8`, `min_processed=10`).

### 3.2 Tier 2: Boundary & Corner Cases (Casos Límite y Casos Esquina)
Verificación de entradas patológicas, límites de rango numérico y estados de borde (mínimo 5 por categoría):
- **0.00 € vs No Hidratado**: Distinción matemática estricta entre un saldo nulo verificado (`0.00`) y un estado no recuperado (`None` / "No encontrado").
- **Ausencia de Tarjeta**: Comportamiento cuando una cuenta tiene saldo pero no tarjeta, o carece de ambas.
- **Diferenciación de EANs**: Identificación de prefijos Alcampo (`400200`, `400300`), prefijos de tarjeta física (`280...`), y rechazo de códigos ajenos.
- **Timeouts de Red en Capa 2**: Manejo de interrupciones de red, URLs `chrome-error://` o códigos de error HTTP durante la transferencia OAuth.
- **Archivos de Shard Vacíos**: Resiliencia del consolidador anteExcels de shards vacíos, con 0 registros o con encabezados incompletos.
- **Mensajes de Telegram y Excel Malformados**: Caracteres especiales (`<`, `>`, `&`, `"`, `'`), textos extremadamente largos (>3980 chars) que exigen truncado limpio sin romper etiquetas HTML, y formatos numéricos internacionales (`3,00 €`, `3.00 €`, `0,00&nbsp;€`, `1.250,50 €`).

### 3.3 Tier 3: Cross-Feature Combinations (Interacciones Cruzadas)
Pruebas de interacción entre subsistemas acoplados:
- **Combo 1**: `btnPwReset` + Degradación de Capa 1 + Fallback a Capa 2 (desafío de contraseña superado, llegada a Capa 1 con microservicio caído, y resolución definitiva en Capa 2).
- **Combo 2**: Desafío WAF 429 + Disparo de Circuit Breaker + Registro en Cooldown Manager (fallos de IP acumulativos disparan la desconexión segura de la VM y ponen la cuenta en enfriamiento).
- **Combo 3**: Partición Matricial (Shards) + Fallos Parciales de Worker + Consolidación Pass 1 + Cola Pass 2 + Recálculo de Top 10.
- **Combo 4**: Instrumentación de capturas sistemáticas en cascada de errores sin fugas de descriptores de archivo ni bloqueos en disco.
- **Combo 5**: Generación concurrente de Excel de 6 hojas y reporte Telegram bajo mezclas heterogéneas de errores y éxitos.

### 3.4 Tier 4: Real-World Application Scenarios (Simulaciones de Aplicación Real)
Simulaciones completas e integrales de extremo a extremo:
- **Escenario 1 (Lote 512 Cuentas)**: Simulación estocástica del procesamiento de 512 cuentas repartidas en 7 shards, verificando consolidación global, erradicación de falsos ceros y balance acumulado.
- **Escenario 2 (Integridad Top 10)**: Extracción del Top 10 entre cientos de cuentas, verificando desempate, orden estrictamente decreciente y tope de 10 elementos.
- **Escenario 3 (Generación de Excel 6 Hojas)**: Creación de archivo `.xlsx` real con datos sintéticos representativos, validación de schemas de columnas y comprobación de integridad de hojas.
- **Escenario 4 (Notificación Telegram Sanitizada)**: Renderizado del mensaje final de Telegram con estadísticas, Top 10 y validación contra oráculo HTML estricto.
- **Escenario 5 (Ciclo de Vida Cuenta Testigo Noelia)**: Recreación exacta del flujo de `noelia_gll@hotmail.com` desde login, detección de banner de degradación, salto a `miportal`, captura de 3,00 € y tarjeta `4003009301402`, consolidación en Hoja 2 y ascenso al Top 10.

---

## 4. Umbrales de Calidad y Criterios de Aceptación (Quality Gates)

| Métrica | Umbral Requerido | Mecanismo de Verificación |
|---------|------------------|---------------------------|
| **Tasa de Aprobación de Tests** | **100% Verde (0 fallos, 0 errores)** | `pytest tests/test_e2e_requirements.py -q` |
| **Tiempo de Ejecución Total** | **< 60 segundos** | Cronometrado vía runner de pytest |
| **Dependencia de Red Externa** | **0 peticiones salientes** | Mocks locales de socket/requests/urllib |
| **Dependencia de Chrome/Browser** | **0 procesos Chrome vivos** | Drivers virtuales en memoria |
| **Validación HTML Telegram** | **100% etiquetas balanceadas y caracteres sanitizados** | Oráculo `StrictTelegramHTMLOracle` |
| **Integridad de Excel** | **6 hojas estructuradas y desduplicación estricta** | Validación con `pandas` / `openpyxl` en memoria |
| **Compatibilidad de Plataforma** | **Windows 10/11 y Linux Ubuntu (CI/CD)** | Manejo multiplataforma de rutas (`os.path.join`) y codificación UTF-8 |

---

## 5. Instrucciones de Ejecución

Para ejecutar la suite completa de pruebas de requisitos E2E de forma determinista y offline:

```powershell
python -m pytest tests/test_e2e_requirements.py -v
```

Para verificar conjuntamente la suite canónica de 47 tests unitarios y la suite E2E:

```powershell
python -m pytest tests/test_circuit_breaker.py tests/test_cooldown_manager.py tests/test_matrix_calc.py tests/test_merge_and_retry.py tests/test_e2e_requirements.py -q
```
