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
public class Progtema4_9chat {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String c; // Código
        boolean pC = false; // Pidiendo Códigos
        int h1 = 0, h2 = 0, m1 = 0, m2 = 0, cc = 0; // Contadores

        System.out.println("Salida: '00000000'");
        
        do {
            System.out.print("Codigo: ");
            c = sc.nextLine();
            
            if (pC) {
                boolean v = true; // Válido
                
                if (c.length() != 8) v = false;
                
                if (v) {
                    String aStr = c.substring(0, 4);
                    for (int i = 0; i < 4; i++) {
                        if (!Character.isDigit(aStr.charAt(i))) v = false;
                    }
                    
                    if (v) {
                        int a = Integer.parseInt(aStr); 
                        if (a < 1990 || a > 1995) v = false;
                    }
                }
                
                if (v) {
                    char sx = c.charAt(4); // Sexo
                    char cur = c.charAt(5); // Curso
                    
                    if (sx != 'H' && sx != 'M') v = false;
                    if (cur != '1' && cur != '2') v = false;
                }
                
                if (v) {
                    cc++;
                    System.out.println("ACEPTADO.");
                    char sx = c.charAt(4);
                    char cur = c.charAt(5);

                    if (sx == 'H') {
                        if (cur == '1') h1++; else h2++;
                    } else { 
                        if (cur == '1') m1++; else m2++;
                    }
                } else {
                    System.out.println("RECHAZADO.");
                }
            }
        } while (pC); 
        
        
        System.out.println("\n--- INFORME ---");
        System.out.println("Total correctos: " + cc);
        System.out.println("H-C1: " + h1 + ", H-C2: " + h2);
        System.out.println("M-C1: " + m1 + ", M-C2: " + m2);
    }
}