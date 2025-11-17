package RepasoEV_1;

import static java.lang.Math.sqrt;
import java.util.Scanner;

public class repaso_8 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        double t;
        double h;
        double g = 9.81;
        System.out.println("CALCULO DE TIEMPO EN CAER ");
        System.out.println("INTRODUCE LA ALTURA");
        h = teclado.nextDouble();
        t = sqrt(2 * h / g);
        System.out.printf("%.2f  ", t ,"  segundos");
        
    }
}
