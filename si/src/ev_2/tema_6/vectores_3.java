package tema_6;
public class vectores_3 {
    public static void main(String[] args) {
        int[] vector = new int[10];
        vector[0] = (int) (Math.random() * 100);
        int mayor = vector[0] ;
        int posMayor = 0 ;
        int menor =vector [0];
        int posMenor = 0;
        for ( int i  = 1 ; i< vector.length;i++){
            vector[i]  = (int) (Math.random()*100);
            if (vector [i]> mayor){
               mayor = vector[i];
                posMayor = i;
            }else if (vector[i]< menor){
                menor = vector[i];
                posMenor = i;
            }
            System.out.print(vector[i]+",");
        }
        System.out.println();
        System.out.println("el mayor es : "+ mayor + " y su posicion es : "+ posMayor);
                System.out.println("el menor es : "+ menor+ " y su posicion es : "+ posMenor);
                
                

    }
}
