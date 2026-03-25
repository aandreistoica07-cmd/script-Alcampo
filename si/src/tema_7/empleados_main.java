package tema_7;
import java.util.Scanner;

public class empleados_main {

    public static void main(String[] args) {
        Scanner teclado = new Scanner(System.in);
        
        System.out.println("¿Cuántos empleados normales quieres crear?");
        int numEmps = teclado.nextInt();
        
        System.out.println("¿Cuántos jefes quieres crear?");
        int numJefes = teclado.nextInt();
        teclado.nextLine(); 

      
        empleados[] emps = new empleados[numEmps];
        jefe[] jefes = new jefe[numJefes];

        if (numEmps >= 0 && numJefes >= 0) {
            
           

        // --- VISUALIZACIÓN DE RESULTADOS ---
        System.out.println("\n===============================");
        System.out.println("      LISTADO DE PERSONAL");
        System.out.println("===============================");

        System.out.println("\n>> EMPLEADOS:");
        for (int i = 0; i < emps.length; i++) {
            System.out.println("- " + emps[i].getNombre() + " | Sueldo: " + emps[i].getSueldo() + "€");
        }
    
        System.out.println("\n>> JEFES:");
        for (int i = 0; i < jefes.length; i++) {
            System.out.println("- " + jefes[i].getNombre() + 
                               " | Dept: " + jefes[i].getDept() + 
                               " | Título: " + jefes[i].getTitulo() + 
                               " | Sueldo: " + jefes[i].getSueldo() + "€");
        }
        
        teclado.close();
    }
    }
}