/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package si;

import java.util.Scanner;
/**
 * @author alvarezherrera25
 * Imprime el deporte apropiado para practicarlo a la temperatura introducida por el usuario.
 * Fecha: 29092025
 */
public class ProgDeporte {
    public static void main(String[] args){
            Scanner teclado=new Scanner(System.in);
            int temp;
            String deporteRecomendado;
            
            System.out.print("Ingrese la temperatura actual en grados Celsius: ");
        temp = teclado.nextInt();

        if (temp > 29){
        deporteRecomendado = ("Tira a nadar");
        }    
        
        else if (temp > 21){
        deporteRecomendado = ("Un partiditio de tenis");
        }    
        
        else if (temp > 0){
        deporteRecomendado = ("Un golf");    
        }    
        
        else if (temp > -12){
        deporteRecomendado = ("A la montaña a esquiar");  
        }    
        
        else{ 
        deporteRecomendado = "A casa a juar al 1";
        }
        
        System.out.println("Temperatura ingresada: " + temp + "°C");
        System.out.println("Deporte apropiado: " + deporteRecomendado);
    
    }
}

