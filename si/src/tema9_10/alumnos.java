package tema9_10;
import java.util.ArrayList;
import java.util.Comparator;

public class alumnos {
private int id;
private String nombre;
private String apellido;
private double notaMedia;


ArrayList<alumnos> listaAlumnos = new ArrayList<>();


public alumnos(int id,String nombre,String apellido,double n1,double n2, double n3){
    this.id =id;
    this.nombre = nombre;
    this.apellido = apellido;
    this.notaMedia = (n1+n2+n3)/3.0 ;
}

public String getApellido(){
    return this.apellido;
}
public String getNombre(){
    return this.nombre;
}
public double getMedia(){
    return this.notaMedia;
}

public void rellenarLista(ArrayList<alumnos> listaAllenar){
    String[] nombres = {
    "Juan", "María", "Carlos", "Elena", "Diego", 
    "Lucía", "Sergio", "Paula", "Marc", "Alba"
};

String[] apellidos = {
    "García", "Rodríguez", "López", "Sánchez", "Pérez", 
    "Martínez", "Gómez", "Ruiz", "Díaz", "Hernández"
};
   
    for (int i = 0; i < 50 ; i++){
       int randnombre = (int)(Math.random()*10);
        int randApellido = (int) (Math.random()*10);
        int randN1 = (int) (Math.random()*101);
        int randN2 = (int) (Math.random()*101);
        int randN3 = (int) (Math.random()*101); 
        
        alumnos miAlumno = new alumnos(i, nombres[randnombre], apellidos[randApellido], randN1, randN2, randN3);

        listaAllenar.add(miAlumno);

    }

    
}

public void ordenarNombre_Apellido(ArrayList<alumnos> listaLlena){
        listaLlena.sort(Comparator.comparing(alumnos::getApellido).thenComparing(alumnos::getNombre));

        listaLlena.forEach(alumno -> System.out.println(alumno.getApellido() + ","+ alumno.getNombre() ));
    }

public void ordenarNotaMedia(ArrayList<alumnos> listaLlena){
        listaLlena.sort(Comparator.comparing(alumnos::getMedia).reversed());

        listaLlena.forEach(alumno -> System.out.println(alumno.getApellido() + ","+ alumno.getNombre() + "," + alumno.getMedia()));
    }    

}
