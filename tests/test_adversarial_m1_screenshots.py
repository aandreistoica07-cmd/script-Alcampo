"""
Empirical Adversarial Test Suite for Milestone M1 (Screenshot Instrumentation).
Author: Screenshot Challenger 2
Tests systematic screenshot capture and error injection across:
- `capture_screenshot` safety and contracts
- `_scrape_account_with_driver` error paths and labels
- `check_single_account` error paths and labels
- `scripts/local_test.py` run_single_test error paths and labels
"""

import os
import re
import pytest
from unittest.mock import MagicMock, patch, call
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.script_optimizado import (
    capture_screenshot,
    _scrape_account_with_driver,
    check_single_account,
    limpiar_saldo
)
import scripts.local_test as local_test_module


# ==============================================================================
# 1. HELPER CONTRACT & RESILIENCE TESTS
# ==============================================================================

class TestCaptureScreenshotContract:
    """Stress tests the capture_screenshot helper against adverse runtime conditions."""

    def test_null_driver_returns_none(self):
        """Passing None driver must safely return None without raising."""
        assert capture_screenshot(None, "user@alcampo.es", "err_inputs") is None

    def test_driver_without_save_screenshot_returns_none(self):
        """Driver without save_screenshot method must safely return None."""
        dummy_driver = object()
        assert capture_screenshot(dummy_driver, "user@alcampo.es", "err_inputs") is None

    def test_driver_save_screenshot_exception_absorbed(self, tmp_path):
        """Exceptions in save_screenshot (e.g. disk full, permission denied) must be caught."""
        mock_driver = MagicMock()
        mock_driver.save_screenshot.side_effect = PermissionError("WinError 5: Access Denied")
        res = capture_screenshot(mock_driver, "user@alcampo.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None
        mock_driver.save_screenshot.assert_called_once()

    def test_email_sanitization(self, tmp_path):
        """Special characters in email must be sanitized to valid filesystem characters."""
        mock_driver = MagicMock()
        mock_driver.save_screenshot.return_value = True
        shot_path = capture_screenshot(
            mock_driver,
            "test.user+tag#123@sub.alcampo.es",
            "err_inputs",
            screenshot_dir=str(tmp_path)
        )
        assert shot_path is not None
        filename = os.path.basename(shot_path)
        assert "@" not in filename
        assert "+" not in filename
        assert "#" not in filename
        assert filename.startswith("test_user_tag_123_sub_alcampo_es_err_inputs_")
        assert filename.endswith(".png")

    def test_none_email_defaults_to_anon(self, tmp_path):
        """Email None or empty string must default to 'anon'."""
        mock_driver = MagicMock()
        mock_driver.save_screenshot.return_value = True
        shot_path = capture_screenshot(mock_driver, None, "err_unexpected", screenshot_dir=str(tmp_path))
        assert shot_path is not None
        assert os.path.basename(shot_path).startswith("anon_err_unexpected_")

    def test_directory_created_automatically(self, tmp_path):
        """If target directory does not exist, it must be created automatically."""
        target_dir = tmp_path / "deep" / "nested" / "screenshots"
        assert not target_dir.exists()
        mock_driver = MagicMock()
        mock_driver.save_screenshot.return_value = True
        shot_path = capture_screenshot(mock_driver, "u@test.es", "test_label", screenshot_dir=str(target_dir))
        assert target_dir.exists()
        assert shot_path is not None


# ==============================================================================
# 2. ERROR INJECTION IN `_scrape_account_with_driver`
# ==============================================================================

class TestScrapeAccountWithDriverErrorInjection:
    """Empirical verification that simulated errors in _scrape_account_with_driver trigger capture_screenshot with expected labels."""

    def test_err_inputs_when_uname1_times_out(self):
        """When #uname1 times out without WAF, capture_screenshot must be called with err_inputs."""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Generic Login Page</body></html>"
        mock_driver.current_url = "https://compraonline.alcampo.es/login"

        with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("Timed out waiting for #uname1")
            mock_wait_cls.return_value = mock_wait

            # Execute function
            driver_ret, res = _scrape_account_with_driver(
                driver=mock_driver,
                init_driver_fn=lambda: mock_driver,
                email="witness@alcampo.es",
                password="pass",
                label_prefix="[Test]"
            )

            # Check capture_screenshot was invoked with err_inputs
            labels_captured = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_inputs" in labels_captured

    def test_err_waf_when_uname1_times_out_with_cloudflare(self):
        """When #uname1 times out with Cloudflare in page_source, err_waf must be captured."""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Attention Required! Cloudflare Ray ID: 87654321 blocked by cloudflare</body></html>"
        mock_driver.current_url = "https://compraonline.alcampo.es/login"

        with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("Timed out")
            mock_wait_cls.return_value = mock_wait

            driver_ret, res = _scrape_account_with_driver(
                driver=mock_driver,
                init_driver_fn=lambda: mock_driver,
                email="witness@alcampo.es",
                password="pass",
                label_prefix="[Test]"
            )

            labels_captured = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_waf" in labels_captured

    def test_err_needs_attention_when_pwreset_outcome(self):
        """When _check_login_outcome returns 'pwreset', capture_screenshot must record err_needs_attention."""
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_driver.find_element.return_value = mock_elem

        with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.submit_login_form"), \
             patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
             patch("scraper.script_optimizado._handle_pwreset_relogin") as mock_pw_relogin, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elem
            mock_wait_cls.return_value = mock_wait
            mock_outcome.return_value = ("pwreset", "Password reset required")
            mock_pw_relogin.return_value = (False, "Relogin failed")

            driver_ret, res = _scrape_account_with_driver(
                driver=mock_driver,
                init_driver_fn=lambda: mock_driver,
                email="pwreset_user@alcampo.es",
                password="pass",
                label_prefix="[Test]"
            )

            labels_captured = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_needs_attention" in labels_captured

    def test_err_call_center_on_account_lock(self):
        """When login outcome is error and page mentions call center / bloqueada, err_call_center must be captured."""
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_driver.find_element.return_value = mock_elem
        mock_driver.page_source = "<html><body>Tu cuenta ha sido bloqueada. Contacte con Call Center 913 687 857</body></html>"

        with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.submit_login_form"), \
             patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elem
            mock_wait_cls.return_value = mock_wait
            mock_outcome.return_value = ("error", "Cuenta bloqueada")

            driver_ret, res = _scrape_account_with_driver(
                driver=mock_driver,
                init_driver_fn=lambda: mock_driver,
                email="locked@alcampo.es",
                password="pass",
                label_prefix="[Test]"
            )

            labels_captured = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_call_center" in labels_captured

    def test_err_oauth_timeout_on_pending_redirect(self):
        """When login outcome stays pending beyond poll timeout, err_oauth_timeout must be captured."""
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_driver.find_element.return_value = mock_elem
        mock_driver.page_source = "<html><body>Authorizing...</body></html>"

        with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.submit_login_form"), \
             patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
             patch("scraper.script_optimizado.time.time") as mock_time, \
             patch("scraper.script_optimizado.time.sleep"), \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elem
            mock_wait_cls.return_value = mock_wait
            # Simulate time advancing 16s so poll loop finishes
            mock_time.side_effect = [100.0, 100.0, 100.0, 116.0, 116.0, 116.0, 116.0, 116.0]
            mock_outcome.return_value = ("pending", "")

            driver_ret, res = _scrape_account_with_driver(
                driver=mock_driver,
                init_driver_fn=lambda: mock_driver,
                email="timeout@alcampo.es",
                password="pass",
                label_prefix="[Test]"
            )

            labels_captured = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_oauth_timeout" in labels_captured

    def test_loyalty_balance_labels(self):
        """Test positive balance, zero verified, and unhydrated balance labels."""
        for balance_val, card_val, expected_label in [
            ("Tu Saldo es 3,50 €", "4002001234567", "saldo_positivo"),
            ("Tu Saldo es 0,00 €", "4002001234567", "saldo_cero_verificado"),
            ("Tu Saldo es 0,00 €", None, "saldo_cero_compraonline"),
            ("No encontrado", None, "saldo_no_detectado"),
        ]:
            mock_driver = MagicMock()
            mock_elem = MagicMock()
            mock_driver.find_element.return_value = mock_elem

            with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
                 patch("scraper.script_optimizado.submit_login_form"), \
                 patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
                 patch("scraper.script_optimizado._verify_and_hydrate_session") as mock_hydrate, \
                 patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
                mock_wait = MagicMock()
                mock_wait.until.return_value = mock_elem
                mock_wait_cls.return_value = mock_wait
                mock_outcome.return_value = ("logged_in", "")
                mock_hydrate.return_value = (balance_val, card_val)

                driver_ret, res = _scrape_account_with_driver(
                    driver=mock_driver,
                    init_driver_fn=lambda: mock_driver,
                    email="loyalty@alcampo.es",
                    password="pass",
                    label_prefix="[Test]"
                )

                labels_captured = [call_args[0][2] for call_args in mock_capture.call_args_list]
                assert expected_label in labels_captured, f"Expected {expected_label} in {labels_captured} for balance='{balance_val}', card='{card_val}'"


# ==============================================================================
# 3. ERROR INJECTION IN `check_single_account`
# ==============================================================================

class TestCheckSingleAccountErrorInjection:
    """Empirical verification that simulated errors in check_single_account trigger capture_screenshot with expected labels."""

    def test_err_inputs_on_uname1_timeout(self):
        """check_single_account captures err_inputs when #uname1 times out."""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Login Form Missing</body></html>"

        with patch("scraper.script_optimizado.create_stealth_driver") as mock_create, \
             patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_create.return_value = mock_driver
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("uname1 not found")
            mock_wait_cls.return_value = mock_wait

            res = check_single_account("single_test@alcampo.es", "secret")
            assert res["status"] == "error"

            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_inputs" in labels

    def test_err_call_center_on_locked_account(self):
        """check_single_account captures err_call_center when locked account is detected."""
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_driver.find_element.return_value = mock_elem
        mock_driver.page_source = "<html><body>Tu cuenta ha sido bloqueada. Call Center 913 687 857</body></html>"

        with patch("scraper.script_optimizado.create_stealth_driver") as mock_create, \
             patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.submit_login_form"), \
             patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_create.return_value = mock_driver
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elem
            mock_wait_cls.return_value = mock_wait
            mock_outcome.return_value = ("error", "Cuenta bloqueada")

            res = check_single_account("locked_single@alcampo.es", "secret")
            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_call_center" in labels

    def test_err_needs_attention_on_pwreset(self):
        """check_single_account captures err_needs_attention when pwreset is triggered."""
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_driver.find_element.return_value = mock_elem
        mock_driver.page_source = "<html><body>Restablecer contrasena btnPwReset</body></html>"

        with patch("scraper.script_optimizado.create_stealth_driver") as mock_create, \
             patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.submit_login_form"), \
             patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
             patch("scraper.script_optimizado._handle_pwreset_relogin") as mock_relogin, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_create.return_value = mock_driver
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elem
            mock_wait_cls.return_value = mock_wait
            mock_outcome.return_value = ("pwreset", "Password reset required")
            mock_relogin.return_value = (False, "Relogin failed")

            res = check_single_account("reset_single@alcampo.es", "secret")
            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_needs_attention" in labels

    def test_saldo_positivo_capture(self):
        """check_single_account captures saldo_positivo when balance > 0."""
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_driver.find_element.return_value = mock_elem
        mock_driver.page_source = "<html><body>Tu Saldo es 12,50 €</body></html>"

        with patch("scraper.script_optimizado.create_stealth_driver") as mock_create, \
             patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls, \
             patch("scraper.script_optimizado.submit_login_form"), \
             patch("scraper.script_optimizado._check_login_outcome") as mock_outcome, \
             patch("scraper.script_optimizado._extract_loyalty_balance") as mock_extract, \
             patch("scraper.script_optimizado.capture_screenshot") as mock_capture:
            mock_create.return_value = mock_driver
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elem
            mock_wait_cls.return_value = mock_wait
            mock_outcome.return_value = ("logged_in", "")
            mock_extract.return_value = "Tu Saldo es 12,50 €"

            res = check_single_account("positive@alcampo.es", "secret")
            assert res["status"] == "success"
            assert res["balance"] == 12.50

            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "saldo_positivo" in labels


# ==============================================================================
# 4. ERROR INJECTION IN `scripts/local_test.py`
# ==============================================================================

class TestLocalTestRunnerErrorInjection:
    """Empirical verification of capture_screenshot calls in local_test.run_single_test."""

    def test_local_test_err_inputs(self, tmp_path):
        """local_test.run_single_test captures err_inputs when #uname1 is missing."""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Login Form Broken</body></html>"

        with patch("scripts.local_test.WebDriverWait") as mock_wait_cls, \
             patch("scripts.local_test.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("inputs not found")
            mock_wait_cls.return_value = mock_wait

            res = local_test_module.test_single_account(
                driver=mock_driver,
                email="cli_test@alcampo.es",
                password="pass",
                screenshot_dir=str(tmp_path)
            )
            assert res["status"] == "failed"
            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_inputs" in labels

    def test_local_test_err_waf(self, tmp_path):
        """local_test.test_single_account captures err_waf when cloudflare is detected."""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Cloudflare Ray ID blocked by cloudflare</body></html>"

        with patch("scripts.local_test.WebDriverWait") as mock_wait_cls, \
             patch("scripts.local_test.capture_screenshot") as mock_capture:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("waf block")
            mock_wait_cls.return_value = mock_wait

            res = local_test_module.test_single_account(
                driver=mock_driver,
                email="cli_waf@alcampo.es",
                password="pass",
                screenshot_dir=str(tmp_path)
            )
            assert res["status"] == "failed"
            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_waf" in labels

    def test_local_test_err_unexpected(self, tmp_path):
        """local_test.test_single_account captures err_unexpected on unhandled crash."""
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("Browser disconnected unexpectedly")

        with patch("scripts.local_test.capture_screenshot") as mock_capture:
            res = local_test_module.test_single_account(
                driver=mock_driver,
                email="cli_crash@alcampo.es",
                password="pass",
                screenshot_dir=str(tmp_path)
            )
            assert res["status"] == "error"
            labels = [call_args[0][2] for call_args in mock_capture.call_args_list]
            assert "err_unexpected" in labels


# ==============================================================================
# 5. ADVERSARIAL STRESS & RESILIENCE: SCREENSHOT SUBSYSTEM FAILURES
# ==============================================================================

class TestScreenshotFailureResilience:
    """Stress tests: even if the screenshot subsystem completely fails, scraping logic must not crash."""

    def test_scrape_account_resilient_to_save_screenshot_crash(self):
        """If driver.save_screenshot raises an exception, _scrape_account_with_driver must not crash."""
        mock_driver = MagicMock()
        mock_driver.save_screenshot.side_effect = OSError("Disk full: [WinError 112]")
        mock_driver.page_source = "<html><body>Generic Page</body></html>"

        with patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("inputs not found")
            mock_wait_cls.return_value = mock_wait

            # Must not raise OSError, must catch and return normal error result
            driver_ret, res = _scrape_account_with_driver(
                driver=mock_driver,
                init_driver_fn=lambda: mock_driver,
                email="resilience@alcampo.es",
                password="pass",
                label_prefix="[Resilience]"
            )
            assert res is not None
            assert "Error" in res or "Timeout" in str(res)

    def test_check_single_account_resilient_to_save_screenshot_crash(self):
        """If driver.save_screenshot raises an exception, check_single_account must return error dict cleanly."""
        mock_driver = MagicMock()
        mock_driver.save_screenshot.side_effect = PermissionError("WinError 5: Access Denied")
        mock_driver.page_source = "<html><body>Generic Page</body></html>"

        with patch("scraper.script_optimizado.create_stealth_driver") as mock_create, \
             patch("scraper.script_optimizado.WebDriverWait") as mock_wait_cls:
            mock_create.return_value = mock_driver
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException("uname1 not found")
            mock_wait_cls.return_value = mock_wait

            res = check_single_account("resilience_single@alcampo.es", "secret")
            assert isinstance(res, dict)
            assert res["status"] == "error"
            assert "uname1 not found" in res["error"]

