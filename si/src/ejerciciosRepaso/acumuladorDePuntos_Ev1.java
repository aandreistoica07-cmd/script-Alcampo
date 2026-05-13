package ejerciciosRepaso;
import java.util.Scanner;
/**
 * <p>clase que solicita al usuario que introduzca numeros positivos por consola
 *      -   los va sumando y lleva la cuenta de cuantos se han introducido
 *      -   si introduce un numero negativo el programa debe mostar un mensaje de error y que se ignore (no sumar ni contar)
 *      -   parar el programa si el usuario mete un 0
 *      -   cuando termina muestra por pantalla la suma total y la cantidad total de numeros ingresados
 * </p>
 * 
 *  
 */

public class acumuladorDePuntos_Ev1 {
    public static void main (String [] args){
        Scanner teclado = new Scanner(System.in);
        int contador = 0; 
        int acumulador = 0;
        int numUsuario;
        

        do {
            System.out.println("ingresa un numero entero positivo");
                numUsuario = teclado.nextInt();
            if (numUsuario < 0 ){
                System.out.println("no debes ingresar numeros negativos no se sumara ni contara");
            }
        } while (numUsuario != 0);

    }   
}
