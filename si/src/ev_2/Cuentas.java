import tema_5.CuentaCorriente;

public class Cuentas {
    private CuentaCorriente[] listaCuentas = new CuentaCorriente[100];
    private int numCuentas = 0;

    public void añadirCuentas(CuentaCorriente c) {

        if (numCuentas >= 100) {
            System.out.println("Lista llena. No se puede agregar más cuentas.");
            return;
        }

        for (int i = 0; i < numCuentas; i++) {
            if (listaCuentas[i].getCodigo().equals(c.getCodigo())) {
                System.out.println("Código de cuenta repetido. No se puede agregar.");
                return;
            }
        }
        listaCuentas[numCuentas] = c;
        numCuentas++;
        System.out.println("Cuenta agregada correctamente.");
    }

    public CuentaCorriente cuentaMayor() {
        CuentaCorriente cuentaMayor = null;
        for (int i = 0; i < numCuentas; i++) {
            CuentaCorriente cuentaActual = listaCuentas[i];
            if (cuentaMayor == null || cuentaActual.getSaldo() > cuentaMayor.getSaldo()) {
                cuentaMayor = cuentaActual;
            }
        }
        return cuentaMayor;
    }

    public void imprimirMayores() {
        CuentaCorriente mayor = cuentaMayor();
        if (mayor == null) {
            System.out.println("No hay cuentas disponibles");
            return;
        }

        float saldoMaximo = mayor.getSaldo();
        System.out.println("Cuentas con el saldo máximo (" + saldoMaximo + "):");
        System.out.println("---------------------------------------");

        for (int i = 0; i < numCuentas; i++) {
            if (listaCuentas[i].getSaldo() == saldoMaximo) {
                System.out.println("Titular: " + listaCuentas[i].getTitular());
                System.out.println("Código: " + listaCuentas[i].getCodigo());
                System.out.println("---------------------------------------");
            }
        }

    }

    public static void main(String[] args) {
        Cuentas cuentas = new Cuentas();
        CuentaCorriente c1 = new CuentaCorriente("Paco", 500, "36464342");
        CuentaCorriente c2 = new CuentaCorriente("Maria", 3454, "12345678");
        CuentaCorriente c3 = new CuentaCorriente("Luis", 3454, "87654321"); // mismo saldo que Maria
        CuentaCorriente c4 = new CuentaCorriente("Ana", 1200, "23456789");
        CuentaCorriente c5 = new CuentaCorriente("Jorge", 800, "34567890");

        cuentas.añadirCuentas(c1);
        cuentas.añadirCuentas(c2);
        cuentas.añadirCuentas(c3);
        cuentas.añadirCuentas(c4);
        cuentas.añadirCuentas(c5);

        cuentas.imprimirMayores();

    }

}
