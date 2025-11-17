package Progtema4;

import java.util.Scanner;

public class Progtema4_11 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        String frase;

        System.out.println("introduce una frase");
        frase = teclado.nextLine();
        frase = frase.toUpperCase();
        int[] frecuencia = new int[26];

        for (int i = 0; i < frase.length(); i++) {
            char c = frase.charAt(i);

            if (c >= 'A' && c <= 'z') {
                frecuencia[c - 'A']++;

            }
        }
        System.out.println("\nFrecuencia de letras:");
        int distintas = 0;

        for (int i = 0; i < 26; i++) {
            if (frecuencia[i] > 0) {
                System.out.println((char) (i + 'A') + ": " + frecuencia[i]);
                distintas++;
            }
        }
          System.out.println("\nTotal de letras distintas: " + distintas);
    }
}
