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
public class ProgCalc {
        public static void main(String[] args){
            Scanner teclado=new Scanner(System.in);
            int num1,num2,num3,resultado;
            
            System.out.print("Ingrese primer valor:");
            num1=teclado.nextInt();
            System.out.print("Ingrese segundo valor:");
            num2=teclado.nextInt();
            System.out.print("Ingrese tercero valor:");
            num3=teclado.nextInt();
            
            if (num1 < 0) {
            resultado = num1 * num2 * num3;
            
            System.out.println("Números introducidos:");
            System.out.println( "Numero1= " + num1 + "  " + "Numero2= " + num2 + "  " + "Numero3= " + num3 );
            
            System.out.println("El primer número fue negativo. Se calcula el PRODUCTO:");
            System.out.println("Resultado (Producto): " + resultado); 
        } 
            else {
            resultado = num1 + num2 + num3;
            
            System.out.println("Números introducidos:");
            System.out.println( "Numero1= " + num1 + "  " + "Numero2= " + num2 + "  " + "Numero3= " + num3 );
            
            System.out.println("El primer número fue cero o positivo. Se calcula la SUMA:");
            System.out.println("Resultado (Suma): " + resultado);
        }
    }
}