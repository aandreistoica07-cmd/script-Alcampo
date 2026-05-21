package tema_9;

public class main {
    public static void main(String[] args) {
        int [] misNumeros = new int[100000];

        for (int i = 0; i< misNumeros.length;i++){
            misNumeros[i] = (int) (Math.random()*100000) +1;
        }

    
        
       System.out.println("Vector generado. Empezando a ordenar...");

         Ordenar miAlgoritmo = new Seleccion();

        long tiempoInicio = System.currentTimeMillis();

         miAlgoritmo.ordenar(misNumeros);

        long tiempoFin = System.currentTimeMillis();

        for (int i = 0; i < misNumeros.length;i++){
            System.out.print(misNumeros[i]+",");
        }
        System.out.println();
        long tiempoTotal = tiempoFin-tiempoInicio;
        System.out.println("¡Terminado! La Burbuja ha tardado: " + tiempoTotal + " milisegundos.");
    }
}
