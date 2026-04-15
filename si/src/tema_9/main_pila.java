
package tema_9;
import java.util.Stack;

public class main_pila {
    public static void main(String[] args) {
        // ==========================================
        // EJEMPLO 1: UNA PILA DE TEXTOS (String)
        // ==========================================
        System.out.println("--- PILA DE TEXTOS ---");
        
        // 1. Creamos la pila y le decimos que la <T> será un String
        Pila_gemini<String> pilaHistorial = new Pila_gemini<String>();
        
        // 2. Apilamos páginas web (como si fuera el botón "Atrás" del navegador)
        pilaHistorial.apilar("google.com");
        pilaHistorial.apilar("youtube.com");
        pilaHistorial.apilar("twitch.tv");

        // 3. Desapilamos (Recuerda: ¡El último en entrar es el primero en salir!)
        System.out.println("Saco el último: " + pilaHistorial.desapilar()); // Imprime "twitch.tv"
        System.out.println("Saco el anterior: " + pilaHistorial.desapilar()); // Imprime "youtube.com"


        // ==========================================
        // EJEMPLO 2: UNA PILA DE NÚMEROS (Integer)
        // ==========================================
        System.out.println("\n--- PILA DE NÚMEROS ---");
        
        // 1. Creamos OTRA pila diferente. Ahora la <T> es Integer.
         Pila_gemini<Integer> pilaNumeros = new  Pila_gemini<Integer>();
        
        // 2. Apilamos números
        pilaNumeros.apilar(10);
        pilaNumeros.apilar(50);
        pilaNumeros.apilar(99);
        
        // 3. Desapilamos todo hasta vaciarla
        System.out.println("Saco número: " + pilaNumeros.desapilar()); // Imprime 99
        System.out.println("Saco número: " + pilaNumeros.desapilar()); // Imprime 50
        System.out.println("Saco número: " + pilaNumeros.desapilar()); // Imprime 10
        
        // 4. Si intentamos desapilar otra vez aquí... ¡Boom! 
        // Saltaría el error que programamos: "¡La pila está vacía!"
        // pilaNumeros.desapilar();


 System.out.println("\n--- PILA CON LA CLASE STACK---");

       Stack<String> pila = new Stack<>(); // JAVA YA IMPLEMENTA LA PILA CON STACK//
       //   APILAR//
       pila.push("hola"); 
       pila.push("adios");
              pila.push("fdvfvds");

       
       // DEVUELVE EL ULTIMO ELEMENTO SIN ELIMINAR//

       System.out.println("superior " +pila.peek()); 
       
       //SACA EL ULTIMO ELEMENTO ELIMINANDOLO//

       System.out.println("Sacado: " + pila.pop());
       System.out.println("Nueva cima: " + pila.peek());
    }
}
