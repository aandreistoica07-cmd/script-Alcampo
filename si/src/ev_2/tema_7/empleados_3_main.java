package tema_7;
import java.util.Scanner;
public class empleados_3_main {
    public static void main(String[] args) {
        Scanner teclado = new Scanner (System.in);

        empleados_3[] listaEmpleados = new empleados_3[100];
        int opcion;
        
        listaEmpleados[0] = new empleados_3("Juan", 25, 10);
        listaEmpleados[1] = new empleados_3("Ana", 30, 5);
        listaEmpleados[2] = new jefe_3("Pedro", 40, 15, "Ventas");
        listaEmpleados[3] = new jefe_3("Maria", 45, 20, "I+D");

        do{
            System.out.println("\n--- DADO EL SIGUIENTE MENÚ ---");
        System.out.println("1. Modificar el sueldo base de todos los empleados.");
        System.out.println("2. Modificar el plus de todos los jefes.");
        System.out.println("3. Visualizar los datos de todos los empleados.");
        System.out.println("4. Salir.");
        System.out.print("ELIJA UNA OPCIÓN: ");
        
        opcion = teclado.nextInt();


        switch (opcion) {
            case 1:
                System.out.print("Introduzca nuevo sueldo base: ");
                // Como SUELDO_BASE es static en empleados_3, cambiamos todos a la vez
                empleados_3.SUELDO_BASE = teclado.nextDouble();
                break;
                
            case 2:
                System.out.print("Introduzca nuevo plus para los jefes: ");
                // OJO: Para que esto funcione, en tu clase jefe_3 debes 
                // quitar 'final' a plusJefe y ponerle 'static'
                jefe_3.plusJefe = teclado.nextDouble();
                break;
                
            case 3:
                System.out.println("\nLISTADO ACTUAL:");
                for (int i = 0; i < listaEmpleados.length; i++) {
                    listaEmpleados[i].verDatos();
                    System.out.println("-------------------");
                }
                break;
                
            case 4:
                System.out.println("Saliendo del programa...");
                break;
                
            default:
                System.out.println("Opción no válida.");
        }
        }while(opcion != 4);

       

    }
}
