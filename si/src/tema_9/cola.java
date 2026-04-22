package tema_9;

public class cola<T> {
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

    private Nodo inicio = new Nodo();
    private Nodo finalCola = new Nodo();

    public cola(){
        this.inicio = null;
        this.finalCola  = null;
    }

    public void encolar(T e){
        Nodo aux = new Nodo();
        aux.setDato(e);
        aux.setEnlace(null);

        
    }
}
