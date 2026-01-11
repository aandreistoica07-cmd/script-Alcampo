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
public class Progtema3_7 {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        
        // Variables
        int sumaTotal = 0;
        int contador = 0;
        int mayor = 0;
        int menor = 0;
        int numeroLeido;
        
        System.out.println("Introduce números enteros. Cero (0) termina la serie.");

        // Leer el primer número para inicializar las variables y entrar al bucle.
        System.out.print("Introduce un número: ");
        numeroLeido = sc.nextInt();

        // Inicializar mayor y menor con el primer número (si no es 0)
        if (numeroLeido != 0) {
            mayor = numeroLeido;
            menor = numeroLeido;
        }

        // Bucle do-while: Se ejecuta MIENTRAS el número leído NO sea 0
        do {
            // El número leído en la iteración anterior (o el primero) se procesa aquí.
            
            // 1. Procesamiento (solo si ya se ha procesado el primer número)
            if (contador > 0 || numeroLeido != 0) { // Garantiza que no se procese el 0 final
                sumaTotal += numeroLeido;
                contador++;

                // 2. Determinar Mayor y Menor
                if (numeroLeido > mayor) {
                    mayor = numeroLeido;
                }
                if (numeroLeido < menor) {
                    menor = numeroLeido;
                }
            }
            
            // 3. Leer el SIGUIENTE número (que se evaluará en la condición 'while')
            System.out.print("Introduce un número: ");
            numeroLeido = sc.nextInt();

        } while (numeroLeido != 0); // La condición evalúa el número recién leído



        if (contador > 0) {
            // Ajuste final para compensar la lógica de conteo dentro del bucle
            // Aquí el contador debe ser igual al número de elementos sumados.
            
            double media = (double) sumaTotal / contador;
            
            System.out.println("Total de números leídos: " + contador);
            System.out.println("La media (promedio) es: " + String.format("%.2f", media));
            System.out.println("El número MAYOR es: " + mayor);
            System.out.println("El número MENOR es: " + menor);
        } else {
            System.out.println("No se introdujo ningún número válido.");
        }
    }
}