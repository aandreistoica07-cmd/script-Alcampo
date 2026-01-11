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
public class Progtema3_2 {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int N;

        //Lectura
        do {
            System.out.println("Ingresa un número N para la tabla (entre 1 y 10):");
            N = scanner.nextInt(); // Lee el numero

            if (N < 1 || N > 10) {
                System.out.println("¡Número inválido! Debe estar entre 1 y 10.");
            }
            
        } while (N < 1 || N > 10); // Repite si N está fuera del rango

        //Generación de la Tabla
        System.out.println("TABLA DE MULTIPLICAR DE: " + N);
        
        // Bucle 'for' para calcular N * i, desde i=1 hasta i=10
        for (int i = 1; i <= 10; i++) {
            // Imprime el resultado en el formato solicitado
            System.out.println(N + " * " + i + " = " + (N * i));
        }
    }
}
        
    

