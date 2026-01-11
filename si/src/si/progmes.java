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
public class progmes {
    public static void main(String[] args){
    Scanner teclado= new Scanner(System.in);
    int numeroMes;
    
    System.out.print("Ingrese un numero del 1-12:");
    numeroMes=teclado.nextInt();
 
    String nombreMes;
    
    nombreMes = switch (numeroMes) {
            case 1 -> "Enero";
            case 2 -> "Febrero";
            case 3 -> "Marzo";
            case 4 -> "Abril";
            case 5 -> "Mayo";
            case 6 -> "Junio";
            case 7 -> "Julio";
            case 8 -> "Agosto";
            case 9 -> "Septiembre";
            case 10 -> "Octubre";
            case 11 -> "Noviembre";
            case 12 -> "Diciembre";
            default -> "inválido.";
        };
     System.out.println("El mes es " + nombreMes);
    }
}
