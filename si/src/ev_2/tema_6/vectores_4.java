package tema_6;
public class vectores_4 {
    public static void main(String[] args) {
        int[] vectorA = new int[10];
        int[] vectorB = new int[10];
        // devolver array entre 1 y 5
        for (int i = 0; i < vectorA.length; i++) {
            vectorA[i] = (int) (Math.random() * 5) + 1;
            vectorB[i] = (int) (Math.random() * 5) + 1;
        }
        // imprimir arrays//
        for (int i = 0; i < 10; i++) {
            System.out.print(vectorA[i] + ",");
        }
        System.out.println();
        for (int i = 0; i < 10; i++) {
            System.out.print(vectorB[i] + ",");
        }
        System.out.println();

        for (int i = 0; i < 10; i++) {
            int contador = 0;
            for (int j = 0; j < 10; j++) {
                if (vectorA[i] == vectorB[j]) {
                    contador++;
                }
            }
            System.out.println("elemento " + (i + 1) + " (" + vectorA[i] + "): " + contador + " veces");
        }
    }
}
