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
public class Progtema4_2 {

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        //La frase a utilizar 
        System.out.print("Introduce una palabra: ");
        String frase = sc.nextLine();
        //SOLUCIÓN
        //Filtro para no mas de 80 caracteres
        if (frase.length() >= 80) {
            System.out.print("Maximo 80 caracteres");
        } else {
            int mays = 0;
            int mins = 0;
            for (int i = 0; i < frase.length(); i++) {
                char c = frase.charAt(i); // charAt()

                if (c >= 'A' && c <= 'Z' || c == 'Ñ') {
                    mays++;
                } else if (c >= 'a' && c <= 'z' || c == 'ñ') {
                    mins++;
                } else {
                    System.out.println("Caracter no conocido");
                }
            }
            System.out.println("Mayúsculas: " + mays);
            System.out.println("Minúsculas: " + mins);
        }
    }
}
