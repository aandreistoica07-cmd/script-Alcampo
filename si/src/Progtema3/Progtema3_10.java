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
public class Progtema3_10 {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        
        System.out.print("Introduce un número entero N: ");
        int N = sc.nextInt();
        int sigue = N+1;
        boolean primo = true;
        while (primo){
            primo = false;
            for (int i = 2; i < N; i++) {
                if (sigue % i == 0) {
                    primo = true;
                }
            }
            if (primo){
                sigue++;
            }
        
        }  
        System.out.print("El primo mas cercano es: " + sigue);
    }
}    