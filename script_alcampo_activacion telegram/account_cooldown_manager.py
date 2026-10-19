import os
import json
import threading
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

class AccountCooldownManager:
    """
    Gestor de Estado y Cooldown para Cuentas Alcampo.
    
    Reglas de negocio:
    1. Si una cuenta falla 5 días consecutivos (credenciales incorrectas, bloqueos, timeouts),
       se descarta temporalmente y entra en período de reposo (cooldown) de 5 días.
    2. Durante esos 5 días de reposo, el script la ignora automáticamente para ahorrar tiempo
       y evitar bloqueos innecesarios en la IP.
    3. Una vez transcurridos los 5 días de reposo, el script la vuelve a probar automáticamente.
    4. Si tras el reposo vuelve a funcionar, el contador de fallos se resetea a 0 y pasa a activa.
    5. Si vuelve a fallar tras el reposo, vuelve a entrar en reposo por otros 5 días.
    """

    def __init__(self, status_file_path=None):
        self.lock = threading.Lock()
        if status_file_path:
            self.status_file = Path(status_file_path)
        else:
            self.status_file = Path(__file__).resolve().parent / "account_status.json"
        
        self.docs_status_file = self.status_file.parent.parent / "docs" / "account_status.json"
        self.data = self._load()

    def _get_today_str(self):
        """Retorna la fecha actual en formato YYYY-MM-DD (UTC)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self):
        if self.status_file.exists():
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, dict) and "accounts" in content:
                        return content
                    elif isinstance(content, dict):
                        return {"accounts": content, "metrics": {}}
            except Exception as e:
                print(f"⚠️ [CooldownManager] Error leyendo {self.status_file}: {e}. Iniciando base limpia.")
        return {"accounts": {}, "metrics": {}}

    def save(self):
        """Guarda atómicamente el estado en disco y actualiza docs/ si existe."""
        with self.lock:
            # Calcular métricas globales
            total = len(self.data["accounts"])
            today = self._get_today_str()
            cooling_down = 0
            active = 0
            
            for acc in self.data["accounts"].values():
                status = acc.get("status", "active")
                cooldown_until = acc.get("cooldown_until")
                if status == "cooling_down" and cooldown_until and cooldown_until > today:
                    cooling_down += 1
                else:
                    active += 1

            self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self.data["metrics"] = {
                "total_tracked": total,
                "active_count": active,
                "cooling_down_count": cooling_down
            }

            try:
                # Guardar en archivo principal
                self.status_file.parent.mkdir(parents=True, exist_ok=True)
                tmp_file = self.status_file.with_suffix(".tmp")
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                tmp_file.replace(self.status_file)
            except Exception as e:
                print(f"❌ [CooldownManager] Error guardando {self.status_file}: {e}")

            # Guardar también en docs/ si la carpeta existe para el Dashboard
            try:
                if self.docs_status_file.parent.exists():
                    tmp_docs = self.docs_status_file.with_suffix(".tmp")
                    with open(tmp_docs, "w", encoding="utf-8") as f:
                        json.dump(self.data, f, ensure_ascii=False, indent=2)
                    tmp_docs.replace(self.docs_status_file)
            except Exception as e:
                pass

    def unpause_all_cooldowns(self):
        """
        Quita todas las cuentas de la lista de espera / cooldown de 5 días
        y las vuelve a activar para ser probadas inmediatamente,
        reseteando sus fallos consecutivos a 0.
        """
        with self.lock:
            unpaused = 0
            for email, rec in self.data.get("accounts", {}).items():
                if rec.get("status") == "cooling_down" or rec.get("cooldown_until"):
                    rec["status"] = "active"
                    rec["cooldown_until"] = None
                    rec["consecutive_failures"] = 0
                    unpaused += 1
            self.save()
            return unpaused

    def filter_accounts_for_run(self, accounts, today_str=None, ignore_cooldown=False):
        """
        Filtra la lista de cuentas para la ejecución de hoy.
        Retorna:
          (eligible_accounts, skipped_accounts, retest_accounts)
        """
        if ignore_cooldown or os.environ.get("IGNORE_COOLDOWN", "").lower() in ("true", "1", "yes"):
            return list(accounts), [], []
        """
        Filtra la lista de cuentas para la ejecución de hoy.
        Retorna:
          (eligible_accounts, skipped_accounts, retest_accounts)
        """
        if not today_str:
            today_str = self._get_today_str()

        eligible = []
        skipped = []
        retesting = []

        with self.lock:
            for acc in accounts:
                email = acc.get("email", "").strip()
                if not email:
                    continue

                record = self.data["accounts"].get(email)
                if not record:
                    # Cuenta nueva no registrada aún
                    eligible.append(acc)
                    continue

                status = record.get("status", "active")
                cooldown_until = record.get("cooldown_until")

                if status == "cooling_down" and cooldown_until:
                    if today_str < cooldown_until:
                        # En cooldown activo: descartar para la ejecución de hoy
                        skipped.append({
                            "email": email,
                            "cooldown_until": cooldown_until,
                            "failures": record.get("consecutive_failures", 5)
                        })
                    else:
                        # Los 5 días de cooldown han vencido: se vuelve a probar hoy
                        retesting.append({
                            "email": email,
                            "last_tested": record.get("last_checked_date")
                        })
                        eligible.append(acc)
                else:
                    # Cuenta activa normal
                    eligible.append(acc)

        return eligible, skipped, retesting

    def record_result(self, email, is_success, error_msg=None, today_str=None):
        """
        Registra el resultado de la comprobación de una cuenta y aplica las reglas de cooldown.
        Retorna un diccionario con la acción realizada.
        """
        if not today_str:
            today_str = self._get_today_str()

        email = email.strip()
        with self.lock:
            if email not in self.data["accounts"]:
                self.data["accounts"][email] = {
                    "consecutive_failures": 0,
                    "consecutive_successes": 0,
                    "last_checked_date": None,
                    "last_status": None,
                    "last_error": None,
                    "status": "active",
                    "cooldown_until": None,
                    "cooldown_history_count": 0,
                    "total_checks": 0,
                    "total_success": 0,
                    "total_failures": 0
                }

            rec = self.data["accounts"][email]
            rec["total_checks"] = rec.get("total_checks", 0) + 1
            prev_status = rec.get("status", "active")
            prev_failures = rec.get("consecutive_failures", 0)
            last_date = rec.get("last_checked_date")

            if is_success:
                rec["consecutive_failures"] = 0
                rec["consecutive_successes"] = rec.get("consecutive_successes", 0) + 1
                rec["status"] = "active"
                rec["cooldown_until"] = None
                rec["last_status"] = "success"
                rec["last_error"] = None
                rec["last_checked_date"] = today_str
                rec["total_success"] = rec.get("total_success", 0) + 1

                was_in_cooldown = (prev_status == "cooling_down")
                return {
                    "email": email,
                    "action": "recovered" if was_in_cooldown else "success",
                    "consecutive_failures": 0,
                    "status": "active"
                }
            else:
                # Solo incrementar días consecutivos de fallo si no se falló ya en el mismo día
                if last_date != today_str:
                    rec["consecutive_failures"] = prev_failures + 1
                rec["consecutive_successes"] = 0
                rec["last_status"] = "error"
                rec["last_error"] = str(error_msg or "Error desconocido")
                rec["last_checked_date"] = today_str
                rec["total_failures"] = rec.get("total_failures", 0) + 1

                # Comprobar umbral de 5 días seguidos de fallo
                if rec["consecutive_failures"] >= 5:
                    today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
                    cooldown_until_dt = today_dt + timedelta(days=5)
                    cooldown_until_str = cooldown_until_dt.strftime("%Y-%m-%d")

                    rec["status"] = "cooling_down"
                    rec["cooldown_until"] = cooldown_until_str
                    rec["cooldown_history_count"] = rec.get("cooldown_history_count", 0) + 1

                    return {
                        "email": email,
                        "action": "entered_cooldown",
                        "consecutive_failures": rec["consecutive_failures"],
                        "cooldown_until": cooldown_until_str,
                        "status": "cooling_down"
                    }
                else:
                    return {
                        "email": email,
                        "action": "failure_recorded",
                        "consecutive_failures": rec["consecutive_failures"],
                        "status": "active"
                    }

    def get_account_status(self, email):
        """Retorna el registro de una cuenta específica."""
        with self.lock:
            return self.data["accounts"].get(email.strip(), None)
