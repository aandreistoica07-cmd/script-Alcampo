package tema_7.visibilidad1;
import tema_7.visibilidad2.EmpleadoEspecial;

public class JefeEspecial extends EmpleadoEspecial{
    public JefeEspecial() {
        super(); // [cite: 36, 41]
       // Escribe 'super.' y observa:
    this.nombreEs = "Juan";    // Te deja (es public)
    this.direcciones = "BCN";  // Te deja (es protected, aunque estés en otro paquete)
    
    // ESTOS DARÁN ERROR:
    this.sueldoEs = 500.0f;    // ERROR: es private
    this.edad = 20;            // ERROR: es default y estás en el paquete visibilidad1
    }
}
