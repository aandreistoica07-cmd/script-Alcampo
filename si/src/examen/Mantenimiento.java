package examen;
/*
    Interfaz que define las operaciones de mantenimiento.
     @author Alex Stoica
*/
public interface Mantenimiento {
    /**
     * Indica si el dispositivo necesita una revisión.
     * @return true si debe revisarse, false en caso contrario.
     */
    boolean debeRevisarse();
    
    /**
     * Resetea los contadores al pasar la revisión.
     */
    void pasarRevision();
    
}
