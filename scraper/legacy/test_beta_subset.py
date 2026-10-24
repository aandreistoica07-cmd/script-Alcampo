import time
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import logic from the modified script
from ultima_version_beta import procesar_cuenta, CHROME_DRIVER_PATH

# Test accounts from the database
TEST_ACCOUNTS = [
  {"email": "nflmadrid2004@yahoo.es", "password": "Cibona69"},
  {"email": "mcristina.cabrera@hotmail.com", "password": "Cristina240660"},
  {"email": "perdiguero54@yahoo.es", "password": "Dios1954"}
]

print("Starting subset verification test on 3 accounts...")
print(f"Using ChromeDriver path: {CHROME_DRIVER_PATH}")

start_time = time.time()
resultados = []

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(procesar_cuenta, acc["email"], acc["password"], i + 1): acc 
        for i, acc in enumerate(TEST_ACCOUNTS)
    }
    for future in as_completed(futures):
        res = future.result()
        resultados.append(res)
        print(f"Result for {res['email']}: {res['saldo']}")

end_time = time.time()
print(f"\nTest finished in {end_time - start_time:.2f} seconds.")
print("Results:")
for r in resultados:
    print(r)
