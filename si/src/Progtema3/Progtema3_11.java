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
public class Progtema3_11 {

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int N;

        System.out.println("Introduce un numero:");
        N = sc.nextInt();
        for (int i = 2; i <= N; i++) {
            int divisores = 0;

            for (int j = 1; j <= i; j++) {
                if (i % j == 0) {
                    divisores++;
                }
            }
            if (divisores == 2) {
                System.out.println(i);
            }
        }
    }
}
