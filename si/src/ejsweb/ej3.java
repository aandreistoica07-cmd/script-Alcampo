package ejsweb;

import java.util.Scanner;

public class ej3 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        System.out.println("ingresa un numero");
        int numero = teclado.nextInt();
        int divisores = 0;
        if ( numero<2){
            System.out.println("no primo");
        }else{
        for (int i = 1; i <= numero; i++) {
            if (numero % i == 0) {
                divisores++;
            }
        }
        if ( divisores==2){
            System.out.println(numero +" primo");
        } else {
            System.out.println(numero + " no primo");
        }
    }
    }
}
