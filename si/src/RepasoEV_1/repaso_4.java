package RepasoEV_1;
import java.util.Scanner;
public class repaso_4 {
public static void main(String[] args) {
 Scanner teclado = new Scanner (System.in);  
    float horas;
    int salario_hora= 12;
    System.out.println("--CALCULO DE SALARIO SEMANAL");
        System.out.println("--INTRODUCE LAS HORAS TRABAJADAS EN LA SEMANA");
                horas = teclado.nextFloat();
 
       double salario_semanal = (salario_hora*horas);        
       System.out.println("--EL SALARIO ES :" + salario_semanal+"--");
       teclado.close();
}
}

