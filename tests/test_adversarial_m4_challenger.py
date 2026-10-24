"""
Adversarial stress test suite for M4: Session Hydration and 4-tier error classification.
Zero external Chrome or network dependencies.
"""

import re
import sys
import time
from unittest import mock
import pytest

from scraper.script_optimizado import (
    CircuitBreaker,
    _verify_and_hydrate_session,
    _extract_loyalty_balance,
    extraer_tarjeta,
    limpiar_saldo,
)


# ==============================================================================
# 1. ADVERSARIAL STRESS TESTS: CIRCUIT BREAKER & 4-TIER ERROR CLASSIFICATION
# ==============================================================================

class TestCircuitBreakerAdversarialStress:
    """Stress tests challenging CircuitBreaker assumptions on alternating errors and thresholds."""

    def test_interleaved_non_ip_errors_prevent_trigger_despite_exceeding_total_threshold(self):
        """Feeding alternating sequences of session_error, account_error, and ip_error.
        Even if total errors far exceed the threshold (e.g. 60 total errors),
        the interleaved non-IP errors reset consecutive_server_errors to 0,
        and keep server ratio at 33.3% (< 50% max_failure_ratio), preventing trip."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        sequence = ["session_error", "account_error", "ip_error"]
        total_cycles = 20  # 20 * 3 = 60 total errors

        for i in range(total_cycles):
            for err in sequence:
                is_server = (err == "ip_error")
                reason = "HTTP 429" if is_server else f"Handled {err}"
                triggered, trigger_reason = cb.record_result(
                    is_server_error=is_server,
                    reason=reason,
                    error_type=err
                )
                assert triggered is False, f"CB triggered prematurely on cycle {i}, error {err}: {trigger_reason}"
                assert cb.triggered is False

        assert cb.total_processed == 60
        assert cb.total_server_errors == 20
        # Ratio is 20/60 = 0.333 <= 0.50
        assert cb.consecutive_server_errors <= 1
        assert cb.triggered is False

    def test_interleaved_session_and_account_errors_with_zero_ip_errors_never_trips(self):
        """100 consecutive non-IP errors (50 session_error, 50 account_error).
        Verify consecutive_server_errors stays 0 and circuit breaker NEVER trips."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        for i in range(50):
            triggered, _ = cb.record_result(is_server_error=False, reason="DOM no hidratado", error_type="session_error")
            assert triggered is False
            triggered, _ = cb.record_result(is_server_error=False, reason="Credenciales invalidas", error_type="account_error")
            assert triggered is False

        assert cb.total_processed == 100
        assert cb.total_server_errors == 0
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    def test_eight_consecutive_ip_errors_triggers_circuit_breaker(self):
        """Verify that exactly 8 consecutive ip_error events trigger the circuit breaker."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        # First 7 IP errors: should NOT trigger yet
        for i in range(1, 8):
            triggered, reason = cb.record_result(is_server_error=True, reason=f"Cloudflare {i}", error_type="ip_error")
            assert triggered is False, f"Triggered prematurely at iteration {i}"
            assert cb.consecutive_server_errors == i
            assert cb.triggered is False

        # 8th consecutive IP error: MUST trigger
        triggered, reason = cb.record_result(is_server_error=True, reason="Cloudflare 8", error_type="ip_error")
        assert triggered is True, "Circuit breaker failed to trip on 8th consecutive IP error"
        assert cb.triggered is True
        assert cb.consecutive_server_errors == 8
        assert "8 caídas consecutivas" in reason
        assert "Cloudflare 8" in reason

    def test_reset_consecutive_at_seventh_ip_error_prevents_tripping(self):
        """Stress testing boundary: 7 IP errors -> 1 session error -> 7 IP errors -> 1 account error.
        Total IP errors = 14, total errors = 16.
        Verify consecutive counter never reaches 8 when interleaved with non-IP errors."""
        # Use max_failure_ratio=1.0 to isolate the consecutive failure logic
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=1.0, min_processed_threshold=10)

        # 7 consecutive IP errors
        for i in range(7):
            cb.record_result(is_server_error=True, reason="WAF Block", error_type="ip_error")
        assert cb.consecutive_server_errors == 7
        assert cb.triggered is False

        # Single session error resets counter
        cb.record_result(is_server_error=False, reason="Saldo no hidratado", error_type="session_error")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

        # Another 7 consecutive IP errors
        for i in range(7):
            cb.record_result(is_server_error=True, reason="WAF Block", error_type="ip_error")
        assert cb.consecutive_server_errors == 7
        assert cb.triggered is False

        # Single account error resets counter again
        cb.record_result(is_server_error=False, reason="Credenciales incorrectas", error_type="account_error")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    def test_needs_attention_also_resets_consecutive_server_errors(self):
        """Verify that 2FA or Call Center 'needs_attention' resets consecutive_server_errors."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        for i in range(6):
            cb.record_result(is_server_error=True, reason="HTTP 502", error_type="ip_error")
        assert cb.consecutive_server_errors == 6

        cb.record_result(is_server_error=False, reason="Call Center 2FA", error_type="needs_attention")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    @pytest.mark.parametrize("status_code,page_source,error_msg,expected_tier", [
        (429, "", "", "ip_error"),
        (403, "", "", "ip_error"),
        (500, "", "", "ip_error"),
        (502, "", "", "ip_error"),
        (522, "", "", "ip_error"),
        (None, "<html>Cloudflare Ray ID: 12345</html>", "", "ip_error"),
        (None, "Attention Required! | Cloudflare challenge-platform", "", "ip_error"),
        (None, "Too Many Requests - Access forbidden by WAF", "", "ip_error"),
        (None, "", "net::ERR_CONNECTION_TIMED_OUT", "ip_error"),
        (None, "", "connection refused by target host", "ip_error"),
        (None, "", "timeout esperando #uname1", "ip_error"),
        (None, "Tu cuenta ha sido bloqueada. Contacte Call Center.", "", "needs_attention"),
        (None, '<div><button id="btnPwReset">Restablecer contraseña</button></div>', "", "needs_attention"),
        (None, "Introduce el código de verificación 2FA", "", "needs_attention"),
        (None, "Device activation OTP sent to email", "", "needs_attention"),
        (None, "", "session_error: timeout esperando redirección", "session_error"),
        (None, "Tu sesión ha expirado", "", "session_error"),
        (None, "", "Error: Saldo no hidratado en DOM", "session_error"),
        (None, "", "authenticationerror during oauth handshake", "session_error"),
        (None, "Usuario o contraseña incorrectos", "", "account_error"),
        (None, "", "Error: credenciales no redirigidas o no válidas", "account_error"),
        (None, "Contraseña no válida", "", "account_error"),
        (None, "", "random unknown failure after login form submit", "account_error"),
    ])
    def test_classify_error_4_tier_adversarial_matrix(self, status_code, page_source, error_msg, expected_tier):
        cb = CircuitBreaker()
        tier, reason = cb.classify_error(status_code=status_code, page_source=page_source, error_msg=error_msg)
        assert tier == expected_tier, f"Failed for status={status_code}, page='{page_source}', err='{error_msg}'. Got {tier} instead of {expected_tier}"


# ==============================================================================
# 2. ADVERSARIAL STRESS TESTS: _verify_and_hydrate_session
# ==============================================================================

class MockStressDriver:
    """Configurable Mock WebDriver capable of simulating arbitrary network and DOM failures."""

    def __init__(
        self,
        current_url="https://www.compraonline.alcampo.es/settings/loyalty",
        page_sources=None,
        refresh_exception=None,
        get_exception=None,
        page_source_exception=None,
    ):
        self.current_url = current_url
        self.page_sources = page_sources or [""]
        self.page_idx = 0
        self.refresh_exception = refresh_exception
        self.get_exception = get_exception
        self.page_source_exception = page_source_exception

        self.refresh_calls = 0
        self.get_calls = []

    @property
    def page_source(self):
        if self.page_source_exception:
            raise self.page_source_exception
        if self.page_idx < len(self.page_sources):
            return self.page_sources[self.page_idx]
        return self.page_sources[-1] if self.page_sources else ""

    def refresh(self):
        self.refresh_calls += 1
        if self.refresh_exception:
            raise self.refresh_exception
        if self.page_idx + 1 < len(self.page_sources):
            self.page_idx += 1

    def get(self, url):
        self.get_calls.append(url)
        self.current_url = url
        if self.get_exception:
            raise self.get_exception
        if self.page_idx + 1 < len(self.page_sources):
            self.page_idx += 1


class TestVerifyAndHydrateSessionAdversarialStress:
    """Adversarial stress testing of _verify_and_hydrate_session under pathological conditions."""

    @pytest.fixture(autouse=True)
    def patch_sleep(self):
        """Patch time.sleep so stress tests run instantaneously without real delays."""
        with mock.patch("time.sleep", return_value=None):
            yield

    def test_stubborn_unhydrated_dom_never_hydrates(self):
        """Simulates stubborn DOM that never shows balance or card across initial check,
        refresh, and home navigation. Must not hang or crash, and return fallback tuple."""
        driver = MockStressDriver(
            page_sources=[
                "<html><body><div>Cargando perfil de usuario...</div></body></html>",
                "<html><body><div>Cargando perfil de usuario tras refresh...</div></body></html>",
                "<html><body><div>Home alcampo</div></body></html>",
                "<html><body><div>Cargando perfil de usuario tras home...</div></body></html>",
            ]
        )

        saldo, card_number = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "No encontrado"
        assert card_number is None
        assert driver.refresh_calls == 1
        assert "https://www.compraonline.alcampo.es/" in driver.get_calls
        assert "https://www.compraonline.alcampo.es/settings/loyalty" in driver.get_calls

    def test_stubborn_zero_balance_without_card_never_hydrates(self):
        """Simulates a stubborn fake 0,00 € DOM where loyalty card never appears.
        Must complete both refresh and home recovery attempts, returning ('Tu Saldo es 0,00 €', None)."""
        driver = MockStressDriver(
            page_sources=[
                "<div><p>Tu Saldo es 0,00 €</p></div>",
                "<div><p>Tu Saldo es 0,00 €</p></div>",
                "<div>Home</div>",
                "<div><p>Tu Saldo es 0,00 €</p></div>",
            ]
        )

        saldo, card_number = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "Tu Saldo es 0,00 €"
        assert card_number is None
        assert driver.refresh_calls == 1
        assert len(driver.get_calls) >= 2

    def test_slow_navigation_hydrates_on_second_polling_attempt(self):
        """Simulates dynamic SPA hydration where balance appears on delayed poll without refresh."""
        pages = [
            "<div>Cargando...</div>",
            "<div>Tu Saldo es 18,75 €</div><span class='sana-sans-alt'>4002005555555</span>"
        ]

        class DynamicPollingDriver:
            def __init__(self):
                self.current_url = "https://www.compraonline.alcampo.es/settings/loyalty"
                self.access_count = 0
                self.refresh_calls = 0
                self.get_calls = []

            @property
            def page_source(self):
                self.access_count += 1
                if self.access_count == 1:
                    return pages[0]
                return pages[1]

            def refresh(self):
                self.refresh_calls += 1

            def get(self, url):
                self.get_calls.append(url)

        driver = DynamicPollingDriver()
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.5)

        assert saldo == "Tu Saldo es 18,75 €"
        assert card == "4002005555555"
        assert driver.refresh_calls == 0
        assert driver.get_calls == []

    def test_exception_during_driver_refresh_handled_gracefully(self):
        """Simulates WebDriver crashing/throwing during driver.refresh().
        _verify_and_hydrate_session must catch the exception, proceed to home navigation,
        and return safely without raising."""
        driver = MockStressDriver(
            page_sources=["<div>Sin datos</div>", "<div>Sin datos</div>"],
            refresh_exception=Exception("WebDriverException: connection reset by peer")
        )

        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "No encontrado"
        assert card is None
        assert driver.refresh_calls == 1
        # It still attempted home navigation after refresh crashed
        assert "https://www.compraonline.alcampo.es/" in driver.get_calls

    def test_exceptions_during_both_refresh_and_get_handled_gracefully(self):
        """Simulates catastrophic WebDriver failure where both refresh() and get() raise exceptions.
        Must return ('No encontrado', None) without unhandled exception."""
        driver = MockStressDriver(
            page_sources=["<div>Sin datos</div>"],
            refresh_exception=RuntimeError("Broken pipe"),
            get_exception=TimeoutError("Navigation timed out")
        )

        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "No encontrado"
        assert card is None

    def test_exception_accessing_page_source_handled_gracefully(self):
        """Simulates WebDriver throwing an exception when reading driver.page_source."""
        driver = MockStressDriver(
            page_source_exception=Exception("Window already closed / SessionNotFound")
        )

        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "No encontrado"
        assert card is None

    def test_empty_string_page_source_never_crashes(self):
        """Empty string page_source must return fallback tuple safely."""
        driver = MockStressDriver(page_sources=["", "", ""])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)
        assert saldo == "No encontrado"
        assert card is None

    def test_whitespace_and_newlines_only_page_source(self):
        """Page source containing only spaces, tabs, and newlines."""
        driver = MockStressDriver(page_sources=["   \n\t\r\n   ", "   "])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)
        assert saldo == "No encontrado"
        assert card is None

    def test_none_page_source_handled_gracefully(self):
        """Simulates driver.page_source returning None."""
        driver = MockStressDriver(page_sources=[None, None])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)
        assert saldo == "No encontrado"
        assert card is None

    def test_corrupt_malformed_html_and_script_injection(self):
        """Simulates deeply nested unclosed tags, binary garbage, and script tags."""
        corrupted_html = (
            "<html><head><script>var x = {invalid json; function()</script></head>"
            "<body><div><p>Tu Saldo es 45,90 €</p>"
            "<script id='__NEXT_DATA__'>{'props': broken JSON</script>"
            "<span class='s1-subtitle'>4002008888888</span>"
            + "\x00\x01\xff\xfe" * 10
            + "</div></body></html>"
        )
        driver = MockStressDriver(page_sources=[corrupted_html])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "Tu Saldo es 45,90 €"
        assert card == "4002008888888"
        assert driver.refresh_calls == 0

    def test_hydration_succeeds_only_after_home_navigation(self):
        """Simulates handshake that fails on initial load AND refresh,
        but succeeds after navigating to home and returning to loyalty."""
        p_unhydrated = "<div><p>Cargando perfil...</p></div>"
        p_hydrated = (
            "<div><p>Tu Saldo es 33,20 €</p>"
            "<span class='sana-sans-alt'>4002007777777</span></div>"
        )
        driver = MockStressDriver(
            page_sources=[
                p_unhydrated,  # Initial read
                p_unhydrated,  # After refresh
                p_unhydrated,  # On home
                p_hydrated,    # After home -> loyalty
            ]
        )

        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "Tu Saldo es 33,20 €"
        assert card == "4002007777777"
        assert driver.refresh_calls == 1
        assert "https://www.compraonline.alcampo.es/" in driver.get_calls
        assert "https://www.compraonline.alcampo.es/settings/loyalty" in driver.get_calls
