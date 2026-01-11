package RepasoEV_1;
import java.util.Scanner;
public class repaso_2 {
public static void main(String[] args) {
   Scanner teclado  = new Scanner (System.in);
    double numero1;
    double numero2;

    System.out.println("ingresa el primer numero");
    numero1  =teclado.nextDouble();

    System.out.println("ingresa el segundo numero");
    numero2 = teclado.nextDouble();

    double suma = numero1 + numero2;
    double multiplicacion = numero1*numero2;
    double division = numero1/numero2;
    double resta = numero1-numero2;
    System.out.println( "la suma de" + numero1+"+" +numero2+"es"+suma );
         System.out.println( "la multiplicacion de : " + numero1+"+" +numero2+ " es"+multiplicacion );
            System.out.println( "la division de : " + numero1+ "+" +numero2+" es"+division );
                System.out.println( "la resta de: " + numero1+ "+" +numero2+" es"+resta );
}
}
