package RepasoEV_1;

import java.util.Scanner;

public class repaso_16 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        // Pedimos los datos
        System.out.print("Introduce el primer número: ");
        long n1 = teclado.nextLong();
        System.out.print("Introduce el segundo número: ");
        long n2 = teclado.nextLong();

        // --- PASO 1: Invertir n1 ---
        long invertido1 = 0;
        while (n1 > 0) {
            invertido1 = (invertido1 * 10) + (n1 % 10);
            n1 = n1 / 10;
        }

        // --- PASO 2: Invertir n2 ---
        long invertido2 = 0;
        while (n2 > 0) {
            invertido2 = (invertido2 * 10) + (n2 % 10);
            n2 = n2 / 10;
        }

        System.out.println("El resultado de la mezcla es: ");

        // --- PASO 3: Mezclar ---
        while (invertido1 > 0 && invertido2 > 0) {
            // Sacamos dígito de n1
            System.out.print(invertido1 % 10);
            invertido1 = invertido1 / 10;

            // Sacamos dígito de n2
            System.out.print(invertido2 % 10);
            invertido2 = invertido2 / 10;
        }
        
        System.out.println(); // Salto de línea final para que quede bonito
    }
}