/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package Progtema3;

import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 */
public class Progtema3_6 {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        
        // Variables para almacenar las sumas
        int sumaImpar = 0; // Suma de números en posiciones 1ª, 3ª, 5ª, ...
        int sumaPar = 0;   // Suma de números en posiciones 2ª, 4ª, 6ª, ...
        
        // Contador para saber la POSICIÓN (lugar) del número actual. Empieza en 1.
        int posicion = 1; 
        
        int numeroLeido;
        System.out.println("Introduce números enteros. La serie termina con 0.");

        // El bucle se ejecuta al menos una vez
        do {
            System.out.print("Introduce el número en la posición " + posicion + ": ");
            numeroLeido = scanner.nextInt();

            // 1. Condición de Salida: Si es 0, no se procesa, solo se usa para salir.
            if (numeroLeido != 0) {
                
                // 2. Comprobar la Posición
                // Si la posición dividida por 2 tiene RESTO diferente de 0, es IMPAR (1, 3, 5, 7...)
                if (posicion % 2 != 0) { 
                    sumaImpar += numeroLeido;
                } 
                // Si el resto es 0, es PAR (2, 4, 6, 8...)
                else { 
                    sumaPar += numeroLeido;
                }
                
                // 3. Incrementar el contador de posición para el siguiente número
                posicion++;
            }
            
        } while (numeroLeido != 0); // El bucle se repite mientras el número leído NO sea 0


        System.out.println("FIN de la entrada de datos.");
        
        // Escribir los resultados
        System.out.println("Suma de números en POSICIÓN IMPAR (1ª, 3ª, 5ª, etc.): " + sumaImpar);
        System.out.println("Suma de números en POSICIÓN PAR (2ª, 4ª, 6ª, etc.):   " + sumaPar);
        // La posición final menos 1 da el total de números introducidos sin contar el 0
        System.out.println("Total de números introducidos: " + (posicion - 1));
    }
}