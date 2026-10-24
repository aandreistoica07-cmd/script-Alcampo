"""
Unit tests for CircuitBreaker: error classification taxonomy and trip logic.
Zero external Chrome or network dependencies.
"""

import pytest
from scraper.script_optimizado import CircuitBreaker


class TestCircuitBreakerClassification:
    """Test suite for classify_error distinguishing between all 4 error domains."""

    @pytest.fixture
    def cb(self):
        return CircuitBreaker(max_consecutive_failures=5, max_failure_ratio=0.50, min_processed_threshold=10)

    def test_classify_account_error(self, cb):
        category, reason = cb.classify_error(page_source="Usuario o contraseña incorrectos.")
        assert category == "account_error"
        assert "credenciales" in reason.lower()

        category, reason = cb.classify_error(page_source="Contraseña no válida.")
        assert category == "account_error"

        category, reason = cb.classify_error(error_msg="Error: credenciales no redirigidas")
        assert category == "account_error"

    def test_classify_session_error(self, cb):
        category, reason = cb.classify_error(error_msg="session_error: timeout esperando redirección")
        assert category == "session_error"
        assert "sesión" in reason.lower() or "session" in reason.lower()

        category, reason = cb.classify_error(page_source="Tu sesión ha expirado por inactividad.")
        assert category == "session_error"

        category, reason = cb.classify_error(error_msg="redirección demorada en home")
        assert category == "session_error"

        category, reason = cb.classify_error(error_msg="Error: Saldo no hidratado en DOM")
        assert category == "session_error"

        category, reason = cb.classify_error(error_msg="authenticationerror")
        assert category == "session_error"

        category, reason = cb.classify_error(page_source="DOM no hidratado")
        assert category == "session_error"

    def test_classify_needs_attention_call_center_and_password_reset(self, cb):
        category, reason = cb.classify_error(page_source="Tu cuenta ha sido bloqueada. Contacte con Call Center.")
        assert category == "needs_attention"
        assert "bloqueada" in reason.lower()

        category, reason = cb.classify_error(page_source='<button id="btnPwReset">Restablecer contraseña</button>')
        assert category == "needs_attention"

    def test_classify_needs_attention_2fa_and_otp(self, cb):
        category, reason = cb.classify_error(page_source="Introduce el código de verificación enviado a tu email.")
        assert category == "needs_attention"
        assert "2fa" in reason.lower() or "verificación" in reason.lower() or "email" in reason.lower()

        category, reason = cb.classify_error(page_source="Device activation required. Identity verification needed.")
        assert category == "needs_attention"

    def test_classify_ip_error_http_status_codes(self, cb):
        category, reason = cb.classify_error(status_code=429)
        assert category == "ip_error"
        assert "429" in reason

        category, reason = cb.classify_error(status_code=403)
        assert category == "ip_error"

        category, reason = cb.classify_error(status_code=502)
        assert category == "ip_error"

        category, reason = cb.classify_error(status_code=524)
        assert category == "ip_error"

    def test_classify_ip_error_cloudflare_and_waf(self, cb):
        category, reason = cb.classify_error(page_source="Attention Required! Cloudflare Ray ID: 88712abc")
        assert category == "ip_error"

        category, reason = cb.classify_error(page_source="Please solve this captcha challenge-platform")
        assert category == "ip_error"

        category, reason = cb.classify_error(page_source="429 Too Many Requests - Access forbidden")
        assert category == "ip_error"

    def test_classify_ip_error_network_connection(self, cb):
        category, reason = cb.classify_error(error_msg="net::ERR_CONNECTION_TIMED_OUT")
        assert category == "ip_error"

        category, reason = cb.classify_error(error_msg="Timeout esperando #uname1")
        assert category == "ip_error"

        category, reason = cb.classify_error(error_msg="connection refused by remote host")
        assert category == "ip_error"

        category, reason = cb.classify_error(error_msg="connection refusal detected")
        assert category == "ip_error"

        category, reason = cb.classify_error(error_msg="DNS lookup failed for compraonline.alcampo.es")
        assert category == "ip_error"


class TestCircuitBreakerStateAndTripLogic:
    """Test suite for consecutive failure counts and tripping thresholds."""

    def test_consecutive_failure_threshold(self):
        cb = CircuitBreaker(max_consecutive_failures=3, min_processed_threshold=10)
        assert cb.triggered is False

        # 2 server errors: not yet triggered
        cb.record_result(is_server_error=True, reason="HTTP 429", error_type="ip_error")
        cb.record_result(is_server_error=True, reason="HTTP 429", error_type="ip_error")
        assert cb.triggered is False

        # 3rd consecutive server error: should trip
        triggered, reason = cb.record_result(is_server_error=True, reason="HTTP 429", error_type="ip_error")
        assert triggered is True
        assert cb.triggered is True
        assert "3 caídas consecutivas" in reason

    def test_success_resets_consecutive_failures(self):
        cb = CircuitBreaker(max_consecutive_failures=3, min_processed_threshold=10)

        cb.record_result(is_server_error=True, reason="HTTP 502", error_type="ip_error")
        cb.record_result(is_server_error=True, reason="HTTP 502", error_type="ip_error")
        assert cb.consecutive_server_errors == 2

        # A successful check or account error resets consecutive_server_errors
        cb.record_result(is_server_error=False, error_type="ok")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    def test_account_errors_do_not_trip_circuit_breaker(self):
        cb = CircuitBreaker(max_consecutive_failures=3, min_processed_threshold=10)

        # 5 consecutive account_errors should NOT trip IP circuit breaker
        for _ in range(5):
            triggered, _ = cb.record_result(is_server_error=False, reason="Credenciales incorrectas", error_type="account_error")
            assert triggered is False

        assert cb.triggered is False
        assert cb.consecutive_server_errors == 0

    def test_session_and_account_errors_reset_consecutive_server_errors(self):
        cb = CircuitBreaker(max_consecutive_failures=3, min_processed_threshold=10)

        # 2 consecutive IP errors
        cb.record_result(is_server_error=True, reason="HTTP 429", error_type="ip_error")
        cb.record_result(is_server_error=True, reason="HTTP 429", error_type="ip_error")
        assert cb.consecutive_server_errors == 2

        # session_error must reset consecutive_server_errors to 0
        cb.record_result(is_server_error=False, reason="Saldo no hidratado", error_type="session_error")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

        # Accumulate again and test account_error reset
        cb.record_result(is_server_error=True, reason="HTTP 502", error_type="ip_error")
        cb.record_result(is_server_error=True, reason="HTTP 502", error_type="ip_error")
        assert cb.consecutive_server_errors == 2

        cb.record_result(is_server_error=False, reason="Credenciales incorrectas", error_type="account_error")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

        # Accumulate again and test needs_attention reset
        cb.record_result(is_server_error=True, reason="Cloudflare", error_type="ip_error")
        assert cb.consecutive_server_errors == 1

        cb.record_result(is_server_error=False, reason="Call Center", error_type="needs_attention")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    def test_only_ip_error_increments_consecutive_server_errors(self):
        cb = CircuitBreaker(max_consecutive_failures=3, min_processed_threshold=10)

        # Non-IP errors do not increment counter
        cb.record_result(is_server_error=False, error_type="account_error")
        assert cb.consecutive_server_errors == 0

        cb.record_result(is_server_error=False, error_type="session_error")
        assert cb.consecutive_server_errors == 0

        cb.record_result(is_server_error=False, error_type="needs_attention")
        assert cb.consecutive_server_errors == 0

        # Only ip_error increments consecutive counter towards threshold
        cb.record_result(is_server_error=True, reason="Cloudflare", error_type="ip_error")
        assert cb.consecutive_server_errors == 1

        cb.record_result(is_server_error=True, reason="WAF Block", error_type="ip_error")
        assert cb.consecutive_server_errors == 2

        triggered, reason = cb.record_result(is_server_error=True, reason="HTTP 429", error_type="ip_error")
        assert cb.consecutive_server_errors == 3
        assert triggered is True
        assert cb.triggered is True

