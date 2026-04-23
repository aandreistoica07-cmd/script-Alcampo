package tema_7.visibilidad1;
import tema_7.visibilidad2.EmpleadoEspecial; // [cite: 33]

import tema_5.empleado;

public class Jefe extends Empleado {
    public Jefe() {
        super(); 
       // Escribe 'super.' y observa la lista:
    this.nombre = "Pepe";     // Te deja (es default/package)
    this.direccion = "Calle";  // Te deja (es protected)
    this.edad = 30;           // Te deja (es public)
    
    // Si intentas poner el siguiente, saldrá un ERROR (subrayado rojo):
    this.sueldo = 1000;
        
    }
}
