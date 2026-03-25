package tema_6;
public class vectores_1 {

    public static void main(String[] args) {
        int[] numeroAleatorio = new int[20];
        int suma = 0;
        for (int i = 0; i < numeroAleatorio.length; i++) {

            numeroAleatorio[i] = (int) (Math.random() * 100);

            suma += numeroAleatorio[i];
            System.out.print(numeroAleatorio[i] + ",");

        }
        System.out.println();

        double media = (double) suma / numeroAleatorio.length;
        System.out.println("La media es: " + media);

        System.out.println("numeros mayores que la media");
        for (int i = 0; i < numeroAleatorio.length; i++) {
            if (numeroAleatorio[i] > media) {
                System.out.print(numeroAleatorio[i] + ",");
            }
        }
        System.out.println();
        System.out.println();
        System.out.println("numeros menores que la media");
        for (int i = 0; i < numeroAleatorio.length; i++) {
            if (numeroAleatorio[i] < media) {
                System.out.print(numeroAleatorio[i] + ",");
            }
        }
        System.out.println();
        System.out.println();
        System.out.println("numeros iguales  que la media");
        for (int i = 0; i < numeroAleatorio.length; i++) {
            if (numeroAleatorio[i] == media) {
                System.out.print(numeroAleatorio[i] + ",");
            }
        }
    }
}
