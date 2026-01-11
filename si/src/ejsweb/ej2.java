package ejsweb;
import java.util.Scanner;
public class ej2 {
public static void main(String[] args) {
   Scanner teclado = new Scanner (System.in); 
    System.out.print("numero");
    int numero = teclado.nextInt();

    for ( int i = 1 ; i <= 10 ; i++){
        int tabla = numero*i;
        System.out.println(numero + " * " +  i + " = " + tabla);
    }
}

}
