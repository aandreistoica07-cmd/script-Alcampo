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
public class Progtema3_8 {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int N;
        
        
        // 1. Filtrar la entrada (N debe ser mayor que 0)
        do {
            System.out.print("Introduce un número entero N (debe ser > 0): ");
            N = scanner.nextInt();

            if (N <= 0) {
                System.out.println("Error: El factorial solo se calcula para números mayores que cero. Inténtalo de nuevo.");
            }
        } while (N <= 0); // Repetir mientras N no sea mayor que 0
        

        // 2. Inicializar variables para el cálculo
        // Usamos 'long' en lugar de 'int' para evitar desbordamiento 
        // con números factoriales grandes (ej. 13! ya excede el int).
        int factorial = 1;

        // 3. Calcular el factorial
        // La definición es N * (N-1) * ... * 1
        for (int i = 1; i <= N; i++) {
            factorial = factorial * i;
        }

        // 4. Mostrar el resultado
        System.out.println("El número introducido es N = " + N);
        System.out.println("El factorial de " + N + " (" + N + "!) es: " + factorial);
    }
}

