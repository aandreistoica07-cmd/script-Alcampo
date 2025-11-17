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
public class Progtema4_5 {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String frase;
        do {
            System.out.print("Introduce una frase de maximo 80 caracteres:");
            frase = sc.nextLine();
            if (frase.length() > 80) {
                System.out.println("Error: La frase tiene mas de 80 caracteres");
            }
        } while (frase.length() > 80);
        String letraPar = "";
        String letraImpar = "";

        for (int i = 0; i < frase.length(); i++) {
            // Obtenemos el carácter en la posición actual
            char caracter = frase.charAt(i);

            // Verificamos si el índice (i) es par o impar
            if (i % 2 == 0) {
                // Si el resto de dividir el índice entre 2 es 0, es PAR.
                letraPar += caracter;
            } else {
                // Si el resto no es 0, es IMPAR.
                letraImpar += caracter;
            }
        }

        // Resultado

        System.out.println("Frase original:  " + frase);
        System.out.println("Letras Posicion PAR:   " + letraPar);
        System.out.println("Letras Posicion IMPAR: " + letraImpar);
    }
}