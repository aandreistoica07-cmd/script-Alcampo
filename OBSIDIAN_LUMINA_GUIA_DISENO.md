# Sistema de Diseño Obsidian Lumina (Stitch MCP)
## Arquitectura de Modo Oscuro para Alcampo Analytics & Proyectos React

Este documento describe la arquitectura visual, tokens cromáticos y componentes creados mediante el **MCP de Stitch** y aplicados al ecosistema de **Alcampo Analytics**.

---

### 1. Filosofía Visual y Paleta Cromática OLED

El sistema **Obsidian Lumina** está optimizado para paneles OLED, eliminando reflejos en los bordes y fatiga cognitiva mediante:
* **Lienzo Base (Canvas Void):** `#090B10` (negro obsidiana puro con contraste absoluto).
* **Superficies Estructurales:** `#0F121C` (pozo de herramientas) y `#151A28` (tarjetas elevadas).
* **Paneles Glassmorphism:** `rgba(22, 27, 43, 0.72)` con `backdrop-filter: blur(20px) saturate(180%)` y borde especular `1px solid rgba(255, 255, 255, 0.08)`.
* **Rejilla OLED:** Textura milimétrica de 32px (`.bg-grid-pattern`) con trazos sutiles de `rgba(255, 255, 255, 0.035)`.

#### Acentos Neón & Estado:
* **Electric Cyan (`#00F2FE` / `#38BDF8`):** Foco primario, balizas activas y botones de acción principal.
* **Luminous Lilac (`#A78BFA` / `#CEBDFF`):** Nodos secundarios, selectores y badges temáticos.
* **Soft Mint (`#34D399` / `#5FF4B7`):** Métricas óptimas, saldo positivo y 60 FPS feedback.
* **Vibrant Coral (`#F43F5E`):** Alertas de error, cuentas bloqueadas y controles de ventana macOS.
* **Neon Amber (`#FBBF24`):** Advertencias y estados en progreso.

---

### 2. Componentes React + Tailwind Transferidos
Ubicación en este repositorio: `./components-react-dark/`

1. **`DarkNavbar.tsx`**: Barra flotante en cristal oscuro con cápsula de búsqueda `⌘K`, píldora *Dark Edition* y botón con gradiente cian-lila.
2. **`DarkHero.tsx`**: Encabezado tipográfico con titular de alto contraste, orbes de luz ambiental y ticker de estadísticas en vivo.
3. **`DarkStudioMockup.tsx`**: Mockup de estudio creativo con sliders reactivos en vivo (*Luminosidad Especular* y *Profundidad Háptica*), paleta de swatches con copiado al portapapeles, ecualizador de audio animado y tarjeta cuántica.
4. **`DarkFeatures.tsx`**: Bento Grid de 3 columnas de *Arquitectura Sensorial* con efectos de elevación al hover y copiado de snippets.
5. **`DarkShowcase.tsx`**: Tarjetas en perspectiva 3D adaptadas al contraste OLED con controles dinámicos.
6. **`DarkCTA.tsx`**: Banner de canal cerrado con formulario interactivo y confirmación animada.
7. **`DarkFooter.tsx`**: Pie de página moderno con píldora de estado operativo del sistema (*Todos los sistemas operativos*).
8. **`CommandPalette.tsx`**: Paleta modal accesible mediante `⌘K` o clic en la barra para búsqueda rápida y copiado de tokens.
9. **`ThemeContext.tsx`**: Contexto React para alternar entre el modo oscuro *Obsidian Lumina* y el modo claro *Modo Serenidad*.
10. **`FloatingThemeToggle.tsx`**: Botón flotante accesible desde cualquier scroll para alternar entre temas.
11. **`CustomCursor.tsx`**: Cursor dinámico que emite un halo fosforescente sobre fondo oscuro.
12. **`obsidian-lumina-tokens.css`**: Archivo de tokens completos de Tailwind v4 y clases de utilidad.

---

### 3. Mejoras Aplicadas al Dashboard de Alcampo (`index.html` & `css/style.css`)

1. **Reemplazo del fondo marino opaco por Obsidian Void (`#090B10`)**:
   * Contraste negro puro para paneles OLED.
   * Textura de rejilla milimétrica añadida en el fondo (`<div class="bg-grid-pattern"></div>`).
2. **Vidrio Especular y Elevación Suave en Tarjetas**:
   * Bordes superiores especulares `inset 0 1px 0 rgba(255, 255, 255, 0.08)`.
   * Sombras de difusión profunda `box-shadow: 0 16px 40px -4px rgba(0, 0, 0, 0.75)`.
   * Efecto hover con micro-elevación `translateY(-3px)` y aura de neón cian.
3. **Selector de Pestañas ("Bien Encuadrada")**:
   * Diseño de cápsula flotante con borde sutil `rgba(255, 255, 255, 0.12)` y fondo ultra oscuro.
   * Pestaña activa con degradado cian-lila y resplandor de neón difuso.
4. **Botón de Iniciar GitHub Actions**:
   * Nuevo estilo neón con degradado `linear-gradient(135deg, #00F2FE 0%, #A78BFA 100%)`, texto oscuro `#090B10` y resplandor cian reactivo al hover.
5. **Tarjetas de Saldo y Métricas**:
   * Valores numéricos en tipografía geométrica de alto impacto (`Geist` / `Outfit`) con tracking ajustado.
   * Saldo acumulado con degradado luminoso cian a lila.
   * Insignias de tendencia en formato píldora circular con borde translúcido.
6. **Tarjetas Digitales del Centro QR**:
   * Fondo con degradado dark glassmorphism y borde cian reactivo al hover.
7. **Barra de Desplazamiento Personalizada**:
   * Scrollbar ultra delgado con pista obsidiana y cursor interactivo con brillo cian.
