package repaso_arrays;

public class parYMayor25 {

    public static void main(String[] args) {
        int[]original = {4,7,0,5,1,2,15,93,25,12,82,87,100};
        int [] destino = new int [original.length];
        int aux=0;


        for (int i = 0; i < original.length;i++){
            if(original[i]%2 == 0 && original[i]>25){
                aux = original[i];
            }
            for (int j = 0; j< destino.length;j++){
                destino[j]= aux;
            }
        }

            
    }
}
