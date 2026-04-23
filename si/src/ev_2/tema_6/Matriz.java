package tema_6;
public class Matriz {
    int filas;
    int columnas;
    private double[][] matriz;

    public Matriz(int filas, int columnas) {
        this.filas = filas;
        this.columnas = columnas;
        this.matriz = new double[filas][columnas];
    }

    public int getFilas() {
        return this.filas;
    }

    public int getColumnas() {
        return this.columnas;
    }

  public void imprimirMatriz() {
    for (int i = 0; i < this.filas; i++) {
        // 1. Abrimos el gran paréntesis de la fila
        System.out.print("( "); 
        
        for (int j = 0; j < this.columnas; j++) {
            // 2. Imprimimos cada casilla individual con corchetes
            // El %6.2f mantiene todo alineado como un reloj
            System.out.printf("[ %6.2f ] ", this.matriz[i][j]);
        }
        
        // 3. Cerramos el gran paréntesis y saltamos de línea
        System.out.println(")"); 
    }
    System.out.println(); // Espacio extra al final
}



    public double devolverCelda(int fila, int columna) {

        if (fila >= 0 && fila < filas && columna >= 0 && columna < columnas) {
            return this.matriz[fila][columna];
        } else {
            System.out.println("out of bounds");
            return -1.0;
        }
    }

    public void asignarCelda(int fila, int columna, double valor) {

        if (fila >= 0 && fila < filas && columna >= 0 && columna < columnas) {
            this.matriz[fila][columna] = valor;
        } else {
            System.out.println("fuera de rango");
        }
    }

    public Matriz sumarMatriz(Matriz otra) {
        if (this.filas == otra.getFilas() && this.columnas == otra.getColumnas()) {

            Matriz resultado = new Matriz(this.filas, this.columnas);

            for (int i = 0; i < this.filas; i++) {
                for (int j = 0; j < this.columnas; j++) {
                    double suma = this.matriz[i][j] + otra.devolverCelda(i, j);
                    resultado.asignarCelda(i, j, suma);
                }
            }
            resultado.imprimirMatriz();
            return resultado;
        } else {
            return null;
        }
    }

    public Matriz restarMatriz(Matriz otra) {
        if (this.filas == otra.getFilas() && this.columnas == otra.getColumnas()) {

            Matriz resultado = new Matriz(this.filas, this.columnas);

            for (int i = 0; i < this.filas; i++) {
                for (int j = 0; j < this.columnas; j++) {
                    double resta = this.matriz[i][j] - otra.devolverCelda(i, j);
                    resultado.asignarCelda(i, j, resta);
                }
            }
            resultado.imprimirMatriz();
            return resultado;
        } else {
            return null;
        }
    }

    public Matriz multipMatriz(Matriz otra) {
        if (this.columnas != otra.getFilas()) {
            return null;
        }
         Matriz resultado = new Matriz(this.filas, otra.getColumnas());

         for ( int i = 0; i < this.filas; i++){
            for ( int j = 0; j < otra.getColumnas();j++){
                double bolsaDeSuma = 0; // acumulacion de todos los valores de cada celda //
                for ( int k = 0 ; k < columnas; k++){ // tercer bucle para pasar por cada valor de filas y columnas e ir sumando //
                   double multiplicacion = this.matriz[i][k] * otra.devolverCelda(k, j); 

                    bolsaDeSuma+= multiplicacion; 
                }
                resultado.asignarCelda(i, j, bolsaDeSuma);
            }
          
         }
         resultado.imprimirMatriz();
          return resultado;
    }

  public static void main(String[] args) {

    
}
}