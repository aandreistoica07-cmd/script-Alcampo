import re
from pathlib import Path

p = Path("dump_miportal.html")
if not p.exists():
    p = Path(r"c:\Users\Estudiante\Downloads\Proyectos_Alcampo\script-Alcampo\dump_miportal.html")

html = p.read_text(encoding="utf-8")
print("Miportal HTML size:", len(html))

patterns = [r"400\d{10}", r"SALDO DISPONIBLE", r"3,00", r"[\d,.]+\s*€"]
for pat in patterns:
    matches = list(re.finditer(pat, html, re.IGNORECASE))
    print(f"\n--- Patrón: {pat} ({len(matches)} encontrados) ---")
    for m in matches[:5]:
        s = max(0, m.start() - 100)
        e = min(len(html), m.end() + 100)
        print("  MATCH:", html[s:e].replace("\n", " ").strip())
