/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package si;

import java.util.Scanner;

/**
 *
 * @author alvarezherrera25
 */
public class ProgDigito {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        
        // Iniciamos contador
        int contador = 1;
        
        // Bucle hasta 10
        while (contador <= 10) {
            
            // Introducimos dígito
            System.out.print("Introduce una letra (" + contador + "/10): ");
            String entrada = teclado.nextLine().trim();
            
            
            // Coger la primera
            char letra = entrada.charAt(0);
            char mayuscula = Character.toUpperCase(letra);
            char digito;

            // Lógica de conversión (anteriormente en letraADigito)
            // AHORA DIRECTAMENTE EN EL MAIN (SIN SEPARAR EN OTRO MÉTODO)
            digito = switch (mayuscula) {
                case 'A', 'B', 'C' -> '2';
                case 'D', 'E', 'F' -> '3';
                case 'G', 'H', 'I' -> '4';
                case 'J', 'K', 'L' -> '5';
                case 'M', 'N', 'O' -> '6';
                case 'P', 'Q', 'R', 'S' -> '7';
                case 'T', 'U', 'V' -> '8';
                case 'W', 'X', 'Y', 'Z' -> '9';
                default -> '0';
            };

            // Imprimimos el resultado
            if (digito != '0') {
                System.out.println(" La letra '" + letra + "' corresponde al dígito: " + digito);
            } else {
                System.out.println("ERROR: El carácter '" + letra + "' no es una letra del alfabeto (A-Z).");
            }
            
            contador++;
        }
        
        System.out.println("Se han completado las 10 entradas. Programa finalizado.");
        teclado.close();
    }
}


//contador = 1;
//while (contador <=10) {

