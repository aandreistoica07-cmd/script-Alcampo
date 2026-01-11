/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */


import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 */
public class Progtema4_8 {
    public static void main(String[] args) {
        // Inicializacion
        Scanner sc = new Scanner(System.in);
        
        System.out.print("Introduce la frase a cifrar: ");
        String frase = sc.nextLine();
        frase = frase.toUpperCase();
        String Nfrase = "";

       
        for (int i = 0; i < frase.length(); i++) {
            char c = frase.charAt(i);
            
            if (c >= 'A' && c <= 'Z'){
              char cifrado = (char) ((int)c + 3);
                      
                if (c == 'Z'){
                    cifrado = (char) ((int)cifrado - 26);
                }
                Nfrase += cifrado;
 
            } else {
                System.out.println("Error");
            }
        }
        System.out.println("Frase inicial: " + frase );
        System.out.println("Frase inicial: " + Nfrase );
    }
}