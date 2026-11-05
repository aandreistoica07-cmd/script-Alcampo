# QR Club Alcampo

Objetivo vigente (pendiente): seleccionar una cuenta en el dashboard, iniciar su sesión en el navegador del usuario y llegar a su tarjeta en la web oficial. La generación local de QR descrita abajo es un trabajo previo y no cumple por sí sola este objetivo.

## Autenticación: evidencia y límite actual

La prueba interactiva con la cuenta elegida por el usuario llegó desde el inicio de sesión oficial a `/es/cuenta/fidelidad`, con el QR visible. No se ha implementado todavía el cambio de cuenta desde el dashboard.

La documentación de Salesforce distingue dos mecanismos:

- `login_hint` permite sugerir un usuario; con una sesión existente no selecciona otra cuenta por sí solo. En Experience Cloud se combina con `prompt=login`, que exige autenticarse de nuevo. Esto no es un inicio automático.
- El flujo Headless Identity de credenciales requiere una integración de cliente configurada y autorizada. No hay evidencia de que el dashboard disponga de esa configuración ni de que Alcampo lo habilite para esta aplicación.

Fuentes: https://help.salesforce.com/s/articleView?id=xcloud.remoteaccess_oauth_web_server_flow.htm&language=en_US&type=5 y https://help.salesforce.com/s/articleView?id=sf.remoteaccess_authorization_code_credentials_flow.htm&language=en_US&type=5

No se deben reutilizar códigos OAuth, extraer cookies de una sesión, ni tratar el callback del cliente oficial como una API de transferencia de sesiones. Ver código de callback en el bundle no acredita autorización para una integración propia. La siguiente validación es determinar si existe un mecanismo admitido para este dashboard, manteniendo el inicio de sesión en el navegador de destino.

## Fuente comprobada el 28 de octubre de 2026

- Portal: https://www.miportal.alcampo.es/es/cuenta/fidelidad
- Aplicación pública: https://www.miportal.alcampo.es/assets/js/app.e89eb240.js
- SHA-256 del archivo inspeccionado: `b2db5af7c30d9ef44d7d1dcea517273f4c0eaee0d13a56458ad5f96fffc4203b`.
- El getter `qrCode` concatena `?clif=` y `account.cardNumberAuchan`.
- El componente `qrcode-vue` recibe ese valor y el nivel de corrección `H`.

No se encontró la necesidad de una API que genere un token dinámico para este QR. Esto describe la versión inspeccionada del portal; debe revisarse si Alcampo cambia su formato.

## Implementación

`clubQrPayload` y `renderClubQr` centralizan el formato. Modal, generador manual, catálogo y pantalla completa utilizan el mismo contenido. El código de barras conserva solo el número de tarjeta.

El botón «QR Club» abre directamente la pantalla completa. Si falta el número, se ofrece introducir el de la tarjeta real o abrir la sección de fidelidad del portal. Ese enlace utiliza la sesión que el usuario tenga en Alcampo; no inicia sesión automáticamente ni selecciona la cuenta del dashboard.

Se eliminan los generadores de números aleatorios, los números de ejemplo usados como fallback y la creación de tarjetas a partir del email. Los overrides locales que coinciden con el antiguo generador se ignoran sin borrar el almacenamiento del navegador. Las correcciones manuales restantes se conservan. No se envían tarjetas a servicios externos para dibujar los QR.

## Verificación

- `node tests/test_dashboard_ui.cjs`: sintaxis y regresiones existentes en ambas copias.
- `node tests/test_club_qr.cjs`: contenido, acciones de apertura, ausencia de tarjeta, overrides antiguos y fallo del dibujado; sin cuentas reales, red ni escrituras remotas.
- Comprobación puntual contra el getter descargado de la aplicación oficial: mismo contenido para una tarjeta ficticia de prueba.
- Codificación con QRCode.js 1.0.0 y decodificación independiente con ZXing: se recupera exactamente el contenido esperado, incluido `?clif=`.
- Navegador local: apertura desde el botón, QR visible a pantalla completa y medidas móviles de 390 × 844; alternativa sin tarjeta disponible.

El formato y el dibujo se han verificado. No se ha probado una transacción ni la aceptación por un lector de caja físico. Los cambios quedan en local, sin commit ni despliegue.
