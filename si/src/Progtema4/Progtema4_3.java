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
public class Progtema4_3 {

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        //La frase a utilizar 
        System.out.print("Frase completa: ");
        String frase = sc.nextLine();
        //Palabra a buscar
        System.out.print("Palabra a buscar: ");
        String palabra = sc.nextLine();
        
        int posicion = frase.indexOf(palabra);
        int resultado;
        if (posicion == -1) {
            // Si indexOf devuelve -1 (no encontrada), el resultado es 0.
            resultado = 0;
        } else {
            // Si la encuentra, el resultado es la posición donde empieza
            resultado = posicion;
        }
        
        // 3. Mostrar el resultado
        System.out.println("Resultado de la posicion: " + resultado);
    }
}

    

