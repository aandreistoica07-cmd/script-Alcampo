import java.util.Scanner;

public class empleado {
    private String nombre;
    private int numeroEmpleado;

    public String getnombre() {
        return nombre;
    }

    public int getnumeroEmpleado() {
        return numeroEmpleado;
    }

    public void setnombre(String nombre) {
        this.nombre = nombre;
    }

    public void setnumeroEmpleado(int numeroEmpleado) {
        this.numeroEmpleado = numeroEmpleado;
    }

    public void leerDatos() {
        Scanner teclado = new Scanner(System.in);
        System.out.println("introduce el nombre del empleado");
        this.nombre = teclado.nextLine();
        teclado.nextLine();

        System.out.println("introduce el numero del empleado");
        this.numeroEmpleado = teclado.nextInt();
    }

    public void verDatos() {

        System.out.print(nombre +","+ numeroEmpleado);
       
    }

    public empleado(int numeroEmpleado, String nombre) {
        this.nombre = nombre;
        this.numeroEmpleado = numeroEmpleado;
    }

    public static void main(String[] args) {

        empleado emp = new empleado(0, null);
        emp.leerDatos();
        emp.verDatos();
hola
        emp.getnombre();
    }

}
avadvdavdavdv