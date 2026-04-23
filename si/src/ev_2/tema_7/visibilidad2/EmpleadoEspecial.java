package tema_7.visibilidad2;

public class EmpleadoEspecial {
    public String nombreEs;     // Accesible desde cualquier lugar [cite: 27]
    private float sueldoEs;     // Solo accesible dentro de esta clase [cite: 28]
    protected String direcciones; // Accesible por hijos o mismo paquete [cite: 29]
    int edad;
}
