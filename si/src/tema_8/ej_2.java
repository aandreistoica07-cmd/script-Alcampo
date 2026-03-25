package tema_8;

import java.util.Scanner;

public class ej_2 {
    static Scanner teclado = new Scanner(System.in);

    public static String pedirCadena() {
        System.out.println("introduce una letra para salir");
        return teclado.nextLine();
    }

    public static int pedirNumero()  {
        System.out.println("introduce un numero");
        String texto = pedirCadena();

        return Integer.parseInt(texto);
    }

public static void main(String[] args) {
    int suma = 0;
    int contador = 0;
    boolean seguir = true;
    
    while(contador < 6 && seguir){
        
        try{
            int numero = pedirNumero();

            suma+=numero;
            contador++;
        }catch(NumberFormatException e){
            System.out.println("se ha introducido un dato incorrecto");
            System.out.println(e.getMessage());
            seguir = false;
        }
    }

    System.out.println(suma);
}

}
