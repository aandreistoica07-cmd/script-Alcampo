package Progtema3;



/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */


  import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 * fecha 2025/10/22
 */
    public class Proftema3_1profe {
        public static void main (String[] args){
        Scanner teclado = new Scanner(System.in);
        int A, B, suma = 0 ;

        //Introducimos A y B y comprobamos que (A <= B)
            System.out.println("Introduce A:");
            A = teclado.nextInt();

            System.out.println("Introduce B:");
            B = teclado.nextInt();

            if (A <= B) {
            
            }
            else{
                if (A > B)
                    System.out.println("Error: A debe ser menor o igual que B.");
            }
            
            for ( int i = A + 1; i < B; i++)
                suma = suma + i;
            
                
        //Resultado
        System.out.println("La suma de los enteros entre " + A + " y " + B + " (excluidos) es: " + suma);

        teclado.close();
    }
}   

