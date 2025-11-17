package Progtema4;





import java.util.Scanner;

public class Progtema4_12 {

    public static void main(String[] args) {

        Scanner teclado = new Scanner(System.in);
        String palabra;

        System.out.println("introduce una palabra");
        palabra = teclado.nextLine();

        String rotacion = palabra;
        for (int i = 0; i <= palabra.length(); i++) {
            rotacion = rotacion.charAt(rotacion.length() - 1) + rotacion.substring(0, rotacion.length() - 1);
            System.out.println(rotacion);
        }
    }
}
