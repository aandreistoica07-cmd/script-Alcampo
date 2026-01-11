/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package Progtema4;

import java.util.Scanner;
/**
 *
 * @author stoica25
 */
public class Progtema4_10 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        int hombresC1 = 0;
        int mujeresC1 = 0;
        int hombresC2 = 0;
        int mujeresC2 = 0;
        int codigosCorrectos = 0;

        String codigo;

        System.out.println("Ingrese códigos de 8 caracteres (00000000 para terminar):");
        
        do {
            System.out.print("Código: ");
            codigo = teclado.nextLine();
            
            if (!codigo.equals("00000000")) {
                boolean esValido = true;
                
                // Verificar longitud
                if (codigo.length() != 8) {
                    esValido = false;
                }
                
                // Verificar que los primeros 4 caracteres sean dígitos
                if (esValido) {
                    for (int i = 0; i < 4; i++) {
                        if (!Character.isDigit(codigo.charAt(i))) {
                            esValido = false;
                        }
                    }
                }
                
                // Convertir y verificar el año
                if (esValido) {
                    int ano = Integer.parseInt(codigo.substring(0, 4));
                    if (ano < 1990 || ano > 1995) {
                        esValido = false;
                    }
                }
                
                // Verificar sexo
                if (esValido) {
                    char sexo = codigo.charAt(4);
                    if (sexo != 'H' && sexo != 'M') {
                        esValido = false;
                    }
                }
                
                // Verificar curso
                if (esValido) {
                    char cursoChar = codigo.charAt(5);
                    if (cursoChar != '1' && cursoChar != '2') {
                        esValido = false;
                    }
                }
                
                // Si es válido, contar
                if (esValido) {
                    codigosCorrectos++;
                    char sexo = codigo.charAt(4);
                    int curso = Character.getNumericValue(codigo.charAt(5));
                    
                    if (sexo == 'H') {
                        if (curso == 1) {
                            hombresC1++;
                        } else if (curso == 2) {
                            hombresC2++;
                        }
                    } else if (sexo == 'M') {
                        if (curso == 1) {
                            mujeresC1++;
                        } else if (curso == 2) {
                            mujeresC2++;
                        }
                    }
                } else {
                    System.out.println("Código rechazado: no cumple las condiciones.");
                }
            }
        } while (!codigo.equals("00000000"));
        
        System.out.println("\n========== INFORME FINAL ==========");
        System.out.println("Códigos correctos leídos: " + codigosCorrectos);
        System.out.println("\nCURSO 1:");
        System.out.println("  Hombres: " + hombresC1);
        System.out.println("  Mujeres: " + mujeresC1);
        System.out.println("\nCURSO 2:");
        System.out.println("  Hombres: " + hombresC2);
        System.out.println("  Mujeres: " + mujeresC2);
        System.out.println("===================================");
        
        teclado.close();
    }
}