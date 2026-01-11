package RepasoEV_1;
import java.util.Scanner;
public class repaso_5 {
public static void main(String[] args) {
    Scanner teclado  =new Scanner(System.in);
    double nota1;
    double nota2;
    double media;
    double x;
    System.out.println("--CALCULO DE NOTA NECESARIA");
        System.out.println("--INTRODUCE LO QUE HAS SACADO EN EL PRIMER EXAMEN");
        nota1= teclado.nextDouble();
    System.out.println("--INTRRODUCE LA MEDIA DESESADA");
    media = teclado.nextDouble();

    x= media-(nota1*0.3);
    nota2 = x/0.7;
System.out.println("--LA NOTA NECESARIA EN EL SEGUNDO EXAMEN ES : "+ nota2);
}
}

