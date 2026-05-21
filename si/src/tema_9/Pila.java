package tema_9;

public class Pila {
    private int elemento[];
    private int cima;

    public Pila (int capacidad){
        if (capacidad <=0){
            throw new IllegalArgumentException();
        }
        Elemento v = new Elemento(capacidad);
        cima = 0;
       
        
    }

    public void apilar(int numero){
        Elemento nuevoDato = new Elemento(numero);
        nuevoDato.setSiguiente(numero)
    }
}
