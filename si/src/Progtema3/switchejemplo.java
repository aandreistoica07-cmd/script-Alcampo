/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package Progtema3;

import java.util.Scanner;

/**
 *
 * @author alvarezherrera25
 */
public class switchejemplo {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int O;
        
         System.out.println("--Calcular Area--");
         System.out.println("1-Triangulo");
         System.out.println("2-Cuadrado");
         System.out.println("3-Rectagulo");
         System.out.println("Elegir opcion: ");
         O = sc.nextInt();
         
         switch (O) {
            case 1:
                System.out.println("Introduce lado base");
                float TB = sc.nextInt();
                System.out.println("Introduce lado altura");
                float TA = sc.nextInt();
             
                System.out.println("El area del triangulo es: " + ((TB*TA)/2) );
            break;
            
            case 2: 
                System.out.println("Introduce lado");
                int CL = sc.nextInt();

                System.out.println("El area del cuadrado es: " + (CL*CL));
            break;
            
            case 3:
                System.out.println("Introduce lado base");
                float RB = sc.nextInt();
                System.out.println("Introduce lado altura");
                float RA = sc.nextInt();
             
                System.out.println("El area del triangulo es: " + (RB*RA) ); 
            break;
            
            default: 
                System.out.println("Numero del 1-3"); 
            break;
        }
    }
}