/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package Progtema3;

import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 * 27/10/2025
 */
public class Proftema3_5 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        
        // Variables para almacenar la suma y la cantidad
        int sumaTotal = 0;
        int contadorNumeros = 0;
        int numeroLeido;

        System.out.println("Introduce números enteros. El programa terminará cuando ingreses un 0.");

        // Usamos un bucle do-while para asegurar que al menos se pide un número
        // y para que la condición se evalúe después de cada lectura.
        do {
            System.out.print("Introduce un número: ");
            numeroLeido = teclado.nextInt();

            // Verificamos si el número leído NO es cero.
            if (numeroLeido != 0) {
                // Si no es cero, lo añadimos a la suma y contamos el número.
                sumaTotal += numeroLeido; // sumaTotal = sumaTotal + numeroLeido;
                contadorNumeros++;
            }
            
        } while (numeroLeido != 0); // El bucle continúa mientras el número leído NO sea 0



        System.out.println("FIN de la introducción de números (se ingresó 0).");
        
        // Escribir los resultados
        System.out.println("Suma total de los números: " + sumaTotal);
        System.out.println("Total de números introducidos (sin contar el 0): " + contadorNumeros);
    }
}