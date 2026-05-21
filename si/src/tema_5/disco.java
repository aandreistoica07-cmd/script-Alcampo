package tema_5;
public class disco {
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
        this.titulo = titulo;
    }

    public void setn_canciones(int n_canciones) {
        this.n_canciones = n_canciones;

    }

    public void setprecio(int precio) {
        this.precio = precio;
    }

    public void setfecha_compra(String fecha_Compra) {
        this.fecha_Compra = fecha_Compra;
    }

    public disco(String titulo, int n_canciones,double precio,String fecha_Compra){
        this.titulo = titulo;
        this.n_canciones = n_canciones;
        this.precio = precio;
        this.fecha_Compra = fecha_Compra;
    }

    public static void main(String[] args) {
        disco miDisco = new disco("thriller", 5, 40, "24/09/1998");
         System.out.println("Título: " + miDisco.gettitulo());
         System.out.println("Canciones: " + miDisco.getn_canciones());
         System.out.println("Precio: " + miDisco.getprecio());
        System.out.println("Fecha de compra: " + miDisco.getfecha_compra());
    

    }
}
