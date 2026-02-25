public class conjunto {
    private int[] conjunto = new int[100];
    private int contador = 0;

    public void agregar(int numero) {

        for (int i = 0; i < contador; i++) {
            if (conjunto[i] == numero) {
                System.out.println("numero repetido");
                return;

            }
        }

        if (contador >= 100) {
            System.out.println("Conjunto lleno");
            return;
        }

        conjunto[contador] = numero;
        contador++;
        System.out.println("Número agregado: " + numero);

    }

    public void vaciar() {
        contador = 0;
    }

    public void eliminar(int numeroElim) {
        for (int i = 0; i < contador; i++) {
            if (conjunto[i] == numeroElim) {
                for (int j = i; j < contador - 1; j++) {
                    conjunto[j] = conjunto[j + 1];
                }
                contador--;
                return;
            }
        }

        System.out.println("numero no encontrado" + numeroElim);
    }

    public void copiar(conjunto destino) {
        destino.vaciar();
        for (int i = 0; i < this.contador; i++) {
            destino.agregar(this.conjunto[i]);
        }
    }

    public boolean esMiembro(int numero) {
        for (int i = 0; i < contador; i++) {
            if (conjunto[i] == numero)
                return true;
        }
        return false;
    }

    public boolean esIgual(conjunto otro) {
        if (this.contador != otro.contador) {
            return false;
        }
        for (int i = 0; i < this.contador; i++) {
            if (!otro.esMiembro(this.conjunto[i]))
                return false;
        }
        return true;
    }

    public void imprimir() {
        System.out.print("{ ");
        for (int i = 0; i < contador; i++) {
            System.out.print(conjunto[i]);
            if (i < contador - 1) System.out.print(", ");
        }
        System.out.println(" }");
    }

    public static void main(String[] args) {
        
    }
}