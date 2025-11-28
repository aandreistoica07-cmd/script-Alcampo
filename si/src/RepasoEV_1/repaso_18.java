package RepasoEV_1;

import java.util.Scanner;

public class repaso_18 {
    public static void main(String[] args){
        Scanner sc = new Scanner(System.in);

       System.out.print("Introduce un número entero: ");
        long numero = sc.nextLong();


        // Manejo del signo (sin Math.abs)
        long numPositivo = numero;
        if (numPositivo < 0) {
            numPositivo = -numPositivo;
        }

        // 0 = ausente, 1 = presente.
        int d0 = 0, d1 = 0, d2 = 0, d3 = 0, d4 = 0;
        int d5 = 0, d6 = 0, d7 = 0, d8 = 0, d9 = 0;

        // 2. Marcar dígitos presentes
        if (numPositivo == 0) {
            d0 = 1; // Si el número es 0, solo aparece el dígito 0
        } else {
            long temp = numPositivo;
            while (temp > 0) {
                int digito = (int) (temp % 10);
                
                // Usamos un switch para asignar el valor '1' a la variable correspondiente
                switch (digito) {
                    case 0: d0 = 1; break;
                    case 1: d1 = 1; break;
                    case 2: d2 = 1; break;
                    case 3: d3 = 1; break;
                    case 4: d4 = 1; break;
                    case 5: d5 = 1; break;
                    case 6: d6 = 1; break;
                    case 7: d7 = 1; break;
                    case 8: d8 = 1; break;
                    case 9: d9 = 1; break;
                }
                temp /= 10;
            }
        }

        // 3. Generar y mostrar resultados
        String p = ""; // Presentes
        String a = ""; // Ausentes

        // Recorremos las variables de rastreo para construir las cadenas de resultado
        if (d0 == 1) p += "0 " ; else a += "0 ";
        if (d1 == 1) p += "1 " ; else a += "1 ";
        if (d2 == 1) p += "2 "; else a += "2 ";
        if (d3 == 1) p += "3 "; else a += "3 ";
        if (d4 == 1) p += "4 "; else a += "4 ";
        if (d5 == 1) p += "5 "; else a += "5 ";
        if (d6 == 1) p += "6 "; else a += "6 ";
        if (d7 == 1) p += "7 "; else a += "7 ";
        if (d8 == 1) p += "8 "; else a += "8 ";
        if (d9 == 1) p += "9 "; else a += "9 ";

        System.out.println("Número: " + numero);
        System.out.println("Aparecen:" + p );
        System.out.println("NO aparecen:" + a);
    }
}