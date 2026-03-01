package tema_6;
public class vectores_2 {

    public static void main(String[] args) {
            int [] vectorA = new int [10];
            int [] vectorB = new int [10];
            int [] vectorC = new int [10];
            
            for ( int i  = 0; i<10;i++){
                vectorA[i] = (int) (Math.random()*100);
                vectorB[i] = (int) (Math.random()*100);
                vectorC[i] = vectorA[i] + vectorB[i];
                System.out.print(vectorC[i]+",");
            }
    }
}
