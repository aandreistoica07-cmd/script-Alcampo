package tema_7;
public class empleados_3 {
protected static final String EMPRESA = "Eléctrica SA";
    protected static double SUELDO_BASE = 1000;

    protected String nombre;
    protected int edad;
    protected double porcentajeIncremento;

protected empleados_3(String nombre, int edad,double porcentajeIncremento ){
    this.nombre = nombre;
    this.edad = edad;
    this.porcentajeIncremento = porcentajeIncremento;
    
    
} 
protected void verDatos(){
    System.out.println("empresa : "+ EMPRESA + " el empleado: " + nombre + " de edad: "+ edad +"," + "tiene un sueldo base de : " + SUELDO_BASE + " y un incremento de:  " + porcentajeIncremento  );
}



}
class jefe_3 extends empleados_3{
protected String nombreDept;
protected static  double plusJefe = 250;

    protected jefe_3(String nombre, int edad,double porcentajeIncremento , String nombreDept){
        super(nombre, edad, porcentajeIncremento);
        this.nombreDept = nombreDept;
    }
    @Override
    protected void verDatos(){
        super.verDatos();
         System.out.println("Departamento: " + nombreDept + " y un plus de jefe de: " + plusJefe);
    }

    
}
