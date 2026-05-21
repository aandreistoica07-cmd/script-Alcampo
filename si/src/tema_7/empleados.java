package tema_7;

import java.util.Scanner;

public class empleados {
    private String nombre;
    private double sueldo;

    public empleados(String nombre, double sueldo) {
        this.nombre = nombre;
        this.sueldo = sueldo;
    }

    public String getNombre() {
        return nombre;
    }

    public double getSueldo() {
        return sueldo;
    }

    protected void pedirDatos(Scanner teclado) {
        System.out.print("Nombre: ");
        this.nombre = teclado.nextLine();
        System.out.print("Sueldo: ");
        this.sueldo = teclado.nextDouble();
        teclado.nextLine(); // Limpieza de buffer
    }
     protected  void mostrarDatos() {
        System.out.print("Nombre: " + nombre + " | Sueldo: " + sueldo);
    }
}
class jefe extends empleados{
   
    private String titulo;
    private String dept;

     
    public jefe(String nombre,double sueldo, String titulo,String dept ){
        super(nombre, sueldo);
        this.titulo = titulo;
        this.dept = dept;
    }

    public String getTitulo() {
        return titulo;
    }

    public String getDept(){
        return dept;
    }

    @Override
    public void pedirDatos(Scanner teclado) {
        super.pedirDatos(teclado); // Reutiliza la petición de nombre y sueldo
        System.out.print("Título: ");
        this.titulo = teclado.nextLine();
        System.out.print("Departamento: ");
        this.dept = teclado.nextLine();
    }

    @Override
    public void mostrarDatos() {
        super.mostrarDatos(); // Muestra nombre y sueldo
        System.out.println(" | Título: " + titulo + " | Dept: " + dept);
    }

}
