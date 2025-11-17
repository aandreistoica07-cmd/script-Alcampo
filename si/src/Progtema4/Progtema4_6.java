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
public class Progtema4_6 {

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String frase;
        do {
            System.out.print("Introduce una frase de maximo 80 caracteres:");
            frase = sc.nextLine();
            frase = frase.toLowerCase();
            if (frase.length() > 80) {
                System.out.println("Error: La frase tiene mas de 80 caracteres");
            }
        } while (frase.length() > 80);
        int V = 0;
        int C = 0;
        int N = 0;
        int CN = 0;

        for (int i = 0; i < frase.length(); i++) {
            char c = frase.charAt(i);

            if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u') {
                V++;
            } else if (c >= 'a' && c <= 'z' || c == 'ñ') {
                C++;
            } else if (c >= '0' && c <= '9') {
                N++;
            } else {
                CN++;
            }
        }
        System.out.println("Vocales: " + V);
        System.out.println("Consonantes: " + C);
        System.out.println("Numeros: " + N);
        System.out.println("No conocidos: " + CN);
    }

}
