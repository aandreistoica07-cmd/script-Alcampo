package tema_7;

public abstract class abstracta_5 {

    protected void dormir() {
        System.out.println("Zzzzz...");
    }

    protected abstract void HacerSonido();// solo lo pueden usar las clases hijas//

}

class perro extends abstracta_5{
    
}
