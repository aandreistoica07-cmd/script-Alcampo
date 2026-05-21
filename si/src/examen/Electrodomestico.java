package examen;

public abstract  class Electrodomestico implements Mantenimiento {
    public static final int negro = 0x000000;
    public static final int BLANCO = 0xFFFFFF;

    // 2. ATRIBUTOS
    // 'final' porque el enunciado dice "no podrá ser modificado posteriormente"
    private final int modelo; 
    private int color;
    // 'protected' para que el Horno y el Frigorífico puedan acceder a los días en sus revisiones
    protected int dias;

    public Electrodomestico(int modelo) {
        // Validamos el modelo como pedía el profesor
        if (modelo > 0) {
            this.modelo = modelo;
        } else {
            System.out.println("Error: El modelo debe ser mayor que 0.");
            this.modelo = 1; // Le damos un valor por defecto para que no falle al ser 'final'
        }
        
        // ¡OJO! Inicializamos las demás variables nosotros mismos
        this.color = negro; // Todos salen negros de fábrica
        this.dias = 0;      // Todos salen con 0 días de uso
    }

    public int getModelo() {
        return this.modelo;
    }

    public int getColor() {
        return this.color;
    }

    public void pintar(int color) {
        if (color >= negro && color <= BLANCO) {
            this.color = color;
        } else {
            System.out.println("Error: Color no válido.");
        }
    }

    public void diasTranscurridos(int dias) {
        if (dias > 0) {
            this.dias = this.dias + dias;
        }
    }

    public void diasTranscurridos() {
        this.diasTranscurridos(30); // Llama al método de arriba para no repetir código
    }
   
}
