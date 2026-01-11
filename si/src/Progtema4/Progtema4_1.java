/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package Progtema4;

import java.util.Scanner;

/**
 *
 * @author alvarezherrera25
 */
public class Progtema4_1 {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        //La frase a utilizar 
        System.out.print("Introduce una palabra: ");
        String frase = sc.nextLine();

        //Filtro para no mas de 80 caracteres
        if (frase.length() <= 80) {

            System.out.println("Impresión progresiva de: " + frase );

            //El bucle 'for' desde 1 hasta la longitud total.
            for (int i = 1; i <= frase.length(); i++) {
                // Imprime la subcadena desde el índice 0 hasta el índice i (exclusivo).
                System.out.println(frase.substring(0, i));
            }
        } else {
            System.out.println("No pueden ser mas de 80 caracteres");
        }

    }
}