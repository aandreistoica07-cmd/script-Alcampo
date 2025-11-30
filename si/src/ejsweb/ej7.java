package ejsweb;
import java.util.Scanner;
public class ej7 {
public static void main (String [] args){
    Scanner teclado = new Scanner (System.in);
    System.out.println("ingresa un mes 1-12");
    int mes = teclado.nextInt();
        System.out.println("ingresa un año");
        int año = teclado.nextInt();
        int dias = 0;
    switch (mes) {
        case 1:
        case 3:
        case 5:
        case 7:
        case 8:
        case 10:
        case 12:
            dias = 31;
        break;

        case 4:
        case 6:
        case 9:
        case 11:
            dias = 30;
        break;
        case 2:
        if ( año%4 == 0){
            dias = 29;
        } else {
            dias = 28;
        }

    }
    System.out.print("el mes " + mes + " tiene  " + dias + " dias");
        

        

}
}



