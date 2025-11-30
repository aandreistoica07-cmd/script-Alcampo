package ejsweb;

import java.util.Scanner;

public class ejdados {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        int D1 = 0;
        int D2 = 0;
        int contador12 = 0;
        
        int contadorintentos = 0;

        boolean terminar = false;
        while (!terminar) {
            D1 = (int) (Math.random() * 6) + 1;
            D2 = (int) (Math.random() * 6) + 1;
             int suma = D1+D2;
            contadorintentos++;
          
           System.out.print("Lanzamiento #" + contadorintentos + ": [" + D1 + ", " + D2 + "] -> Suma: " + suma);
                if (suma >= 7   ) {
                    System.out.println(" terminado");
                    terminar = true;

                } else if ( suma >=12){
                    contador12++;
                      System.out.println("terminado");
                        System.out.println(" -- ¡SUMA 12! Ocurrencia #" + contador12);

                    if (contador12 == 2){
                        terminar = true;
                    } else{
                        System.out.println();
                    }
                }
            }
            System.out.println("\n--- SIMULACIÓN FINALIZADA ---");
        System.out.println("Total de lanzamientos necesarios: " + contadorintentos);
        System.out.println("Número de veces que salió 12: " + contador12);

        }
    }

