package RepasoEV_1;

import java.util.Scanner;

public class repaso_18 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        System.out.println(" introduce un numero");
        int numero = teclado.nextInt();
        String aparecen = " ";
        String no_aparecen = " ";
        for (int i = 0; i <= 9; i++) {

            int copia = numero;
            boolean presente = false;
            while (copia > 0 && !presente) {
                int digito = copia % 10;

                if (digito == i) {
                    presente = true;
                }
                copia = copia / 10;
            }
            if (presente) {
                aparecen += i + " ";
            } else {
                no_aparecen += i + " ";
            }

        }
        System.out.println("aparecen : " + aparecen + "  y  no aparecen: " + no_aparecen);

    }
}