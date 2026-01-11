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
public class Progtema3_9 {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        
        System.out.print("Introduce un número entero N: ");
        int N = scanner.nextInt();
        int suma = 0;
        
        for (int i = 1; i < N; i++){
            if (N % i == 0){
            suma += i;
            }
        }
        if (suma == N){
        System.out.println("El nuemro " + N + " es perfecto");
        }else {
        System.out.println("El nuemro " + N + " no es perfecto");
        }
        
    }
}
     