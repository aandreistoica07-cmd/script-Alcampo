package tema9_10;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Scanner;

public class Escanios {

    private class Resultado {
        private String nombrePartido;
        private int cociente;

        public Resultado(String nombre, int cociente) { // cociente = votos / 1 //
            this.nombrePartido = nombre;
            this.cociente = cociente;
        }

        public int getCociente() {
            return this.cociente;
        }

        public String getNombre() {
            return this.nombrePartido;
        }
    }

    ArrayList<Resultado> partidos = new ArrayList<>();
    ArrayList<Resultado> cocientes = new ArrayList<>();

    public void añadirPartidos(ArrayList<Resultado> listaALlenar) {
        Scanner teclado = new Scanner(System.in);
        System.out.println("ingresa el nombre del 'partido");
        String nPart = teclado.nextLine();
        teclado.nextLine();
        System.out.println("ingresa los votos que ha recibido");
        int nvotos = teclado.nextInt();

        Resultado p1 = new Resultado(nPart, nvotos);
        this.partidos.add(p1);
    }

    public void filtrarPartidos(ArrayList<Resultado> listaAFiltrar) {
        int sumaTotal = 0;
        for (Resultado partido : listaAFiltrar) {
            sumaTotal += partido.getCociente();

        }
        double minimoDeVotos = sumaTotal * 0.05;

        for (int i = listaAFiltrar.size() - 1; i >= 0; i--) {
            Resultado p = listaAFiltrar.get(i);

            if (p.getCociente() < minimoDeVotos) {
                listaAFiltrar.remove(i);
            }
        }

    }

    public void calcularCocientes(ArrayList<Resultado> listaFiltrada, int numEscaños) {

        for (Resultado partido : listaFiltrada) {

            for (int i = 1; i <= numEscaños; i++) {
                int numVotos = partido.getCociente();
                int resultadoCociente = (int) (numVotos / i);

                this.cocientes.add(new Resultado(partido.getNombre(), resultadoCociente));
            }

        }
    }

    public void ordenarLista(ArrayList<Resultado> listaCocientes) {
        listaCocientes.sort(Comparator.comparingInt(Resultado::getCociente).reversed());

    }
    
}
