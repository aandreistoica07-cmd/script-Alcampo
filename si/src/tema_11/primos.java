package tema_11;

import java.io.*;
import java.util.*;

public class primos {

    public static void main(String[] args) throws IOException {
        ArrayList<Integer> listaPrimos = new ArrayList<>();

        for (int i = 2; i <= 50; i++) {
            listaPrimos.add(i);
        }

        for (int i = 0; i < listaPrimos.size(); i++) {
            int primoActual = listaPrimos.get(i);
            for (int j = i + 1; j < listaPrimos.size(); j++) {
                if (listaPrimos.get(j) % primoActual == 0) {
                    listaPrimos.remove(j);
                    j--;
                }
            }
        }

        // ✍️ ESCRIBIR
        BufferedWriter escritor = new BufferedWriter(new FileWriter("si\\src\\tema_11\\lista.txt"));
        for (int numero : listaPrimos) {          // foreach es más limpio
            escritor.write(String.valueOf(numero)); // ✅ convierte int a texto
            escritor.newLine();                    // ✅ cada primo en su línea
        }
        escritor.close();

        // 📖 LEER
        BufferedReader lector = new BufferedReader(new FileReader("si\\src\\tema_11\\lista.txt"));
        ArrayList<Integer> listaLeida = new ArrayList<>(); // ✅ Integer, no String
        String linea;
        while ((linea = lector.readLine()) != null) {
            listaLeida.add(Integer.parseInt(linea)); // ✅ convierte texto a int
        }
        lector.close();

        System.out.println(listaLeida);
    }
}