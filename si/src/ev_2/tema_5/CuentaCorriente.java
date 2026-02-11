package tema_5;
import java.util.Scanner;

public class CuentaCorriente {
    private String titular;
    private float saldo;
    private String codigo;
    private boolean saldoSuficiente;
    private float dineroIngresar;
    private float dineroSacar;

    public CuentaCorriente(String titular, float saldo, String codigo) {
        this.titular = titular;
        this.saldo = saldo;
        this.codigo = codigo;
    }

    public void verificarCodigo() {
        boolean soloNumeros = true;
        if (this.codigo.length() != 8) {
            soloNumeros = false;
            System.out.println("tiene que ser de 8 digitos");
        } else {
            for (int i = 0; i < codigo.length(); i++) {
                char c = codigo.charAt(i);
                if (c < '0' || c > '9') {
                    soloNumeros = false;
                } else {
                    soloNumeros = true;
                }
            }
            if (soloNumeros == true) {
                System.out.println("codigo correcto");
            } else {
                System.out.println("codigo incorrecto");
            }
        }

    }

    public void puedoSacar() {
        Scanner teclado = new Scanner(System.in);
        System.out.println("Cuanto dinero quieres sacar");
        dineroSacar = teclado.nextFloat();
        if (saldo > 0 && dineroSacar <= saldo) {
            saldoSuficiente = true;
        } else if (saldo <= 0 || dineroSacar > saldo) {
            saldoSuficiente = false;
        }
        if (saldoSuficiente == true) {
            saldo -= dineroSacar;
            System.out.println("saldo disponible despues de la operacion: " + saldo);
        } else {
            System.out.println("ERROR SALDO INSUFICIENTE");
        }
    }

    public void ingresarDinero() {
        Scanner teclado = new Scanner(System.in);
        System.out.println("Cuanto dinero quieres ingresar");
        dineroIngresar = teclado.nextFloat();
        System.out.println();
        saldo += dineroIngresar;
        System.out.println("Saldo actual despues de la operacion: " + saldo);

    }

    public void operaciones() {
        Scanner teclado = new Scanner(System.in);
        int operacion;
        do {
            System.out.println("Elige la operación a ejecutar:");
            operacion = teclado.nextInt(); 

            if (operacion == 1) {
                puedoSacar();
            } else if (operacion == 2) {
                ingresarDinero();
            } else {
                System.out.println("¡Tiene que ser 1 o 2! Intenta de nuevo.");
            }

        } while (operacion != 1 && operacion != 2);
    }

    public static void main(String[] args) {
        CuentaCorriente c1 = new CuentaCorriente("maria", 3454, "12345678");
        c1.verificarCodigo();
        c1.operaciones();
    }
}
