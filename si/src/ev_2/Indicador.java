import java.util.Scanner;

public class Indicador {
    private float valorInicial;
    private float nuevoValor;
    private float valorActual;
    private float incremento;
    private float decremento;

    public Indicador(float valorInicial, float valorActual) {
        this.valorInicial = valorInicial;
        this.valorActual = valorActual;
    }

    public float getvalorInicial() {
        return valorInicial;
    }

    public void setvalorInicial(float valorInicial) {
        this.valorInicial = valorInicial;
    }

    public float getvalorActual() {
        return valorActual;
    }

    public void setvalorActual(float valorActual) {
        this.valorActual = valorActual;
    }

    public void incrementarValor() {
        Scanner teclado = new Scanner(System.in);
        System.out.println("Selecciona el incremento");
        incremento = teclado.nextFloat();
        this.valorActual += incremento;
        System.out.println("valores: " + this.valorInicial + "--> " + this.valorActual);
    }

    public void disminuirValor() {
        Scanner teclado = new Scanner(System.in);
        System.out.println("Selecciona el decremento");
        decremento = teclado.nextFloat();
        this.valorActual -= decremento;
        System.out.println("valores: " + this.valorInicial + "--> " + this.valorActual);
    }

    public void imprimirDatos() {
        System.out.println("valores: " + this.valorInicial + "--> " + this.valorActual);
       
    }

    public static void main(String[] args) {

        Indicador velocimetro = new Indicador(0, 0);
        velocimetro.incrementarValor();
        velocimetro.imprimirDatos();


    }

}
