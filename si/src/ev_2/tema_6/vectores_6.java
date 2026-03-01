package tema_6;
import tema_5.empleado;
public class vectores_6 {
public static void main(String[] args) {
    
empleado[] listaEmpleados = new empleado[50];
    String[] nombres = {
    "Sofía", "Santiago", "Valentina", "Mateo", "Isabella", 
    "Sebastián", "Camila", "Leonardo", "Valeria", "Matías", 
};

for ( int i = 0; i < listaEmpleados.length;i++){
    int nombresAleatorios = (int) (Math.random()*nombres.length);
    listaEmpleados[i] = new empleado(i, nombres[nombresAleatorios]);
}

for ( int i = 0; i< listaEmpleados.length ; i++){
    System.out.println("El empleado con numeroEmpleado : "+ (i + 1) + " Se llama : "+ listaEmpleados[i].getnombre() );
}

}

}
