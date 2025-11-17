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
public class Progtema3_4 {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.print("Introduce N: ");
        int N = sc.nextInt();

        // 1. Asumimos que es primo por defecto.
        boolean esPrimo = true;

        // 2. N <= 1 no es primo por definición.
        if (N <= 1) {
            esPrimo = false;
        } 
        
        // 3. Revisamos si tiene divisores aparte de 1 y N.
        // Empezamos en 2 y vamos hasta N-1.
        for (int i = 2; i < N; i++) {
            // Si la división es exacta (resto 0), NO es primo.
            if (N % i == 0) {
                esPrimo = false;
            }
        }

        // 4. Mostrar el resultado.
        if (esPrimo) {
            System.out.println("El número " + N + " es primo.");
        } else {
            System.out.println("El número " + N + " no es primo.");
        }
    }
}