package tema9_10;

public class Registro {
    private String usuario;
    private String contrasenia;

    public Registro(String usuario, String contrasenia) {
        this.usuario = usuario;
        
        // Comprobamos si el formato es válido antes de cifrar y guardar
        if (this.formatoValido(contrasenia)) {
            this.contrasenia = this.cifradoCesar(contrasenia);
        } else {
            // Si tiene símbolos raros, paramos la creación y avisamos del error
            throw new IllegalArgumentException("La contraseña solo debe contener letras y números.");
        }
    }

    public String getUsuario() {
        return this.usuario;
    }

    public String getContrasenia() {
        return this.contrasenia;
    }

    public void setContrasenia(String nuevaContrasenia) {
        // También validamos y ciframos cuando nos piden cambiar la contraseña
        if (this.formatoValido(nuevaContrasenia)) {
            this.contrasenia = this.cifradoCesar(nuevaContrasenia);
        } else {
            System.out.println("Error: Formato de la nueva contraseña incorrecto.");
        }
    }

    private boolean formatoValido(String contrasenia) {
        for (int i = 0; i < contrasenia.length(); i++) {
            char c = contrasenia.charAt(i);
            
            // Si el carácter NO es un número ('0'-'9') Y NO es mayúscula Y NO es minúscula...
            if (!(c >= '0' && c <= '9' || c >= 'A' && c <= 'Z' || c >= 'a' && c <= 'z')) {
                return false; // ¡Encontramos un intruso! La contraseña es inválida.
            }
        }
        return true; // Si revisa todas las letras y están bien, es válida.
    }

    private String cifradoCesar(String contrasenia) {
        int desplazamiento = 3;
        String cifrado = "";

        for (int i = 0; i < contrasenia.length(); i++) {
            char c = contrasenia.charAt(i);
            
            // ¡Importante el paréntesis para que sume el número antes de convertir a letra!
            cifrado += (char) (c + desplazamiento);
        }
        return cifrado;
    }

    /**
     * Comprueba si un intento de contraseña (texto normal) coincide
     * con la contraseña cifrada que tenemos guardada en este objeto.
     */
    public boolean comprobarClave(String intentoBruto) {
        // 1. Ciframos lo que el usuario acaba de escribir
        String intentoCifrado = this.cifradoCesar(intentoBruto);
        
        // 2. Comparamos si coincide exactamente con la que tenemos guardada
        return this.contrasenia.equals(intentoCifrado);
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) { // si comparas un objeto con el mismo devuelve true
            return true;
        }

        if (obj == null || this.getClass() != obj.getClass()) { // si el objeto es nulo o de otra clase, false
            return false;
        }

        Registro otroRegistro = (Registro) obj; // casting para llamar al getter

        // Solo comparamos por usuario para que el HashSet no admita repetidos
        return this.usuario.equals(otroRegistro.getUsuario());
    }

    @Override
    public int hashCode() {
        return (this.usuario == null) ? 0 : this.usuario.hashCode();
    }
}