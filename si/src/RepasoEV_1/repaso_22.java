package RepasoEV_1;

import java.util.Scanner;

public class repaso_22 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        System.out.println("Ingresa un numero en formato decimal:");
        double numero = teclado.nextDouble();
        
        // Separar parte entera y decimal
        int parteEntera = (int) numero;
        double parteDecimal = numero - parteEntera;
        
        // Convertir parte entera a octal
        int copia = parteEntera;
        String octalEntero = "";
        do {
            int residuo = copia % 8;
            copia /= 8;
            octalEntero = residuo + octalEntero;
        } while (copia > 0);
        
        // Convertir parte decimal a octal
        String octalDecimal = "";
        int contador = 0;
        while (contador < 10 && parteDecimal != 0) {
            parteDecimal *= 8;
            int digito = (int) parteDecimal;
            octalDecimal += digito;
            parteDecimal -= digito;
            contador++;
        }
        
        // Mostrar resultado
        if (!octalDecimal.isEmpty()) {
            System.out.println("Octal: " + octalEntero + "." + octalDecimal);
        } else {
            System.out.println("Octal: " + octalEntero);
        }
    }
}       