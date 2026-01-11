package RepasoEV_1;

import java.util.Scanner;

public class repaso_7 {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        float horas;
        int salario_hora = 12;
        int salario_hora_extra = 16;
        float horas_extra;
        float hora_normal;
        float salario_semanal;
        System.out.println("--CALCULO DE SALARIO SEMANAL");
        System.out.println("--INTRODUCE LAS HORAS TRABAJADAS EN LA SEMANA");
        horas = teclado.nextFloat();
        if (horas <= 40) {
            salario_semanal = horas * salario_hora;

        } else {
            hora_normal = 40;
            horas_extra = horas - 40;
            salario_semanal = (hora_normal * salario_hora) + (horas_extra * salario_hora_extra);
            System.out.println("-EL SALARIO CON HORAS EXTRA ES : " + salario_semanal);
        }
        System.out.println("-EL SALARIO  ES : " + salario_semanal);
        teclado.close();
    }
}
