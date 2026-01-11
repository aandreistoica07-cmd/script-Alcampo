# Neural Paint: Handwriting AI

Una red neuronal interactiva para el reconocimiento de dígitos manuscritos (Dataset MNIST).
Esta versión utiliza una implementación de Red Neuronal **desde cero** con NumPy, sin librerías pesadas como TensorFlow.

## Instalación

1. Instala las dependencias:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Ejecución

1. Inicia el servidor:
   ```bash
   python app.py
   ```
2. La primera vez que lo inicies, descargará automáticamente el dataset MNIST (11MB).
3. Abre tu navegador en: `http://127.0.0.1:5000`

## Cómo usarlo

1. **Dibuja** un número (0-9) en el recuadro grande.
2. Haz clic en **Predict** para ver qué piensa la IA.
   - *Nota: Al principio la IA no sabe nada y adivinará al azar.*
3. Haz clic en **Start Training**.
   - Verás cómo baja el error (Loss) y sube la precisión (Accuracy) en tiempo real en las gráficas.
   - La IA está aprendiendo de 60,000 imágenes de ejemplo.
4. Intenta dibujar de nuevo mientras entrena (o detenlo cuando la precisión sea alta, >90%).
