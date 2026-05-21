package tema_9;

public class Burbuja extends Ordenar {

    public void ordenar(int[] vector){
        int aux = 0;
        
        for (int i = 0; i < vector.length -1;i++){
                for (int j = 0; j < vector.length -1 - i; j++){
                    if (vector[j]> vector[j+1]){
                        aux = vector[j];
                        vector[j]= vector[j+1];
                        vector[j+1]= aux;

                    }
                }
        }
    }

}
