package RepasoEV_1;

import java.util.Scanner;

public class repaso_11 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        double total = 0;

        System.out.print("Número de personas: ");
        int personas = teclado.nextInt();
        teclado.nextLine();

        System.out.println("Día de la semana");
        String dia = teclado.nextLine();

        System.out.print("¿Tiene tarjeta CinePas? (s/n): ");
        String cinepas = teclado.nextLine();

        if (dia.equalsIgnoreCase("miercoles")) {
            total = personas * 5;
        } else if (dia.equalsIgnoreCase("jueves")) {
            int parejas = personas / 2;
            int sueltos = personas % 2;
            total = parejas * 11 + sueltos * 8;
        } else {
            total = personas * 8;

        }

        if (cinepas.equalsIgnoreCase("s")) {
            total = total * 0.9;
        }

        System.out.println("Total a pagar: " + total + " euros");

    }
}
