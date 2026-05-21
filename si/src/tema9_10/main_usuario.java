package tema9_10;

import java.util.Scanner;

public class main_usuario{

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        GestorUsuarios gestor = new GestorUsuarios();
        int opcion = 0;

        System.out.println("==========================================");
        System.out.println("  SISTEMA DE GESTIÓN DE USUARIOS SEGURO   ");
        System.out.println("==========================================");

        do {
            System.out.println("\n--- MENÚ PRINCIPAL ---");
            System.out.println("1. Insertar nuevo usuario");
            System.out.println("2. Borrar usuario");
            System.out.println("3. Modificar clave de usuario");
            System.out.println("4. Validar acceso");
            System.out.println("5. Salir");
            System.out.print("Elige una opción (1-5): ");

            // TRUCO SENIOR: Leemos como texto y convertimos a número para evitar 
            // el famoso bug del Scanner cuando mezclas nextInt() con nextLine().
            try {
                opcion = Integer.parseInt(scanner.nextLine());
            } catch (NumberFormatException e) {
                opcion = 0; // Forzamos a que salte al 'default' del switch
            }

            String usuario;
            String clave;

            switch (opcion) {
                case 1:
                    System.out.print("Introduce el nombre de usuario: ");
                    usuario = scanner.nextLine();
                    System.out.print("Introduce la contraseña (solo letras y números): ");
                    clave = scanner.nextLine();
                    
                    gestor.insertarUsuario(usuario, clave);
                    break;

                case 2:
                    System.out.print("Introduce el nombre del usuario a borrar: ");
                    usuario = scanner.nextLine();
                    
                    gestor.eliminarUsuario(usuario);
                    break;

                case 3:
                    System.out.print("Introduce el nombre de usuario: ");
                    usuario = scanner.nextLine();
                    System.out.print("Introduce la NUEVA contraseña: ");
                    clave = scanner.nextLine();
                    
                    gestor.modificarClave(usuario, clave);
                    break;

                case 4:
                    System.out.print("Usuario: ");
                    usuario = scanner.nextLine();
                    System.out.print("Contraseña: ");
                    clave = scanner.nextLine();
                    
                    gestor.validarAcceso(usuario, clave);
                    break;

                case 5:
                    System.out.println("\nCerrando el sistema... ¡Hasta pronto!");
                    break;

                default:
                    System.out.println("Error: Opción no válida. Por favor, introduce un número del 1 al 5.");
            }

        } while (opcion != 5);

        scanner.close();
    }
}