package RepasoEV_1;

import java.util.Scanner;

public class repaso_1 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        double euros;
        double pesetas = 166.386;

        System.out.print("Introduce la cantidad en euros: ");
        euros = teclado.nextDouble();

        double resultado = euros * pesetas;

        System.out.println(euros + " euros son " + resultado + " pesetas.");

        teclado.close();
    }
}
