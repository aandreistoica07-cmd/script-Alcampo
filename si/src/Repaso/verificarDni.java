package Repaso;

import java.util.Scanner;

/**
 * <p>
 * Programa que solicite introducir un NIF hasta que sea correcto.
 * Para verificar el NIF de españoles residentes mayores de edad, el algoritmo
 * de cálculo de la letra de control es el siguiente:
 * Se divide el número del DNI —que será mayor que 0 y menor que 100.000.000—
 * entre 23 y el resto permite localizar la letra de control
 * </p>
 * 
 * <p>
 * Clase que pide un texto , el DNI(lo mismo que nif) del usuario
 * - se le extrae el numero y se divide entre(%) 23 y se calcula el numero en
 * funcion del resto que da la operacion
 * - la letra se escoje a traves de una tabla
 * 
 * 
 */
public class verificarDni {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        /**
         * variable de control para el bucle do-while
         */
        boolean valido = true;
        /**
         * DNI del usuario con formato de 8 numeros y 1 letra
         */
        String dni;

        char letraDni;
        int numeroDni;
        String tabla = "TRWAGMYFPDXBNJZSQVHLCKE";

        do {
            System.out.println("ingresa un DNI a verificar");
            dni = teclado.nextLine();
            if (dni.length() != 9) {
                valido = false;
                System.out.println("dni no valido , tamaño incorrecto , reviselo");
            }else{
                try{
                    numeroDni = Integer.parseInt(dni.substring(0,8)); 
                    letraDni = dni.toUpperCase().charAt(8);
        
                    int resto = numeroDni % 23;
                    char letraCalculada = tabla.charAt(resto);
        
                    if ( letraDni == letraCalculada){
                        System.out.println("DNI CORRECTO");
                        valido = true;
                    }else{
                        System.out.println("LETRA INCORRECTA");
                        valido = false;
                    }

                }catch(NumberFormatException e){
                      // Validación extra: por si los primeros 8 caracteres no son números
                      System.out.println("Error: Los primeros 8 caracteres deben ser dígitos.");
                     valido = false;
                }

            }
        } while (!valido);
    }
}
