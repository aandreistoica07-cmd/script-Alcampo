package tema_8;

public class copia_disco {
    String titulo;
    int n_canciones;
    double precio;
    String fecha_Compra;

    public String gettitulo() {
        return titulo;
    }

    public int getn_canciones() {
        return n_canciones;
    }

    public double getprecio() {
        return precio;
    }

    public String getfecha_compra() {
        return fecha_Compra;
    }

    public void settitulo(String titulo) {
        if (titulo == null || titulo.trim().isEmpty()) {
            throw new IllegalArgumentException("error, el titulo no puede estar vacio");
        }
        this.titulo = titulo;
    }

    public void setn_canciones(int n_canciones) {
        if (n_canciones <= 0) {
            throw new IllegalArgumentException("Error: El número de canciones debe ser mayor que 0.");
        }
        this.n_canciones = n_canciones;
    }

    public void setprecio(double precio) {
        if (precio < 0) {
            throw new IllegalArgumentException("error el precio no puede ser menor a 0");
        }
        this.precio = precio;

    }

    public void setfecha_compra(String fecha_Compra) {
        if (fecha_Compra == null || fecha_Compra.trim().isEmpty()) {
            throw new IllegalArgumentException("error en la fecha, no puede estar vacia");
        }
        this.fecha_Compra = fecha_Compra;
    }

    public copia_disco(String titulo, int n_canciones, double precio, String fecha_Compra) {
        settitulo(titulo);
        setn_canciones(n_canciones);
        setprecio(precio);
        setfecha_compra(fecha_Compra);
    }

    public static void main(String[] args) {

        try {
            copia_disco miDisco = new copia_disco("thriller", 20, 40, "24/09/1998");
            System.out.println("¡Disco registrado con éxito!\n");

            System.out.println("Título: " + miDisco.gettitulo());
            System.out.println("Canciones: " + miDisco.getn_canciones());
            System.out.println("Precio: " + miDisco.getprecio());
            System.out.println("Fecha de compra: " + miDisco.getfecha_compra());

        } catch (IllegalArgumentException e) {
            System.out.println("No se ha podido guardar el disco.");
            System.out.println("Motivo: " + e.getMessage());
        }

        System.out.println("fin");
    }
}
