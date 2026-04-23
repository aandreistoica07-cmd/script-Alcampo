package tema9_10;

import java.util.Scanner;

public class main_escanios {
    public static void main(String[] args) {
     Scanner sc = new Scanner(System.in);
        
        // 1. Instanciamos la clase correcta (la máquina)
        Escanios votacion = new Escanios();

        // 2. Necesitamos saber cuántos escaños repartir
        System.out.println("¿Cuántos escaños se reparten en total?");
        int nEscanios = sc.nextInt();

        // 3. Añadimos partidos (puedes meter esto en un bucle para añadir varios)
        // Usamos la lista 'partidos' que está dentro del objeto votacion
        votacion.añadirPartidos(votacion.partidos); 
        votacion.añadirPartidos(votacion.partidos); // Añadimos otro por ejemplo
         votacion.añadirPartidos(votacion.partidos); 
        votacion.añadirPartidos(votacion.partidos); // Añadimos otro por ejemplo
         
        // 4. Ejecutamos el flujo en orden pasando los ingredientes
        votacion.filtrarPartidos(votacion.partidos);
        
        votacion.calcularCocientes(votacion.partidos, nEscanios);
        
        // Al final, usamos la lista de cocientes que se ha ido llenando
        votacion.sacarEscanios(votacion.cocientes, nEscanios);
    }
}
