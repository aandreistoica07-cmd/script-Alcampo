import tema_5.disco;

public class coleccion {

    private disco[] listaDiscos;
    private int indice;

    // constructor//
    public coleccion() {
        this.listaDiscos = new disco[100];
        this.indice = 0;
    }

    public void insertar(disco nuevoDisco) {
        if (indice < 100) {
            listaDiscos[indice] = nuevoDisco;
            indice++;
        } else {
            System.out.println("coleccion llena");
        }
    }

    public void eliminar(String discoABuscar) {
        boolean encontrado = false;
        int i = 0;
        while (i < indice && !encontrado) {
            if (listaDiscos[i].gettitulo().equals(discoABuscar)) {
                // desplazar indice a la izquierda//
                for (int j = i; j < indice - 1; j++) {
                    listaDiscos[j] = listaDiscos[j + 1];
                }

                listaDiscos[indice - 1] = null;

                indice--;
                encontrado = true;
                System.out.println("Disco eliminado.");
            } else {
                i++;
            }

            if (!encontrado) {
                System.out.println("no se encontro tu libro");
            }
        }
    }

    public void verLista() {
        System.out.println("--- ESTADO DE LA COLECCIÓN (" + indice + "/100) ---");
        if (indice == 0) {
            System.out.println(" no hay discos en tu coleccion");
        } else {
            for (int i = 0; i < indice; i++) {
                System.out.println("  [" + i + "] " + listaDiscos[i].gettitulo());
            }
        }
    }

    public static void main(String[] args) {
        coleccion miMusica = new coleccion();

        disco d1 = new disco("Thriller", 9, 15, "12-05-1982");
        disco d2 = new disco("Back in Black", 10, 20, "25-07-1980");
        disco d3 = new disco("Rumours", 11, 12, "04-02-1977");

        miMusica.insertar(d1);
        miMusica.insertar(d2);
        miMusica.insertar(d3);

         miMusica.verLista();
         miMusica.eliminar("Thriller");
         miMusica.verLista();
    }
}
