package ejsweb;

import java.util.Scanner;

public class ej5 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        System.out.println("ingresa el dinero entregado");
        int x = teclado.nextInt();
        System.out.println("ingresa el valor de la compra");
        int y = teclado.nextInt();

        int cambio = x - y;

        while (cambio >= 50) {
            System.out.println("50");
            cambio -= 50;

        }
        while (cambio >= 20) {
            System.out.println("20");
            cambio -= 20;
        }
        while (cambio >= 10) {
            System.out.println("10");
            cambio -= 10;
        }
            while (cambio >= 5) {
                System.out.println("5");
                cambio -= 5;
            }
            while (cambio >= 2) {
                System.out.println("2");
                cambio -= 2;
            }
            while (cambio >=     1) {
                System.out.println("1");
                cambio -= 1;
            }
        }
    }

