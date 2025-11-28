package RepasoEV_1;

public class repaso_19 {
    public static void main(String[] args) {
        System.out.println("generador de melodias");
        int factor = (int) (Math.random() * 7) + 1;
        int numnotas = factor * 4;
        
        String nota = " ";

        String melodia = "";
        String primera_nota = "";
        for (int i = 1; i <= numnotas; i++) {
         int notaIndex = (int) (Math.random() * 7) + 1;
            switch (notaIndex) {
                case 1: nota = "do"; break;
                case 2: nota = "re"; break;
                case 3: nota = "mi"; break;
                case 4: nota = "fa"; break;
                case 5: nota = "sol"; break;
                case 6: nota = "la"; break;
                case 7: nota = "si"; break;
            }
            if (i == 1) {
                primera_nota = nota + "";

            }
            melodia += nota + " ";
            if (i % 4 == 0) {
                melodia += "| ";
            }
        }
        int ultimo = melodia.lastIndexOf(" ");
        int penultimo = melodia.lastIndexOf(" ", ultimo - 1);

        melodia = melodia.substring(0, penultimo + 1);
        melodia += primera_nota;
        melodia += "||";

        System.out.println("Longitud de la Melodía: " + numnotas + " notas.");
        System.out.println("Melodía Generada:");
        System.out.println(melodia);
    }
}
