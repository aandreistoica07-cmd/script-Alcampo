/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package Progtema3;

import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 * fecha 2025/10/22
 */
    public class Progtema3_1 {
        public static void main (String[] args){
        Scanner teclado = new Scanner(System.in);
        int A, B;

        //Introducimos A y B y comprobamos que (A <= B)
        do {
            System.out.println("Introduce A:");
            A = teclado.nextInt();

            System.out.println("Introduce B:");
            B = teclado.nextInt();

            if (A > B) {
                System.out.println("Error: A debe ser menor o igual que B.");
            }
        } while (A > B);
        int suma = 0;
        // El bucle va desde A+1 hasta B-1
        for (int i = A + 1; i < B; i++) {
            suma = suma + i;
        }

        //Resultado
        System.out.println("\nLa suma de los enteros entre " + A + " y " + B + " (excluidos) es: " + suma);

        teclado.close();
    }
} 
