package tema_9;

public class Elemento {
private int dato;
private Elemento siguiente;

public Elemento(int numero) {
        this.dato = numero;
        this.siguiente = null; // Al nacer, la cuerda no está atada a nadie
    }

public int getDato() { return dato; }
    public void setDato(int dato) { this.dato = dato; }

    // Métodos para la cuerda (siguiente)
    public Elemento getSiguiente() { return siguiente; }
    public void setSiguiente(Elemento siguiente) { this.siguiente = siguiente; }
}
