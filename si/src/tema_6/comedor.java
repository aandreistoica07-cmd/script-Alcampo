package tema_6;
public class comedor {

    private final static int MAX_MENUS = 100; // máximo de menús por día
    private int menusVendidos = 0;

    // Carta de 6 platos
    Plato[] carta = {
        new Plato("Croquetas de Jamón", 12, "Jamón ibérico, leche, harina"),
        new Plato("Burrata con Tomate", 14, "Burrata fresca, tomate rosa, pesto"),
        new Plato("Salmón a la Brasa", 21, "Salmón, espárragos y naranja"),
        new Plato("Entrecot de Ternera", 24, "Ternera madurada, patatas y pimientos"),
        new Plato("Tarta de Queso", 8, "Queso crema, huevos y galleta"),
        new Plato("Brownie de Chocolate", 7, "Chocolate 70%, nueces y helado")
    };

    // Mostrar carta
    public void mostrarCarta() {
        System.out.println("=== Carta del Restaurante ===");
        for (int i = 0; i < carta.length; i++) {
            System.out.println((i + 1) + ") " + carta[i].getNombre() + " - " +
                               carta[i].getPrecio() + "€ (Ingredientes: " +
                               carta[i].getIngredientes() + ")");
        }
        System.out.println();
    }

    // Crear un menú para un cliente
    public void crearMenu(int indice1, int indice2, int indicePostre, float dineroPagado) {
        if (menusVendidos >= MAX_MENUS) {
            System.out.println("Lo siento, no quedan menús disponibles.");
            return;
        }

        Plato plato1 = carta[indice1];
        Plato plato2 = carta[indice2];
        Plato postre = carta[indicePostre];

        int totalMenu = plato1.getPrecio() + plato2.getPrecio();
        float cambio = dineroPagado - totalMenu;

        System.out.println("=== Menú del Cliente ===");
        System.out.println(plato1.getNombre() + " - " + plato1.getPrecio() + "€");
        System.out.println(plato2.getNombre() + " - " + plato2.getPrecio() + "€");
        System.out.println("Postre gratis: " + postre.getNombre());
        System.out.println("Precio de cada plato: " + plato1.getPrecio() + ", " + plato2.getPrecio());
        System.out.println("Total a pagar: " + totalMenu + "€");
        System.out.println("Dinero entregado: " + dineroPagado + "€");
        if (dineroPagado >= totalMenu) {
            System.out.println("Cambio: " + cambio + "€");
        } else {
            System.out.println("Dinero insuficiente, falta: " + (-cambio) + "€");
        }
        System.out.println("-------------------------\n");

        menusVendidos++;
    }

    // Clase interna Plato
    class Plato {
        private String nombre;
        private int precio;
        private String ingredientes;

        public Plato(String nombre, int precio, String ingredientes) {
            this.nombre = nombre;
            this.precio = precio;
            this.ingredientes = ingredientes;
        }

        public String getNombre() { return nombre; }
        public int getPrecio() { return precio; }
        public String getIngredientes() { return ingredientes; }
    }

    // Método main de prueba
    public static void main(String[] args) {
       comedor c = new comedor();
        c.mostrarCarta();

        // Ejemplo: 2 clientes
        c.crearMenu(0, 2, 4, 40); // Cliente 1: Croquetas + Salmón + Tarta, paga 40€
        c.crearMenu(1, 3, 5, 50); // Cliente 2: Burrata + Entrecot + Brownie, paga 50€
        
    }
}
