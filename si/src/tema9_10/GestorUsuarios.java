package tema9_10;

import java.util.HashSet;

public class GestorUsuarios {
   private  HashSet<Registro> baseDatos ;

    public GestorUsuarios(){
        this.baseDatos = new HashSet<>();
    }

    private Registro buscarRegistro( String nombreUsuario){
        for (Registro reg : baseDatos) {
            if (reg.getUsuario().equals(nombreUsuario)) {
                return reg; 
            }
        }
        return null;
    }

    public void insertarUsuario(String usuario , String clave){
        try {
            Registro nuevoRegistro = new Registro(usuario, clave);

            boolean insertado = baseDatos.add(nuevoRegistro);

            if (insertado) {
                System.out.println("Usuario '" + usuario + "' registrado correctamente.");
            } else {
                System.out.println("Error: El usuario '" + usuario + "' ya existe en el sistema.");
            }
        } catch(IllegalArgumentException e){
            System.out.println("Error al registrar: " + e.getMessage());
        }
    }

    public void eliminarUsuario(String usuario){
        Registro registroEncontrado = buscarRegistro(usuario);

        // El remove devolverá false si registroEncontrado es null o no está en la lista
        boolean eliminado = baseDatos.remove(registroEncontrado);
        
        if (eliminado){
            System.out.println("Usuario '" + usuario + "' borrado del sistema.");
        } else {
            System.out.println("Error: No se puede borrar, el usuario no existe.");
        }
    }

    public void modificarClave(String usuario, String nuevaClave) {
        Registro registroEncontrado = buscarRegistro(usuario);

        if (registroEncontrado != null) {
            registroEncontrado.setContrasenia(nuevaClave);
        } else {
            System.out.println("Error: El usuario no existe.");
        }
    }

    public void validarAcceso(String usuario , String contrasenia){
        Registro registroEncontrado = buscarRegistro(usuario);

        // 1. Controlamos el caso de que el usuario no exista para evitar el crasheo
        if (registroEncontrado == null) {
            System.out.println("Acceso Denegado: El usuario no existe.");
            return; // Cortamos la ejecución aquí
        }

        // 2. Si llegamos aquí, el usuario existe, comprobamos su clave
        boolean valido = registroEncontrado.comprobarClave(contrasenia);
        if (valido){
            System.out.println("¡Acceso Concedido! Clave correcta.");
        } else {
            System.out.println("Acceso Denegado: Clave incorrecta.");
        }
    }
}
