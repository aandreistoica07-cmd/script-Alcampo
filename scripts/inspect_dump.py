import re

html = open("dump_loyalty.html", encoding="utf-8").read()
print("Length:", len(html))

# Find the context of "Mi cuenta Club Alcampo"
idx = html.find("Mi cuenta Club Alcampo")
while idx != -1:
    print("\n--- OCCURRENCE ---")
    start = max(0, idx - 200)
    end = min(len(html), idx + 200)
    print(html[start:end])
    idx = html.find("Mi cuenta Club Alcampo", idx + 1)

# Find all occurrences of 0,00 or Saldo
for m in re.finditer(r"(saldo|0,00|\b\d+,\d{2}\s*€)", html, re.IGNORECASE):
    s = max(0, m.start() - 50)
    e = min(len(html), m.end() + 50)
    print("\n[SALDO CONTEXT]:", html[s:e].replace("\n", " "))

m = re.search(r'<a[^>]*data-test=["\']loyalty-manage-button["\'][^>]*href=["\']([^"\']*)["\']', html)
print("HREF:", m.group(1) if m else "NOT FOUND")
tag = re.search(r'<a[^>]*data-test=["\']loyalty-manage-button["\'][^>]*>', html)
print("FULL TAG:", tag.group(0) if tag else "NOT FOUND")
