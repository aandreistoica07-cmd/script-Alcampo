package tema_5_POO;
import java.util.Scanner;

public class Hora {
    private int horas;
    private int minutos;
    private int segundos;

    public Hora(int horas, int minutos, int segundos) {
        this.horas = horas;
        this.minutos = minutos;
        this.segundos = segundos;
    }

    public void seleccionarHora() {
        Scanner teclado = new Scanner(System.in);
        do {
            System.out.println("ingresa las horas");
            this.horas = teclado.nextInt();
        } while (horas > 24);

        do {
            System.out.println("ingresa los minutos");
            this.minutos = teclado.nextInt();
        } while (minutos > 60);

        do {
            System.out.println("ingresa los segundos");
            this.segundos = teclado.nextInt();
        } while (segundos > 60);
    }

    public void imprimirHoras() {
        System.out.println("Horas : " + this.horas + ",Minutos : " + this.minutos + ", Segundos : " + this.segundos);
    }

    public void suma(int horas, int minutos, int segundos) {
        this.segundos += segundos;
        this.minutos += minutos;
        this.horas += horas;

        while (this.segundos >= 60) {
            this.segundos -= 60;
            this.minutos += 1;
        }

        while (this.minutos >= 60) {
            this.minutos -= 60;
            this.horas += 1;
        }

        while (this.horas >= 24) {
            this.horas -= 24;
        }

        imprimirHoras();
    }

    public void resta(int horas, int minutos, int segundos) {
        this.horas -= horas;
        this.minutos -= minutos;
        this.segundos -= segundos;

        while (this.segundos < 0) {
            this.minutos -= 1;
            this.segundos += 60;

        }
        while (this.minutos < 0) {
            this.horas -= 1;
            this.minutos += 60;
        }

        while (this.horas < 0) {
            this.horas += 24;

        }

        imprimirHoras();
    }

    public static void main(String[] args) {
        Hora reloj1 = new Hora(23, 0, 0);
        reloj1.resta(11, 30, 5);

    }
}
