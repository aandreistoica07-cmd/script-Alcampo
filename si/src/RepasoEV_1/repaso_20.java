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
    int mayor =0;
for (int i =0; i<3;i++){
    int simbolosRandom =(int) (Math.random() * (5 ) ) + 1 ;
    switch(simbolosRandom){
        case 1 : figura = "corazon"; contadorcorazon++ ; break;
        case 2 : figura = "diamante"; contadordiamante++; break;
        case 3 : figura = " herradura"; contadorherradura++; break;
        case 4 : figura = " campana"; contadorcampana++; break;
        case 5 : figura = " limon"; contadorlimon++; break;
    
       
    }
    
    System.out.print(figura + " ");

}
moneda--;
    System.out.println("has gastado una moneda");
if (contadorcorazon>mayor){
    mayor = contadorcorazon;
} if (contadordiamante>mayor){
    mayor = contadordiamante;
}if (contadorcampana>mayor){
    mayor = contadorcampana;
}if (contadorherradura>mayor){
    mayor = contadorherradura;
}if (contadorlimon> mayor){
    mayor = contadorlimon;
}
if (mayor > 2) {
    System.out.println("felicidades has ganado 10 monedas");
    moneda += 10;
    System.out.println("Monedas actuales: " + moneda);
} else if (mayor == 2) {
    System.out.println("felicidades recuperaste tu moneda");
    moneda += 1;
    System.out.println("Monedas actuales: " + moneda);
} else {
    System.out.println("lo siento has perdido");
    System.out.println("Monedas actuales: " + moneda);
}


}
}