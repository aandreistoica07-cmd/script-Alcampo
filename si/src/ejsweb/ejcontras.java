package ejsweb; 


import java.util.Scanner;



public class ejcontras {

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        // --- 1. DECLARACIÓN DE VARIABLES ---
        int contrasena;
        int puntos = 0;
        boolean todosIguales = true;
        long inverso = 0; // Usamos 'long' para asegurar que el inverso no desborde, aunque con 4 dígitos 'int' es suficiente.
        int contadorPar = 0;
        int contadorImpar = 0;
        int contadorMult3 = 0;
        int digitoAnterior = -1; // Usado para comparar el dígito actual con el anterior
        int numDigitos = 0;
        int tempNum;

        // --- 2. ENTRADA Y VALIDACIÓN DE LONGITUD ---
        System.out.println("Sistema de Calificación de Contraseñas (Ev1)");
        System.out.print("Introduce una contraseña de exactamente 4 dígitos (ej: 1234): ");
        
        if (scanner.hasNextInt()) {
            contrasena = scanner.nextInt();
        } else {
            System.out.println("Entrada inválida. Debe ser un número entero.");
            return;
        }

        // Validación inicial de la longitud (usando una copia)
        tempNum = contrasena;
        if (tempNum < 0) { // Manejar números negativos
            tempNum = Math.abs(tempNum);
        }
        
        int originalCompleto = tempNum; // Guardamos el valor positivo original para el análisis
        
        // Contar dígitos
        if (tempNum == 0) {
             numDigitos = 1; // El 0 tiene 1 dígito
        } else {
            while (tempNum > 0) {
                tempNum = tempNum / 10;
                numDigitos++;
            }
        }
        
        if (numDigitos != 4) {
            System.out.println("Error. La contraseña debe tener exactamente 4 dígitos. Se introdujeron " + numDigitos + ".");
            return;
        }

        // --- 3. BUCLE DE ANÁLISIS DÍGITO A DÍGITO ---
        
        // Reiniciamos tempNum con el valor original para el análisis
        tempNum = originalCompleto; 

        while (tempNum > 0) {
            // 1. CAPTURAR el último dígito (Módulo)
            int digito = tempNum % 10;
            
            // 2. ELIMINAR el último dígito (División Entera)
            tempNum = tempNum / 10;
            
            // --- ANÁLISIS DE CONDICIONES DENTRO DEL BUCLE ---

            // A. Condición de Capicúa: Reconstrucción del Inverso
            // Nota: El inverso se construye de derecha a izquierda (último dígito se convierte en el primero)
            inverso = (inverso * 10) + digito; 

            // B. Condición Todos Iguales
            if (digitoAnterior != -1 && digito != digitoAnterior) {
                todosIguales = false;
            }
            digitoAnterior = digito; // Actualizar el dígito anterior para la próxima iteración

            // C. Puntuación: Par/Impar
            if (digito % 2 == 0) {
                contadorPar++;
            } else { 
                contadorImpar++;
            }

            // D. Puntuación: Múltiplo de 3 (+2 pts por ocurrencia, excluyendo 0)
            if (digito % 3 == 0 && digito != 0) {
                contadorMult3++;
            }
        }
        
        // Asignar puntos acumulados por Múltiplo de 3
        puntos += (contadorMult3 * 2); 

        // --- 4. ASIGNACIÓN DE PUNTOS FINALES Y CLASIFICACIÓN ---

        System.out.println("\n--- Análisis de Puntos ---");

        // 1. Capicúa (+10 pts)
        // La comparación se hace con 'originalCompleto' (int) e 'inverso' (long)
        if (originalCompleto == inverso) {
            puntos += 10;
            System.out.println("+10 pts: Es Capicúa.");
        }

        // 2. Par y Impar (+5 pts)
        if (contadorPar > 0 && contadorImpar > 0) {
            puntos += 5;
            System.out.println("+5 pts: Contiene dígitos pares e impares.");
        }

        // 3. Todos Iguales (-5 pts)
        if (todosIguales) {
            puntos -= 5;
            System.out.println("-5 pts: Todos los dígitos son iguales.");
        }

        System.out.println("\n--- Resultado ---");
        System.out.println("Contraseña analizada: " + originalCompleto);
        System.out.println("Puntuación Total: " + puntos + " puntos");

        // --- CLASIFICACIÓN FINAL ---
        if (puntos >= 15) {
            System.out.println("Clasificación: Contraseña Fuerte 💪");
        } else if (puntos >= 5) {
            System.out.println("Clasificación: Contraseña Moderada 👍");
        } else {
            System.out.println("Clasificación: Contraseña Débil 🤏");
        }
        
        scanner.close();
    }
}
