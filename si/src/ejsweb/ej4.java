package ejsweb;
import java.util.Scanner;
public class ej4 {
public static void main(String[] args) {
    Scanner teclado = new Scanner (System.in);
    System.out.println("Ingresa el numero inicial x");
    int x = teclado.nextInt();
    System.out.println("ingresa hasta donde va a bajar ");
    int y = teclado.nextInt();

    while(x>y){
        System.out.println(x-=2);
    }
}
}
