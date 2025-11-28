package RepasoEV_1;

/* */
/* 1º dividir el numero entre 10 hasta que sea menor a 0 y hacer contador
* 2ª hacer operacion para meter cifras a la derecha y
* 3º calcular divisor para desplazar cifras y meter el digito 

*/
import java.util.Scanner;

public class repaso_17 {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        System.out.println("introduce un numero");
        int numero = teclado.nextInt();
        System.out.println("introduce un digito");
        int digito = teclado.nextInt();
        System.out.println("introduce una poscion");
        int posicion = teclado.nextInt();

        int copia = numero;
        int longitud = 0;

        if (copia == 0) {
            longitud = 1;

        } else {
            while (copia > 0) {
                copia = copia / 10;
                longitud++;

            }

            int cifrasderecha = longitud - (posicion - 1);
            int divisor = 1;
            for (int i = 0; i < cifrasderecha; i++) {
                divisor = divisor * 10;

            }
            int parteIzq = numero/divisor;
            int parteDcha = numero %divisor;
            int resultado  =(parteIzq * 10 + digito) * divisor +parteDcha;
            System.out.println(resultado);
        }
    }
}