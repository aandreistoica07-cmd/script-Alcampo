/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package Progtema4;

import java.util.Scanner;
/**
 *
 * @author alvarezherrera
 */
public class Progtema4_4 {
    public static void main(String[] args) {

        Scanner scanner = new Scanner(System.in);

        // 1. Leer la cadena
        System.out.println("Introduce una cadena:");
        String cadena = scanner.nextLine();

        // 2. Leer la opción (M o m)
        System.out.print("Opción ('M' = MAYUSCULAS, 'm' = minusculas): ");
        // Leemos la línea completa y tomamos solo el primer carácter
        char opcion = scanner.nextLine().charAt(0);

        String resultado;

        // 3. Procesar y 4. Imprimir
        if (opcion == 'M') {
            resultado = cadena.toUpperCase();
        } else if (opcion == 'm') {
            resultado = cadena.toLowerCase();
        } else {
            System.out.println("Opción no válida. Mostrando original.");
            resultado = cadena;
        }

        System.out.println("Resultado: " + resultado);
    }
}