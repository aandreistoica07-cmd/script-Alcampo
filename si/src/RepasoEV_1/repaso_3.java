package RepasoEV_1;
import java.util.Scanner;

public class repaso_3 {
public static void main(String[] args) { 
Scanner teclado = new Scanner (System.in);
double altura;
double base;

System.out.println("-- CALCULO DE AREA -- ");
System.out.println("-- INTRODUCE LA ALTURA -- ");
altura = teclado.nextDouble();
System.out.println("-- INTRODUCE LA BASE -- ");
    base = teclado.nextDouble();


    double area = base*altura;

    System.out.println("  EL AREA ES :" +   area);
    teclado.close();
}
}
