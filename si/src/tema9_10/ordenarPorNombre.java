package tema9_10;
import java.util.Comparator;
public class ordenarPorNombre implements Comparator<alumnos> {
    @Override
    public int compare(alumnos o1 , alumnos o2){
        int res = o1.getApellido().compareTo(o2.getApellido());

        if (res == 0){
           res =  o1.getNombre().compareTo(o2.getNombre());
        }

        return res; 
    }
}
