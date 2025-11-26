package RepasoEV_1;
import java.util.Scanner;
public class repaso_17 {
public static void main(String[] args) {
    Scanner teclado = new Scanner (System.in);

    System.out.println("introduce un numero");
    int numero = teclado.nextInt();
    System.out.println("introduce un digito");
    int digito = teclado.nextInt();
    System.out.println("introduce una poscion");
    int posicion = teclado.nextInt();

    int copia  = numero;
    int longitud = 0;

    if ( copia == 0){
        longitud = 1 ;

    } else {
        while ( copia > 0){
            copia = copia/10 ;
            longitud++;
        }
    }
    int cifrasDerecha = longitud - (posicion - 1);
        
        int divisor = 1;
        // Multiplicamos por 10 tantas veces como cifras necesitemos a la derecha
        for (int i = 0; i < cifrasDerecha; i++) {
            divisor = divisor * 10;
        }

        // 4. Cortar y Pegar
        int parteIzquierda = numero / divisor;
        int parteDerecha   = numero % divisor;

        // Fórmula: (Izquierda + Digito) + Derecha
        int resultado = (parteIzquierda * 10 + digito) * divisor + parteDerecha;

        System.out.println("Resultado: " + resultado);
}
}
