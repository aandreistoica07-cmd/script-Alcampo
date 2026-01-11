/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
import java.util.Scanner;
/**
 *
 * @author alvarezherrera25
 */
public class Ejemplo {
        public static void main(String[] args){
            Scanner teclado=new Scanner(System.in);
            int num1,num2,suma,producto;
            
            System.out.print("Ingrese primer valor:");
            num1=teclado.nextInt();
            System.out.print("Ingrese segundo valor:");
            num2=teclado.nextInt();
            suma=num1 + num2;
            producto=num1 * num2;
            System.out.print("La suma de los dos valores es:");
            System.out.print(suma);
            System.out.print("El producto de los valores es:");
            System.out.print(producto);
        }
}