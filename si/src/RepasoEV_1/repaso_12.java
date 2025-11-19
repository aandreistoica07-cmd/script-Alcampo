package RepasoEV_1;
import java.util.Scanner;
public class repaso_12 {
public static void main(String[] args) {
Scanner teclado = new Scanner (System.in);
String jugador1;
String jugador2;
System.err.println("PIEDRA PAPEL O TIJERA");
System.out.println("jugador 1");
jugador1 = teclado.nextLine();

System.out.println("jugador 2");
jugador2 = teclado.nextLine();

if (jugador1.equals(jugador2)){
    System.out.println("empate");
} else if ( jugador1.equalsIgnoreCase("piedra")  && jugador2 == "papel "){

}
    }
}
