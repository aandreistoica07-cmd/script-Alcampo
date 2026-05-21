package tema_11;

import java.io.*;

public class combinacion {

    public static void main(String[] args) throws IOException {

        if (args.length != 3) {
            System.out.println("debes ingresar 3 ficheros");
            return;
        }

        String fichero1 = args[0];
        String fichero2 = args[1];
        String combinacion = args[2];

        BufferedReader br = new BufferedReader(new FileReader(fichero1));
        BufferedReader br1 = new BufferedReader(new FileReader(fichero2));
        BufferedWriter bw = new BufferedWriter(new FileWriter(combinacion));

        String linea1 = br.readLine();
        String linea2 = br1.readLine();

        while (linea1 != null || linea2 != null) {
            if (linea1 != null) {
              bw.write(linea1);
              bw.newLine();
              linea1 = br.readLine();
              


            }

            if (linea2 != null) {
              bw.write(linea2);
              bw.newLine();
              linea2 = br1.readLine();
            }

          }
          
          br.close();
         br1.close();
         bw.close();
        }
}
