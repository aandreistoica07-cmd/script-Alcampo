import sys
import time
from pathlib import Path
from unittest.mock import MagicMock
from selenium.webdriver.common.by import By
import pytest

from scripts.local_test import test_single_account as run_local_test_account
from scraper.script_optimizado import (
    _handle_pwreset_relogin,
    _verify_and_hydrate_session,
    extraer_tarjeta,
    limpiar_saldo,
    _check_login_outcome,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. WITNESS ACCOUNT FLOW EMPIRICAL TESTS (noelia_gll@hotmail.com)
# ==============================================================================

def test_witness_account_dual_layer_real_dumps():
    """Verify that _verify_and_hydrate_session extracts 3.00 € and 4003009301402 from real dumps."""
    loyalty_path = ROOT_DIR / "dump_loyalty.html"
    miportal_path = ROOT_DIR / "dump_miportal.html"

    with open(loyalty_path, "r", encoding="utf-8", errors="ignore") as f:
        loyalty_html = f.read()

    with open(miportal_path, "r", encoding="utf-8", errors="ignore") as f:
        miportal_html = f.read()

    driver = MagicMock()
    driver.current_url = "https://www.compraonline.alcampo.es/settings/loyalty"
    driver.page_source = loyalty_html

    def mock_get(url):
        driver.current_url = url
        driver.page_source = miportal_html

    driver.get.side_effect = mock_get

    btn_mock = MagicMock()
    btn_mock.get_attribute.return_value = "https://www.miportal.alcampo.es/es/cuenta/fidelidad"
    driver.find_elements.side_effect = lambda by, val: [btn_mock] if "loyalty-manage-button" in val else []

    saldo, card = _verify_and_hydrate_session(driver, timeout_s=1.0, email="noelia_gll@hotmail.com")

    assert saldo == "Tu Saldo es 3,00 €"
    assert card == "4003009301402"
    assert limpiar_saldo(saldo) == 3.0


# ==============================================================================
# 2. _handle_pwreset_relogin EMPIRICAL TESTS
# ==============================================================================

def test_handle_pwreset_relogin_success_flow():
    """Empirically test _handle_pwreset_relogin when relogin succeeds."""
    driver = MagicMock()
    driver.current_url = "https://ar-customerdiamond-es.my.site.com/authorization"

    reset_btn = MagicMock()
    reset_btn.is_displayed.return_value = True

    uname_input = MagicMock()
    pwd_input = MagicMock()
    submit_btn = MagicMock()

    driver.find_elements.side_effect = lambda by, val: [reset_btn] if val == "btnPwReset" else []
    driver.find_element.side_effect = lambda by, val: pwd_input if val == "pwd1" else submit_btn

    with pytest.MonkeyPatch.context() as mp:
        mock_wait = MagicMock()
        mock_wait.until.return_value = uname_input
        mp.setattr("scraper.script_optimizado.WebDriverWait", lambda d, t: mock_wait)

        # First outcome during loop is logged_in
        mp.setattr("scraper.script_optimizado._check_login_outcome", lambda d, allow_pwreset: ("logged_in", ""))

        ok, msg = _handle_pwreset_relogin(driver, "reset_user@test.es", "SecretPass123", timeout=1.0)
        assert ok is True
        assert msg == ""
        uname_input.clear.assert_called_once()
        uname_input.send_keys.assert_called_with("reset_user@test.es")
        pwd_input.clear.assert_called_once()
        pwd_input.send_keys.assert_called_with("SecretPass123")


def test_handle_pwreset_relogin_failure_routes_to_needs_attention():
    """Empirically test _handle_pwreset_relogin when relogin fails."""
    driver = MagicMock()
    driver.current_url = "https://ar-customerdiamond-es.my.site.com/authorization"

    reset_btn = MagicMock()
    reset_btn.is_displayed.return_value = True

    uname_input = MagicMock()
    pwd_input = MagicMock()
    submit_btn = MagicMock()

    driver.find_elements.side_effect = lambda by, val: [reset_btn] if val == "btnPwReset" else []
    driver.find_element.side_effect = lambda by, val: pwd_input if val == "pwd1" else submit_btn

    with pytest.MonkeyPatch.context() as mp:
        mock_wait = MagicMock()
        mock_wait.until.return_value = uname_input
        mp.setattr("scraper.script_optimizado.WebDriverWait", lambda d, t: mock_wait)

        # Check login outcome returns error
        mp.setattr("scraper.script_optimizado._check_login_outcome", lambda d, allow_pwreset: ("error", "Error: Credenciales incorrectas"))

        ok, msg = _handle_pwreset_relogin(driver, "reset_user@test.es", "WrongPass", timeout=1.0)
        assert ok is False
        assert "Credenciales incorrectas" in msg


# ==============================================================================
# 3. scripts/local_test.py EMPIRICAL STRESS TESTS & DEFECT VERIFICATION
# ==============================================================================

def test_local_test_pwreset_flow_resolved_without_name_error():
    """
    CRITICAL EMPIRICAL VERIFICATION OF DEFECT RESOLUTION:
    In scripts/local_test.py line 318+:
        page_src and page_src_low are initialized inside while elapsed_poll < timeout:
    This verifies that NameError is permanently resolved and test_single_account
    safely handles #btnPwReset detection and transitions to status == 'failed' (needs_attention).
    """
    driver = MagicMock()
    driver.current_url = "https://ar-customerdiamond-es.my.site.com/authorization"
    driver.title = "Salesforce Login"
    driver.page_source = "<html><body><button id='btnPwReset'>Reset</button></body></html>"

    uname_el = MagicMock()
    pwd_el = MagicMock()
    submit_el = MagicMock()
    reset_el = MagicMock()
    reset_el.is_displayed.return_value = True

    def mock_find_element(by, value):
        if value == "uname1":
            return uname_el
        if value == "pwd1":
            return pwd_el
        if value == "btnSubmit_login":
            return submit_el
        if value == "btnPwReset":
            return reset_el
        raise Exception(f"Element {value} not found")

    driver.find_element.side_effect = mock_find_element
    driver.find_elements.side_effect = lambda by, val: [reset_el] if val == "btnPwReset" else []

    res = run_local_test_account(driver, "witness@test.com", "SecretPass123", timeout=1.0)

    # Verifies the defect is resolved: No NameError, properly handled needs_attention failure
    assert res["status"] == "failed"
    assert "page_src_low" not in res.get("error_reason", "")
    assert res.get("error_type") == "needs_attention"
    assert "btnPwReset" in res.get("error_reason", "")


def test_local_test_pwreset_relogin_success_flow():
    """Verify that test_single_account successfully completes when _handle_pwreset_relogin succeeds."""
    driver = MagicMock()
    driver.current_url = "https://ar-customerdiamond-es.my.site.com/authorization"
    driver.title = "Salesforce Login"
    driver.page_source = "<html><body><button id='btnPwReset'>Reset</button></body></html>"

    uname_el = MagicMock()
    pwd_el = MagicMock()
    submit_el = MagicMock()
    reset_el = MagicMock()
    reset_el.is_displayed.return_value = True

    def mock_find_element(by, value):
        if value == "uname1":
            return uname_el
        if value == "pwd1":
            return pwd_el
        if value == "btnSubmit_login":
            return submit_el
        if value == "btnPwReset":
            return reset_el
        raise Exception(f"Element {value} not found")

    driver.find_element.side_effect = mock_find_element
    driver.find_elements.side_effect = lambda by, val: [reset_el] if val == "btnPwReset" else []

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("scripts.local_test._handle_pwreset_relogin", lambda d, e, p: (True, ""))
        mp.setattr("scripts.local_test._verify_and_hydrate_session", lambda d, timeout_s, email: ("Tu Saldo es 5,00 €", "4003001234567"))

        res = run_local_test_account(driver, "witness@test.com", "SecretPass123", timeout=1.0)

        assert res["status"] == "success"
        assert res["balance"] == 5.0
        assert "5.00" in res["balance_str"]
        assert res["card_number"] == "4003001234567"
