package tema9_10;

public class Pila_10 {

    private int[] vector;
    private int cima;

    public Pila_10() {
        // Inicializamos el vector con tamaño máximo de 100
        this.vector = new int[100];
        // Cuando la pila está vacía, la cima es -1
        this.cima = -1;
    }

    public void push(int dato) {
        if (cima > 100) {
            throw new IllegalStateException();
        }
        cima++;
        vector[cima] = dato;
    }

    public int pop() {
        if (cima == -1) {
            throw new IllegalStateException();
        }

        int datoExtraido = vector[cima];
        cima--;
        return datoExtraido;
    }

    public int size() {
        return cima + 1;
    }

}
