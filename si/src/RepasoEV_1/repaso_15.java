package RepasoEV_1;
import java.util.Scanner;
public class repaso_15 {
public static void main(String[] args) {
    Scanner teclado = new Scanner (System.in);
    String numero;
    System.out.println("Introduce un numero");
    numero = teclado.nextLine();

    System.out.println("Ahora introduce un digito");
    String digito = teclado.nextLine();

    for ( int i = 0; i < numero.length();i++){
        if ( numero.charAt(i) == digito.charAt(0)){
            System.out.println("el digito " + digito +  " esta en la/s posicion/es "+ (i+1));
        }
    }
}
}
