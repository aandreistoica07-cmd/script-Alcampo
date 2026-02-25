package tema_5_POO;

public class trabajador {
    private int numeroIdentificativo;
    private String nombre;
    private String estadoCivil;
    private String turno;
    private int titulacion;
    private int añosEmpresa;

    public trabajador(int numeroIdentificativo, String nombre, String estadoCivil, String turno, int titulacion,
            int añosEmpresa) {
        this.numeroIdentificativo = numeroIdentificativo;
        this.nombre = nombre;
        this.estadoCivil = estadoCivil;
        this.turno = turno;
        this.titulacion = titulacion;
        this.añosEmpresa = añosEmpresa;
    }

    public int getnumeroidentificativo() {
        return numeroIdentificativo;
    }
    public void seleccionarnumeroidentificativo() {
        if (numeroIdentificativo >= 1 && numeroIdentificativo <= 100) {
            this.numeroIdentificativo = numeroIdentificativo;
        } else {
            System.err.println("ERROR EL NUMERO DE EMPLEADO SOLO VA DEL 1 AL 100");
        }
    }

    public String getEstadoCivil() {
        return estadoCivil;
    }

    public void SetEstadoCivil(String estadoCivil) {
        this.estadoCivil = estadoCivil;
    }

    public void seleccionarEstadoCivil() {
        if (estadoCivil.equals("C")) {
            estadoCivil = "C";
        } else if (estadoCivil.equals("S")) {
            estadoCivil = "S";
        } else {
            System.err.println("ERROR EN EL SELECTOR DE ESTADO CIVIL TIENE QUE SER C O S (MAYUSCULAS)");
        }
    }

    public String getTurno() {
        return turno;
    }

    public void setTurno(String turno) {
        this.turno = turno;
    }

    public void seleccionarTurno() {
        if (turno.equals("D")) {
            turno = "D";
        } else if (turno.equals("N")) {
            turno = "N";
        } else {
            System.err.println("ERROR EN EL SELECTOR DE TURNO TIENE QUE SER D O N ( MAYUSCULAS) ");
        }
    }

    public int getTitulacion() {
        return titulacion;
    }

    public void setTitulacion(int titulacion) {
        this.titulacion = titulacion;
    }

    public void seleccionarTitulacion() {
        if (titulacion < 0 || titulacion > 4) {
            System.err.println("TITULACION INVALIDA");
        }
    }

    public int getañosEmpresa() {
        return añosEmpresa;

    }

    public void setAñosEmpresa(int añosEmpresa) {
        this.añosEmpresa = añosEmpresa;
    }

    public void seleccionarAñosEmpresa() {
        if (añosEmpresa < 0) {
            System.err.println("no pueden haber años negativo");
        }
    }

    public String getNombre() {
        return nombre;
    }

    public void setNombre(String nombre) { // como no hay condiciones no hace falta crear un metodo seleccionarNombre//
        this.nombre = nombre;
    }

    public void verDatos() {
        System.out.println(
                nombre + " : " + numeroIdentificativo + " : " + estadoCivil + " : " + turno + " : " + titulacion
                        + " : " + añosEmpresa);
    }

    public void verificarDatos() {
        seleccionarTurno();
        seleccionarAñosEmpresa();
        seleccionarEstadoCivil();
        seleccionarTitulacion();
        seleccionarnumeroidentificativo();

    }

    public static void main(String[] args) {
        trabajador juan = new trabajador(44, "juan", "C", "D", 4, 10);
       
       trabajador maria = new trabajador(99, "maria", "S", "D", 2, 3);
       maria.calcularNomina();
        
    }

    public double calcularNomina(){
        double salarioBase = 425;

        if (this.turno.equals("N")){
            salarioBase += 100;

        }else if (this.turno.equals("D")){
            salarioBase +=0;
        }else{
            System.out.println("No hay un valor valido en el dato TURNO del trabajador");
            return 0;
        }

        for( int i = 1; i<= this.añosEmpresa;i++){
            salarioBase+=75;
        }

        if (this.titulacion == 0){
            salarioBase += 250;
        }else if (this.titulacion == 1){
            salarioBase+= 500;
        }else if (this.titulacion == 2){
            salarioBase += 1000 ;
        }else if (this.titulacion == 3){
            salarioBase += 1250; 
        }else if (this.titulacion == 4){
            salarioBase += 1500;
        }else{
            System.out.println("No hay un valor valido en el dato TITULACION del trabajador");
            return 0;
        }

        if ( this.estadoCivil.equals("C")){
            salarioBase*=0.9;
        }else if (this.estadoCivil.equals("S")){
            salarioBase*=0.88;
        }else{
            System.out.println("No hay un valor valido en el dato ESTADO CIVIL del trabajador");
            return 0;
        }
        System.out.println("El salario final del trabajador: "+ this.nombre + " es : "+salarioBase);
        return salarioBase;
        
    }
}
