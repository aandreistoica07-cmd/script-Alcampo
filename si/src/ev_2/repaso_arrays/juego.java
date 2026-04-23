package repaso_arrays;

import java.util.Scanner;

public class juego {
    public static void jugar(int n) {
    if (n < 2) {
        System.out.println("No hay suficientes jugadores.");
        return;
    }

    // 1. CREAR RECIPIENTES (Variables)
    int[][] matrizJugadores = new int[n][4];
    int[] numArbitro = new int[2];

    // 2. RELLENAR (Llamada a Comunicación)
    rellenarMatriz(matrizJugadores);
    System.out.println("--- Turno del Árbitro ---");
    numArbitro[0] = validarnumeros(1, 10);
    numArbitro[1] = validarnumeros(1, 10);

    // 3. PROCESAR (Llamada a Calculadoras)
    int[] resultados = calcularPuntos(matrizJugadores, numArbitro);
    int posicionGanador = obtenerGanador(resultados);
    
    // 4. MOSTRAR (Llamada a Salida)
    presentarResultados(resultados, posicionGanador);
}

    

    public static void rellenarMatriz(int matriz[][]) {

       for (int i = 0; i < matriz.length; i++) {
            // Cambio solicitado: Mensaje claro de qué jugador está ingresando datos
            System.out.println("\n---------------------------------");
            System.out.println("SISTEMA: Turno del JUGADOR " + (i + 1));
            System.out.println("---------------------------------");
            
            for (int j = 0; j < matriz[i].length; j++) {
                System.out.print("Jugador " + (i + 1) + " - Valor #" + (j + 1) + " -> ");
                matriz[i][j] = validarnumeros(1, 10);
            }
        }
        }

    


    public static int validarnumeros(int min, int max) {
        Scanner sc = new Scanner(System.in);
        int num = 0;
        do {
            System.out.print("Introduce número (" + min + "-" + max + "): ");
            num = sc.nextInt();
        } while (num < min || num > max); // Solo se preocupa de validar
        return num;
    }

    public static int[] calcularPuntos(int[][] matriz, int[] arbitro) {
    int[] resultados = new int[matriz.length]; // Un hueco por jugador
    
    // Determinamos el min y max del arbitro para no repetir ifs
    int min = Math.min(arbitro[0], arbitro[1]);
    int max = Math.max(arbitro[0], arbitro[1]);

    for (int i = 0; i < matriz.length; i++) {
        int aciertos = 0;
        for (int j = 0; j < matriz[i].length; j++) {
            if (matriz[i][j] >= min && matriz[i][j] <= max) {
                aciertos++;
            }
        }
        resultados[i] = aciertos; // Guardamos los puntos del jugador i
    }
    return resultados; // Devolvemos el array con todos los puntos
}

public static int obtenerGanador(int[] puntos) {
    int maxPuntos = puntos[0];
    int indiceGanador = 0;
    for (int i = 1; i < puntos.length; i++) {
        if (puntos[i] > maxPuntos) {
            maxPuntos = puntos[i];
            indiceGanador = i;
        }
    }
    return indiceGanador; // Solo devuelve el número del jugador
}

public static void presentarResultados(int[] puntos, int ganador) {
    System.out.println("\n--- RESULTADOS FINALES ---");
    
    // Mostramos los puntos de cada uno
    for (int i = 0; i < puntos.length; i++) {
        System.out.println("Jugador " + i + ": " + puntos[i] + " aciertos.");
    }
    
    // Anuncio del ganador
    System.out.println("\n*******************************");
    System.out.println("¡EL GANADOR ES EL JUGADOR " + ganador + "!");
    System.out.println("Con un total de " + puntos[ganador] + " puntos.");
    System.out.println("*******************************");
}
public static void main(String[] args) {
    jugar(3);
}


}
