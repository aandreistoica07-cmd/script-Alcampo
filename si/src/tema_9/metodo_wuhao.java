package tema_9;

public class metodo_wuhao {

    public static void wuhao(int[] u) {
        for (int i = 0; i < u.length; i++) {
            int menor = i;
            for (int j = i + 1; j < u.length; j++) {
                if (u[menor] > u[j]) {
                    menor = j;
                }
            }
            int aux = u[menor];                 //swap --> aux = a ; a = b; b = aux
            u[menor] = u[i];
            u[i] = aux;
        }
    }

    public static void main(String[] args) {
           // 1. Tamaño manejable para este algoritmo lento
        int tamano = 10000; 
        int[] vector = new int[tamano];

        // 2. Llenar el vector con números aleatorios
        System.out.println("Generando números...");
        for (int i = 0; i < vector.length; i++) {
            vector[i] = (int)(Math.random() * 1000);
        }

        // 3. Medir tiempo y ORDENAR (Una sola vez)
        System.out.println("Ordenando...");
        long inicio = System.currentTimeMillis();
        
        wuhao(vector); // <--- Aquí ordenamos todo el vector
        
        long fin = System.currentTimeMillis();

        // 4. MOSTRAR el vector ordenado
        System.out.println("--- VECTOR ORDENADO ---");
        for (int i = 0; i < vector.length; i++) {
            System.out.print(vector[i] + " ");
            // Salto de línea cada 20 números para que se vea limpio
            if ((i + 1) % 20 == 0) System.out.println();
        }

        System.out.println("\n-----------------------");
        System.out.println("Tiempo total: " + (fin - inicio) + " ms");
    }
}
