package tema_9;

public class Pila_gemini<T> {
    private class Nodo{
       private  T dato;
        Nodo enlace;

        public Nodo(){ //constructor//
            this.dato = null;
            this.enlace = null;
        }

        public Nodo getEnlace(){
            return this.enlace;
        }
        public void setEnlace(Nodo x){
            this.enlace = x;
        }

        public T getDato(){
            return this.dato;
        }

        public void setDato(T e){
            this.dato = e;
        }
    }
    private Nodo cima;

    public Pila_gemini(){ //constructor//
        this.cima = null;
    }

    public void apilar( T e){
       Nodo aux = new Nodo();
       aux.setDato(e);
       aux.setEnlace(cima);

       this.cima = aux;
    }

    public T desapilar(){
        if (cima == null){
            throw new IllegalStateException();
        }
        Nodo aux = cima;
        cima = aux.getEnlace();

        return aux.getDato();
    }
}
