package examen;

public class Cafetera extends Electrodomestico {
    // Atributo exclusivo de la cafetera
    private int servicios;

    // CONSTRUCTOR
    public Cafetera(int modelo) {
        // 1. Llamamos al constructor del Padre SIEMPRE en la primera línea
        super(modelo); 
        
        // 2. Validamos el límite de modelos (máximo 4 para cafeteras)
        if (this.getModelo() > 4) {
            System.out.println("Error: El modelo de cafetera no puede ser mayor que 4.");
        }
        
        // 3. Inicializamos su atributo exclusivo
        this.servicios = 0; 
    }

    // MÉTODOS DE SERVICIOS (Igual que los días, con sobrecarga)
    public void serviciosHechos(int cantidad) {
        if (cantidad > 0) {
            this.servicios = this.servicios + cantidad;
        }
    }

    public void serviciosHechos() {
        this.serviciosHechos(1); // Si no me dicen cuántos, asumo que ha hecho 1 café
    }

    // MÉTODOS DE MANTENIMIENTO (Obligatorios por la interfaz)
    @Override
    public boolean debeRevisarse() {
        // Se descalcifica cada 200 servicios
        return this.servicios >= 200; 
    }

    @Override
    public void pasarRevision() {
        // Al pasar revisión, el contador de tazas vuelve a cero
        this.servicios = 0; 
    }
}
