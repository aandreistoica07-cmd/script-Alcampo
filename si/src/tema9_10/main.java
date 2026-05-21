package tema9_10;

import java.util.ArrayList;

public class main {
public static void main(String[] args) {
ArrayList<alumnos> miLista = new ArrayList<>();

 alumnos gestor = new alumnos(0, "", "", 0, 0, 0);

  gestor.rellenarLista(miLista);

        System.out.println("--- ORDENADO POR NOMBRE Y APELLIDO ---");
        gestor.ordenarNombre_Apellido(miLista);

        System.out.println("\n--- ORDENADO POR NOTA MEDIA (MAYOR A MENOR) ---");
        gestor.ordenarNotaMedia(miLista);

}
}
