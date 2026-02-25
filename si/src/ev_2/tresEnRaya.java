import java.util.Scanner;

public class tresEnRaya {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        char[][] tablero = new char[3][3];
        char jugadorActual = 'X';
        boolean finPartida = false;

        // Inicializar tablero con espacios
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                tablero[i][j] = ' ';
            }
        }

        // Bucle principal del juego
        while (!finPartida) {
            int fila = -1, columna = -1;
            boolean casillaVacia = false;

            // Pedir posición hasta que sea válida
            do {
                System.out.println("Jugador " + jugadorActual + ", elige fila (0-2): ");
                fila = teclado.nextInt();
                System.out.println("Jugador " + jugadorActual + ", elige columna (0-2): ");
                columna = teclado.nextInt();

                if (fila >= 0 && fila <= 2 && columna >= 0 && columna <= 2) {
                    if (tablero[fila][columna] == ' ') {
                        tablero[fila][columna] = jugadorActual;
                        casillaVacia = true;
                    } else {
                        System.out.println("Casilla ocupada, elige otra.");
                    }
                } else {
                    System.out.println("Índice fuera de rango. Ingresa un número entre 0 y 2.");
                }
            } while (!casillaVacia);

            // Mostrar tablero q
            for (int i = 0; i < 3; i++) {
                System.out.print("| ");
                for (int j = 0; j < 3; j++) {
                    System.out.print(tablero[i][j] + " | ");
                }
                System.out.println();
                System.out.println("-------------");
            }

            // Comprobar filas y columnas
            for (int i = 0; i < 3; i++) {
                if ((tablero[i][0] == jugadorActual && tablero[i][1] == jugadorActual && tablero[i][2] == jugadorActual) ||
                    (tablero[0][i] == jugadorActual && tablero[1][i] == jugadorActual && tablero[2][i] == jugadorActual)) {
                    System.out.println("¡Gana jugador " + jugadorActual + "!");
                    finPartida = true;
                }
            }

            // Comprobar diagonales
            if (!finPartida) {
                if ((tablero[0][0] == jugadorActual && tablero[1][1] == jugadorActual && tablero[2][2] == jugadorActual) ||
                    (tablero[0][2] == jugadorActual && tablero[1][1] == jugadorActual && tablero[2][0] == jugadorActual)) {
                    System.out.println("¡Gana jugador " + jugadorActual + "!");
                    finPartida = true;
                }
            }

            // Comprobar empate
            if (!finPartida) {
                boolean lleno = true;
                for (int i = 0; i < 3; i++) {
                    for (int j = 0; j < 3; j++) {
                        if (tablero[i][j] == ' ') {
                            lleno = false;
                        }
                    }
                }
                if (lleno) {
                    System.out.println("¡Empate!");
                    finPartida = true;
                }
            }

            // Cambiar jugador
            if (!finPartida) {
                jugadorActual = (jugadorActual == 'X') ? 'O' : 'X';
            }
        }

        teclado.close();
    }
}