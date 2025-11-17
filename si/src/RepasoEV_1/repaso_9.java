package RepasoEV_1;

import java.util.Scanner;

public class repaso_9 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in); 
        int mes;
        int dia;
        String signo = "";
        boolean esValido = true;

        System.out.println("TU SIGNO DEL HOROSCOPO ");

        System.out.println("INTRODUCE EL MES DE NACIMIENTO (1-12): ");
        mes = teclado.nextInt();
        
        System.out.println("INTRODUCE EL DIA DE NACIMIENTO (1-31): "); 
        dia = teclado.nextInt();

        // Validar rango de mes y día
        if (mes < 1 || mes > 12) {
            esValido = false;
        }
        
        if (dia < 1 || dia > 31) {
            esValido = false;
        }

        // Si es válido, determinar el signo
        if (esValido) {
            if ((mes == 3 && dia >= 21) || (mes == 4 && dia <= 19)) {
                signo = "Aries";
            } else if ((mes == 4 && dia >= 20) || (mes == 5 && dia <= 20)) {
                signo = "Tauro";
            } else if ((mes == 5 && dia >= 21) || (mes == 6 && dia <= 20)) {
                signo = "Géminis";
            } else if ((mes == 6 && dia >= 21) || (mes == 7 && dia <= 22)) {
                signo = "Cáncer";
            } else if ((mes == 7 && dia >= 23) || (mes == 8 && dia <= 22)) {
                signo = "Leo";
            } else if ((mes == 8 && dia >= 23) || (mes == 9 && dia <= 22)) {
                signo = "Virgo";
            } else if ((mes == 9 && dia >= 23) || (mes == 10 && dia <= 22)) {
                signo = "Libra";
            } else if ((mes == 10 && dia >= 23) || (mes == 11 && dia <= 21)) {
                signo = "Escorpio";
            } else if ((mes == 11 && dia >= 22) || (mes == 12 && dia <= 21)) {
                signo = "Sagitario";
            } else if ((mes == 12 && dia >= 22) || (mes == 1 && dia <= 19)) {
                signo = "Capricornio";
            } else if ((mes == 1 && dia >= 20) || (mes == 2 && dia <= 18)) {
                signo = "Acuario";
            } else if ((mes == 2 && dia >= 19) || (mes == 3 && dia <= 20)) {
                signo = "Piscis";
            } else {
                signo = "Fecha inválida";
            }
            
            System.out.println("\n====== RESULTADO ======");
            System.out.println("Fecha: " + dia + "/" + mes);
            System.out.println("Signo zodiacal: " + signo);
        } else {
            System.out.println("\n❌ ERROR: Mes debe estar entre 1-12 y Día entre 1-31");
        }
        
        teclado.close();
    }
}
