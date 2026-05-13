package Repaso;

import java.util.Scanner;

/**
 * <p>
 * Calcular el número de días transcurridos desde la fecha de nacimiento del
 * alumno hasta hoy
 * . Por las fechas que se manejan en este caso —alumnos de edades posibles—,
 * será suficiente considerar como bisiestos los años múltiplos de 4 (el año
 * 2000 fue bisiesto)
 * .
 * Las fechas se introducirán con tres números enteros (día, mes, año) cada una
 * . En el programa no será preciso validar que la fecha sea correcta
 * </p>
 * 
 * <p>
 * clase que calcula en numero de dias que han pasado hasta hoy desde el
 * nacimiento del alumno
 * - se consideran bisiestos los años multiplos de 4
 * - la fecha se ve como 3 enteros dia mes y año
 * </p>
 */
public class diasTranscurridos {
    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);

        int diasMes;
        int diasHastaAcabarAñoNacim = 0;
        int diasCadaAño = 0;
        int diasTrascurridosAñoActual = 0;

        System.out.println("ingresa el dia de nacimietno");
        int diaNacim = teclado.nextInt();

        System.out.println("ingresa el mes de nacimietno");
        int mesNacim = teclado.nextInt();

        System.out.println("ingresa el año de nacimietno");
        int añoNacim = teclado.nextInt();

        System.out.println("ingresa el dia de hoy");
        int diaHoy = teclado.nextInt();

        System.out.println("ingresa el mes de hoy");
        int mesHoy = teclado.nextInt();

        System.out.println("ingresa el año de hoy");
        int añoHoy = teclado.nextInt();

        switch (mesNacim) {
                case 4,6,9,11:
                    diasMes = 30;
                    break;
                    case 2:
                        if (añoNacim % 4 == 0) {
                            diasMes = 29;
                        } else {
                            diasMes = 28;
                        }
                        break;
                        default:
                            diasMes = 31;
                            break;
                        }
            diasHastaAcabarAñoNacim = diasMes - diaNacim;

        /**
         * calcular dias restantes del año de nacimientos
         * bucle for que empieza en el mes y acaba en diciembre y suna los dias que
         * tiene cada mes
         */

        for (int i = mesNacim + 1; i <= 12; i++) {

            
            switch (i) {
                case 4,6,9,11:
                    diasMes = 30;
                    break;
                    case 2:
                        if (añoNacim % 4 == 0) {
                            diasMes = 29;
                        } else {
                            diasMes = 28;
                        }
                        break;
                        default:
                            diasMes = 31;
                            break;
                        }
            diasHastaAcabarAñoNacim += diasMes;
        }
        

        /**
         * 
         * bucle para sumar dias de años enteros dese el año siguiente al nacimiento
         * hasta el previo al
         * de hoy para no contar dias de mas
         *
         */
        for (int i = añoNacim + 1; i < añoHoy; i++) {
            if (i % 4 == 0) {
                diasCadaAño += 366;
            } else {
                diasCadaAño += 365;
            }
        }

        /**
         * sumar dias trascurridos del año actual con diaHoy, mesHoy, añoHoy
         */
        for (int i = 1; i < mesHoy; i++) {
            switch (i) {
                case 4,6,9,11:
                    diasMes = 30;
                    break;
                case 2:
                    if (añoHoy % 4 == 0) {
                        diasMes = 29;
                    } else {
                        diasMes = 28;
                    }
                    break;
                default:
                    diasMes = 31;
                    break;

                }
                diasTrascurridosAñoActual += diasMes;
            }
        //sumar dias que ya han pasado
        diasTrascurridosAñoActual += diaHoy;

        int sumaTotalDias = diasHastaAcabarAñoNacim + diasCadaAño + diasTrascurridosAñoActual;

        System.out.println(sumaTotalDias);
    }
}
