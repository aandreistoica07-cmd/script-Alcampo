package tema_9;

public class Pila { // <T> genericos de java//

    private class Nodo{
        Elemento dato; //sustituir Elemento por T//
        Nodo enlace;

    }
    Nodo pila >= null;

   public void apilar (Elemento e){ //T//
        Nodo aux = new Nodo;
        aux - dato = e;
        aux.enlace = pila;
        pila = aux;
    }

    public Elemento desapilar(){ //T//
        if (pila == null){
            throw new 
        }
        Nodo aux = pila;
        pila = aux.enlace;
        return aux.dato;
    }

    /*
    Pila (tipo x){
        Nodo{
            x dato
            ....
        }        
    Pila (Integer) pi = new Pila();
    Pila (Elemento) pe = new Pila();
    }
    */

    /*
    Pila <Elemento> pe = new Pila <Elemento>();
    Pila <Integer> pi = new Pila <Integer>();

    en vez de Clase variable = new clase(); --> Clase = Pila < Elemento>
    Pila <Electrodomestico> pl = new Pila <Electrodomestico>();

    <t>
    <t,s,a>
    <t extends Clase && Intefaz 1 && Interfaz 2....>
    
    */
}
