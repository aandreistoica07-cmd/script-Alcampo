package RepasoEV_1;

/**
 * programa que hacer piramides usando for anidados autor stoica25 fecha241125
 *
 *
 * /*
 */
import java.util.Scanner;

public class repaso_14 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        System.out.println("Altura de la pirámide: ");
        int altura = teclado.nextInt();

        System.out.println("que direccion: 1 arriba , 2 abajo , 3 derecha , 4 izquierda");
        int direccion = teclado.nextInt();
        System.out.println("introduce el simbolo");
        char simbolo = teclado.next().charAt(0);
        if (direccion == 1) {

// filas que tiene la piramide //
            for (int filas = 0; filas < altura; filas++) {
                /**
                 * espacios para mover los simbolos espacios bajan 1 por cada
                 * fila --> altura = 4 espacio fila 0 --> 4 - 0 -1 = 3 /*
                 */
                for (int espacios = 0; espacios < altura - filas - 1; espacios++) {
                    System.out.print(" ");
                }
                // simbolos impares por cada fila fila 0 --> 1 ; 3; 5.... //
                for (int simbolos = 0; simbolos < (filas * 2) + 1; simbolos++) {
                    System.out.print("*");
                }
                System.out.println();
            }
        } else if (direccion == 2) {
            for (int filas = 0; filas < altura; filas++) {

                // 1. Espacios: Aumentan con la fila (0, 1, 2...)
                for (int espacios = 0; espacios < filas; espacios++) {
                    System.out.print(" ");
                }

                // 2. Símbolos: Disminuyen (7, 5, 3, 1...)
                // (2*altura - 1) es la base - (2 * filas) es la reducción por fila
                for (int simbolos = 0; simbolos < (2 * altura - 1) - (2 * filas); simbolos++) {
                    // Usamos la variable simbolo que ya capturamos
                    System.out.print(simbolo);
                }
                System.out.println();
            }
        } else if (direccion == 3) {
            // *PARTE 1: Triángulo de arriba (Crece)*//
            for (int filas = 0; filas < altura; filas++) {
                for (int simbolos = 0; simbolos < filas + 1; simbolos++) {
                    System.out.print(simbolo);
                }
                System.out.println();
            }
            // PARTE 2: Triángulo de abajo (Decrece)
            // Usamos 'i' para controlar la cantidad de estrellas
            for (int i = altura - 1; i > 0; i--) {
                for (int j = 0; j < i; j++) { // ¡Aquí está tu solución!
                    System.out.print(simbolo);
                }
                System.out.println();
            }
        } else if (direccion == 4) {
            for (int filas = 0; filas < altura; filas++) {
                for (int espacios = 0; espacios < altura - filas - 1; espacios++) {
                    System.out.print(" ");
                }
                for (int simbolos = 0; simbolos < filas + 1; simbolos++) {
                    System.out.print(simbolo);
                }
                System.out.println();
            }
            //2 parte triangulo que decrece //
            for (int i = altura - 1; i > 0; i--) {
        // Espacios (aumentan: 1, 2, 3...)
        for (int espacios = 0; espacios < altura - i; espacios++) {
            System.out.print(" ");
        }
        // Símbolos (disminuyen: 3, 2, 1...)
        for (int simbolos = 0; simbolos < i; simbolos++) {
            System.out.print(simbolo);
        }
        System.out.println();
    }
}
    }
}
