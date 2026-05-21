package tema_11;

import java.io.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class ordenar {

    public static void main(String[] args) throws IOException {
        int archivosEsperados = 1;
        String archivoEntrada = args[0];
        String archivoSalida = archivoEntrada.replace(".txt", "") + "_sort.txt";

        if (args.length != archivosEsperados) {
            throw new IllegalArgumentException("se esperaban: " + archivosEsperados + " archivos" + "se recibieron: " + args.length);

        }

        BufferedReader br = new BufferedReader(new FileReader(archivoEntrada));
        BufferedWriter bw = new BufferedWriter(new FileWriter(archivoSalida));

        String palabra = br.readLine();
        List<String> palabras = new ArrayList<>();

        while (palabra != null) {
                palabras.add(palabra);
                palabra = br.readLine();
            

        }
        Collections.sort(palabras);
        for (String palabraOrdenada : palabras) {
            bw.write(palabraOrdenada);
            bw.newLine();
        }
        br.close();
        bw.close();
    }

}
