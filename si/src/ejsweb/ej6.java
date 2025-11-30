package ejsweb;
import java.util.Scanner;
public class ej6 {
public static void main(String[] args) {
    Scanner teclado = new Scanner (System.in);
    System.out.println("ingresa x");
    int x = teclado.nextInt();
    for ( int i = 2; i <= x;i++){
       
        while( x%i == 0){
            
            System.out.println(x+ "|" + i+" ");
            x /= i;
        }
       
        
        
    }
    
}

}
