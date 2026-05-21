package Repaso;
import java.util.Scanner;
/**
 * <p> Clase que imprime por terminal un diamante de '*'
 *     - se ingresa un numero entero, si este es par se usa el impar mas cercano
 *     - se generara la fila central a partir de este numero que sera el numero de asteriscos
 *     - usa bucles anidados
 * 
 * 
 */
public class Diamante {
    public static void main(String[] args) {
        Scanner teclado = new Scanner (System.in);
        
        System.out.println("ingresa el tamaño del diamante");
        int filaCentral = teclado.nextInt();

        if(filaCentral % 2 == 0){
            filaCentral++;
        }else if(filaCentral<= 0){
            throw new IllegalArgumentException("no puedes ingresar un tamaño negativo");
        }

        //bucles anidados superior//
        /**
         * bucle de filas
         */
        for(int i = 1; i <= (filaCentral/2) + 1 ;i++){
            /**
             * bucle de espacios
             */
            for(int j = 0; j <=(filaCentral/2)- i;j++){
                System.out.print(" ");
            }
            /**
             * bucle de '*'
             */
            for(int k = 1; k <=(2* i)- 1 ;k++){
                System.out.print('*');
            }
            System.out.println();
        }

        //bucles anidados parte inferior//
        /**
         * bucle filas
         */
        for(int i = (filaCentral/2) ; i >= 1;i--){
            /**
             * bucle espacios
             */
            for(int j = 0; j <=(filaCentral/2)- i;j++){
                System.out.print(" ");
            }
            /**
             * bucle '*'
             */
            for(int k = 1; k <=(2* i)- 1 ;k++){
                System.out.print('*');
            }
            System.out.println();
        }
    }
}
