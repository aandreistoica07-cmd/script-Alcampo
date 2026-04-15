package tema_9;

public class Seleccion extends Ordenar {
    @Override
    public void ordenar(int[] vector) {
        
        for (int i = 0; i < vector.length - 1; i++) {
            
            // 1. Al empezar, asumo que el primero de la fila (i) es el más pequeño
            int posicionMenor = i; 
            
            // 2. Empiezo a mirar al resto de la fila (desde el siguiente: i + 1)
            for (int j = i + 1; j < vector.length; j++) {
                
                // 🔥 EL HUECO QUE FALTABA 🔥
                // Si encuentro a alguien AÚN MÁS PEQUEÑO...
                if (vector[j] < vector[posicionMenor]) {
                    // ...me apunto su posición para no olvidarme de dónde está
                    posicionMenor = j;
                }
            }
            
            // 3. Cuando termina el bucle de buscar, ya sé quién es el más pequeño de verdad.
            // Hago el intercambio (swap) para ponerlo en la posición 'i'.
            int aux = vector[i];
            vector[i] = vector[posicionMenor];
            vector[posicionMenor] = aux;
        }
    }
}

