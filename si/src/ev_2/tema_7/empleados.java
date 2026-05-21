package tema_7;

public class empleados {
private String nombre;
private double sueldo;

public empleados(String nombre, double sueldo){
    this.nombre=nombre;
    this.sueldo=sueldo;
}

public String getNombre(){
    return nombre;
}
public double getSueldo(){
    return sueldo;
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

}
