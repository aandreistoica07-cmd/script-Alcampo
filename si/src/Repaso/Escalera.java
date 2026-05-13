package Repaso;
import java.util.Scanner;
/**
 * <p> Clase que genera una escalera de '*' mediante bucles anidados 
 *     - se le pasa por scanner el tamaño de la escalera</p>
 */
public class Escalera {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        System.out.println("ingresa el tamaño");
        int tamaño = teclado.nextInt();
        /**
         * filas
         */
        for(int i = 1 ; i <= tamaño; i++){
            /**
             * espacios
             */
            for(int j = (tamaño-i); j > 0; j--){
                System.out.print(" ");
            }
            /**
             * simbolos
             */
            for(int k = 0; k < i; k++){
                System.out.print('*');
            }
            System.out.println();
        }

        //escalera invertida//

        for(int i = 0; i <= tamaño ; i++){
            for(int j = i ; j < i ; j++){
                System.out.print(" ");
            }
            for(int k = 1 ; k < ( tamaño-i+1);k++){
                System.out.print('*');
            }
            System.out.println();
        }
    }
}
