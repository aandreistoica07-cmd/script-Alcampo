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
public class Progtema3_3 {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.println("Ingresa un número entero N para calcular sus divisores propios:");
        int N = scanner.nextInt();
        
        // Los divisores propios solo existen para números mayores que 1
        if (N <= 1) {
            System.out.println("El numero " + N + " no tiene divisores propios.");
        }

        System.out.println("Los divisores propios de " + N + " son:");
        // Un divisor propio es cualquier número que divide a N, excepto N
        // El bucle empieza en 1 (el divisor más pequeño)
        for (int i = 1; i < N; i++) {
            
            // La condición clave: Si el resto de la división (N % i) es 0
            if (N % i == 0) {
                System.out.println(i);
            }
        }
    }
}
