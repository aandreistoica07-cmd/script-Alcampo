package RepasoEV_1;

import java.util.Scanner;

public class repaso_21 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        System.out.println("ingresa un numero en formato decimal");
        int numero = teclado.nextInt();
        int copia = numero;
        String binario = "";
        do {
            int residuo = copia % 2;
            copia /= 2;
            binario = residuo + binario;
        } while (copia > 0);
        System.out.print(binario);
    }
}
