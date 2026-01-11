/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package si;

import java.util.Scanner;

/**
 * Convierte letras de una palabra/frase en su dígito telefónico
 * equivalente (similar a T9), manteniendo otros caracteres.
 * El programa termina al introducir '0'.
 *
 * @author alvarezherrera25
 */
public class ProgDigito2 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        
        boolean fin = false; 
        
        System.out.println("Introduce palabras o frases. El programa terminará si introduces SÓLO el carácter '0'.");

        while (!fin) {
            
            System.out.print("Introduce una palabra/frase o '0' para terminar: ");
            String entrada = teclado.nextLine().trim();
            
            if (entrada.equals("0")) {
                System.out.println("Programa finalizado por la entrada del carácter '0'.");
                fin = true; 
            }

            else {
                //acumulador
                String resultadoDigitos = "";
                //una vez por cada carácter de la cadena
                for (int i = 0; i < entrada.length(); i++) {
                //toma el carácter que se encuentra en la posición actual
                    char letraActual = entrada.charAt(i);
                //convierte la letra actual a mayúscula
                    char mayuscula = Character.toUpperCase(letraActual);
                    char digito;


                    digito = switch (mayuscula) {
                        case 'A', 'B', 'C' -> '2';
                        case 'D', 'E', 'F' -> '3';
                        case 'G', 'H', 'I' -> '4';
                        case 'J', 'K', 'L' -> '5';
                        case 'M', 'N', 'O' -> '6';
                        case 'P', 'Q', 'R', 'S' -> '7';
                        case 'T', 'U', 'V' -> '8';
                        case 'W', 'X', 'Y', 'Z' -> '9';
                        // Mantenemos el carácter original si no es una letra
                        default -> letraActual; 
                    };
                    

                    resultadoDigitos = resultadoDigitos + digito; 
                }

                System.out.println("Dígitos resultantes para '" + entrada + "': " + resultadoDigitos);
                
            }
        }
        
        teclado.close();
    }
}


//contador = 1;
//fin = contador <= 10;
//while (! fin ){
//cuerpo
//fin = ++contador <= 10;