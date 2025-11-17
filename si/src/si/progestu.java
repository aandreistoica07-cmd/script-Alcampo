/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package si;

import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 */
public class progestu {
    public static void main (String[] args){
        // Variables de entrada
         Scanner teclado= new Scanner(System.in);
        int idAlumno, horasAsistidas, totalHorasLectivas;
        // Ingresar los datos
        System.out.print("Ingrese un id alumno:");
        idAlumno=teclado.nextInt();
        
        System.out.print("Ingrese un numero de horas lectivas:");
        totalHorasLectivas=teclado.nextInt();
        
        System.out.print("Ingrese un numero de horas asistidas:");
        horasAsistidas=teclado.nextInt();
        
        
        // Cálculo horas ausencia 
        int horasAusentes = totalHorasLectivas - horasAsistidas;
        
        // El porcentaje se calcula como (horasAusentes / totalHoras) * 100
        // El (double) es necesario porque la division da siempre un numero entre 0-1 y necesitamos decimales.
        double porcentajeAusencias = ((double) horasAusentes / totalHorasLectivas) * 100.0;

        // Notificación 
        System.out.println("--- Informe de Asistencia ---");
        System.out.println("ID Alumno: " + idAlumno);
        System.out.println("Total de horas lectivas: " + totalHorasLectivas);
        System.out.println("Horas asistidas: " + horasAsistidas);
        System.out.println("Horas ausentes: " + horasAusentes);
        System.out.println("Porcentaje de ausencias: " + porcentajeAusencias);
        System.out.println("----------------------------");

        //Notificacion 15%
        if (porcentajeAusencias > 15.0) {
            System.out.println("NOTIFICACIÓN DE PÉRDIDA DE DERECHO A EVALUACIÓN CONTINUA");
            System.out.println("El alumno " + idAlumno + " ha superado el 15% de ausencias.");
            System.out.println("Ausencias: " + horasAusentes + " horas (" + porcentajeAusencias + ").");
        }
        //Notificacion 10%
         else if (porcentajeAusencias > 10.0) {
            System.out.println("AVISO: El alumno " + idAlumno + " ha superado el 10% de ausencias.");
            System.out.println("Ausencias: " + horasAusentes + " horas (" + porcentajeAusencias + ").");
        }
        //Notificacion 5%
        
        else if (porcentajeAusencias > 5.0) {
            System.out.println("AVISO: El alumno " + idAlumno + " ha superado el 5% de ausencias.");
            System.out.println("Ausencias: " + horasAusentes + " horas (" + porcentajeAusencias + ").");
        } 
        else {
            // Umbral: Ausencias <= 5%
            System.out.println("El alumno " + idAlumno + " cumple con el requisito de asistencia para la evaluación continua.");
        }
    }
}
    
