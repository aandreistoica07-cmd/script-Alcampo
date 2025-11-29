package RepasoEV_1;
public class repaso_20 {
public static void main(String[] args) {
    String figura = "";
     int contadorcorazon = 0;
     int contadordiamante = 0;
     int contadorherradura = 0;
     int contadorcampana = 0;
     int contadorlimon = 0;
    int moneda = 1;
for (int i =0; i<6;i++){
    int simbolosRandom =(int) (Math.random() * (5 ) ) + 1 ;
    switch(simbolosRandom){
        case 1 : figura = "corazon"; contadorcorazon++ ; break;
        case 2 : figura = "diamante"; contadordiamante++; break;
        case 3 : figura = " herradura"; contadorherradura++; break;
        case 4 : figura = " campana"; contadorcampana++; break;
        case 5 : figura = " limon"; contadorlimon++; break;
    
       
    }
    moneda--;
    System.out.println("has gastado una moneda");
    System.out.print(figura + " ");
}

if (contadorcampana>3 || contadordiamante> 3 || contadorcorazon> 3 || contadorherradura > 3 || contadorlimon> 3 ){
    System.out.println("felicidades has ganado toma de vuelta tu moneda");
    moneda++;
    System.out.println(moneda);
}

}
}