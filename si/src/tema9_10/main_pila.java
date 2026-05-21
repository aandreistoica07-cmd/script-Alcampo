package tema9_10;

public class main_pila {
    public static void main(String[] args) {
        Pila_10 miPila = new Pila_10();
        
        for (int i = 0; i < 100; i++) {

            int randNum = (int) (Math.random() * 10000) + 1;

            miPila.push(randNum);
            System.out.println("Apilado el número: " + randNum);
        }

        System.out.println("\nTamaño actual tras apilar: " + miPila.size());

        while(miPila.size()>0){
           int extraido =  miPila.pop();
           System.out.println("Elemento extraído: " + extraido + " | Tamaño restante: " + miPila.size());
        }
    }
}
