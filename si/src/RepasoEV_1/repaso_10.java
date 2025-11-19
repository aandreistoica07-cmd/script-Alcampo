package RepasoEV_1;

import java.util.Scanner;

public class repaso_10 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        int horas;
        int minutos;
        int segundos_hora;
        int segundos_minutos;
        int segundos_total;
        int segundos_dia = 86400;
        int S_restantes;


        System.out.println("Ingresa una hora");
        horas = teclado.nextInt();
        if (horas < 0 && horas >= 24) {
            System.out.println("ERROR entre 0 y 24 horas");
        } else {
            System.out.println("Ingresa los minutos");
            minutos = teclado.nextInt();
            if (minutos < 0 && minutos >= 60) {
                System.out.println("ERROR");
            }

            //pasar a segundos las horas y minutos //
            segundos_hora = horas * 3600;
            segundos_minutos = minutos * 60;
            
            // suma de horas y minutos en segundos//
            segundos_total = segundos_hora + segundos_minutos;

            S_restantes = segundos_dia - segundos_total;

            System.out.println(S_restantes+" segundos");


        }

    }
}
