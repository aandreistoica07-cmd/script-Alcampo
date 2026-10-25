"""
Adversarial Empirical Challenge Verification Suite for Milestone M3
Author: Challenger M3-1 (critic, specialist)
Working Directory: .agents/teamwork/challenger_m3_1

Empirically verifies:
1. Real witness dumps (dump_loyalty.html and dump_miportal.html) extraction of 3.00 € and 4003009301402.
2. 0.00 € taxonomy distinguishing genuine 0.00 € from degraded 0.00 €.
3. Flaw in scripts/merge_and_retry.py where is_definitive_success("Tu Saldo es 0,00 €") returns True.
"""

import os
import re
import time
from pathlib import Path
import pytest
import pandas as pd
from unittest.mock import MagicMock

from scraper.script_optimizado import (
    extraer_tarjeta,
    limpiar_saldo,
    _verify_and_hydrate_session,
    _extract_loyalty_balance,
)
from scripts.merge_and_retry import (
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMP_LOYALTY_PATH = REPO_ROOT / "dump_loyalty.html"
DUMP_MIPORTAL_PATH = REPO_ROOT / "dump_miportal.html"


class MockWitnessDriver:
    """Mock WebDriver designed to simulate the dual-layer transition from Capa 1 to Capa 2."""
    def __init__(self, capa1_html, capa2_html):
        self.capa1_html = capa1_html
        self.capa2_html = capa2_html
        self.current_url = "https://www.compraonline.alcampo.es/settings/loyalty"
        self.page_source = capa1_html
        self.navigated_urls = []
        self.refresh_count = 0
        self.screenshots = []

    def get(self, url):
        self.navigated_urls.append(url)
        self.current_url = url
        # If navigating away from Capa 1 to OAuth / miportal, switch page source to Capa 2
        if "miportal" in url.lower() or "customerdiamond" in url.lower() or "authorize" in url.lower():
            self.page_source = self.capa2_html
        elif "settings/loyalty" in url:
            self.page_source = self.capa1_html

    def refresh(self):
        self.refresh_count += 1

    def find_elements(self, by, value):
        if 'loyalty-manage-button' in value and 'data-test="loyalty-manage-button"' in self.page_source:
            elem = MagicMock()
            m = re.search(r'data-test=["\']loyalty-manage-button["\'][^>]*href=["\']([^"\']+)["\']', self.page_source) or \
                re.search(r'href=["\']([^"\']+)["\'][^>]*data-test=["\']loyalty-manage-button["\']', self.page_source)
            elem.get_attribute.return_value = m.group(1) if m else None
            return [elem]
        return []

    def save_screenshot(self, filepath):
        self.screenshots.append(filepath)
        return True


# ==============================================================================
# SECTION 1: Witness Account Real Dump Empirical Verification
# ==============================================================================

class TestWitnessAccountDumpDualLayer:
    """Empirical verification using actual production HTML dumps from Alcampo."""

    @pytest.fixture(autouse=True)
    def setup_dumps(self):
        assert DUMP_LOYALTY_PATH.exists(), f"Missing witness dump: {DUMP_LOYALTY_PATH}"
        assert DUMP_MIPORTAL_PATH.exists(), f"Missing witness dump: {DUMP_MIPORTAL_PATH}"
        self.loyalty_html = DUMP_LOYALTY_PATH.read_text(encoding="utf-8")
        self.miportal_html = DUMP_MIPORTAL_PATH.read_text(encoding="utf-8")

    def test_capa1_loyalty_dump_contains_degraded_markers_and_no_card(self):
        """
        Empirical proof: In dump_loyalty.html:
        1. 'Tu Saldo es 0,00 €' is present in the DOM.
        2. Alternative error banner 'settings.loyalty.manage.alternative' is present.
        3. loyalty-manage-button is present with Salesforce OAuth href.
        4. extraer_tarjeta returns None (no card rendered in degraded state).
        """
        assert "Tu Saldo es 0,00" in self.loyalty_html
        assert "data-test=\"loyalty-manage-button\"" in self.loyalty_html
        assert "Parece que hay algo que no va bien" in self.loyalty_html or \
               "settings.loyalty.manage.alternative" in self.loyalty_html

        # Crucial: Capa 1 degraded DOM does not expose any card number
        card = extraer_tarjeta(self.loyalty_html)
        assert card is None, f"Expected None in degraded Capa 1, got {card}"

    def test_capa2_miportal_dump_contains_genuine_balance_and_card(self):
        """
        Empirical proof: In dump_miportal.html:
        1. 'Saldo disponible' header exists.
        2. Saldo value is '3,00 €'.
        3. Loyalty card is '4003009301402' (series 400300).
        4. extraer_tarjeta successfully extracts '4003009301402'.
        """
        assert "Saldo disponible" in self.miportal_html
        assert "3,00" in self.miportal_html

        card = extraer_tarjeta(self.miportal_html)
        assert card == "4003009301402", f"Expected card 4003009301402, got {card}"

        # Verify balance regex used by Capa 2
        m_bal = re.search(r"Saldo disponible\s*</span>.*?<span[^>]*>\s*([\d,.]+)\s*(?:&nbsp;|\s)*€\s*</span>", self.miportal_html, re.DOTALL | re.IGNORECASE)
        if not m_bal:
            m_bal = re.search(r"class=[\"'][^\"']*(?:h4-headline|s1-subtitle)[^\"']*[\"'][^>]*>\s*(?:<span>)?\s*([\d,.]+)\s*(?:&nbsp;|\s)*€", self.miportal_html, re.DOTALL | re.IGNORECASE)
        if not m_bal:
            m_bal = re.search(r"Saldo disponible.*?([\d,.]+)\s*(?:&nbsp;|\s)*€", self.miportal_html, re.DOTALL | re.IGNORECASE)

        assert m_bal is not None, "Failed to match balance regex on dump_miportal.html"
        assert m_bal.group(1).strip() == "3,00"

    def test_dual_layer_execution_on_witness_dumps_recovers_positive_balance(self):
        """
        End-to-end empirical test:
        When _verify_and_hydrate_session runs with dump_loyalty.html, it detects degradation,
        navigates to OAuth link (loading dump_miportal.html), and returns 3.00 € and 4003009301402.
        """
        driver = MockWitnessDriver(self.loyalty_html, self.miportal_html)

        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=1.0, email="noelia_gll@hotmail.com")

        # Must have extracted genuine Capa 2 data
        assert saldo == "Tu Saldo es 3,00 €"
        assert tarjeta == "4003009301402"
        assert limpiar_saldo(saldo) == 3.00

        # Must have navigated to OAuth destination
        assert len(driver.navigated_urls) >= 1
        oauth_nav = driver.navigated_urls[0]
        assert "ar-customerdiamond-es.my.site.com" in oauth_nav or "miportal.alcampo.es" in oauth_nav


# ==============================================================================
# SECTION 2: 0.00 € Taxonomy Empirical Stress Tests
# ==============================================================================

class TestZeroEuroTaxonomy:
    """
    Empirical validation of the 3-category taxonomy defined in m3_debate_report.md:
    1. Saldo Cero Verificado (0.00 € + valid card + no degradation banner)
    2. Saldo Cero Degradado / Falso Cero (0.00 € + no card + degradation banner)
    3. Fallo de Hidratación / Timeout (no balance element found)
    """

    def test_category_1_saldo_cero_verificado_genuine(self):
        """Genuine 0.00 €: Has valid card and clean DOM. Must NOT trigger Capa 2."""
        clean_zero_dom = (
            '<html><body>'
            '<div data-test="loyalty-balance"><span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span></div>'
            '<span class="sana-sans-alt">4002005555555</span>'
            '</body></html>'
        )
        driver = MockWitnessDriver(clean_zero_dom, "")
        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.5, email="genuine_zero@test.es")

        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta == "4002005555555"
        assert limpiar_saldo(saldo) == 0.0
        # No Capa 2 navigation triggered
        assert len(driver.navigated_urls) == 0

    def test_category_2_saldo_cero_degraded_triggers_capa2_resolution(self):
        """Degraded 0.00 €: Has degradation banner and no card in Capa 1. Triggers Capa 2."""
        degraded_dom = (
            '<html><body>'
            '<div data-test="loyalty-balance"><span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span></div>'
            '<a data-test="loyalty-manage-button" href="https://www.miportal.alcampo.es/es/cuenta/fidelidad">'
            'settings.loyalty.manage.alternative: Parece que hay algo que no va bien.'
            '</a>'
            '</body></html>'
        )
        capa2_resolved_dom = (
            '<html><body>'
            '<span class="s1-subtitle">Saldo disponible</span>'
            '<span class="h4-headline"><span>0,00 €</span></span>'
            '<div value="?clif=4003001234567"><canvas></canvas></div>'
            '</body></html>'
        )
        driver = MockWitnessDriver(degraded_dom, capa2_resolved_dom)
        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.5, email="degraded_zero@test.es")

        # Successfully navigated to Capa 2 and extracted verified zero with card
        assert len(driver.navigated_urls) == 1
        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta == "4003001234567"

    def test_category_2_saldo_cero_degraded_capa2_failure_preserves_unverified_status(self):
        """Degraded 0.00 €: If Capa 2 times out or is unreachable, returns 0,00 € with tarjeta=None."""
        degraded_dom = (
            '<html><body>'
            '<div data-test="loyalty-balance"><span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span></div>'
            '<a data-test="loyalty-manage-button" href="https://www.miportal.alcampo.es/es/cuenta/fidelidad">'
            'Parece que hay algo que no va bien.'
            '</a>'
            '</body></html>'
        )
        # Capa 2 is blank / error / times out
        capa2_empty_dom = '<html><body>504 Gateway Timeout</body></html>'

        driver = MockWitnessDriver(degraded_dom, capa2_empty_dom)
        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.3, email="unverified_zero@test.es")

        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta is None, "Card must remain None when Capa 2 fails"

    def test_category_3_unhydrated_timeout_triggers_handshake(self):
        """Unhydrated / Timeout: Page source does not contain balance. Triggers refresh/home handshake."""
        unhydrated_dom = '<html><body><div>Cargando perfil de usuario...</div></body></html>'
        driver = MockWitnessDriver(unhydrated_dom, "")
        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.2, email="timeout@test.es")

        assert saldo == "No encontrado"
        assert tarjeta is None
        # Must have attempted refresh and home navigation
        assert driver.refresh_count >= 1
        assert "https://www.compraonline.alcampo.es/" in driver.navigated_urls


# ==============================================================================
# SECTION 3: Empirical Bug Proof in scripts/merge_and_retry.py
# ==============================================================================

class TestMergeAndRetryFlawProof:
    """
    Empirical demonstration of the fatal bug in scripts/merge_and_retry.py:
    is_definitive_success("Tu Saldo es 0,00 €") returns True, causing degraded 0.00 € accounts
    to be excluded from Pass 2 retry queue and excluded from Top 10 balance calculations.
    """

    def test_current_flawed_behavior_empirically_demonstrated(self):
        """
        EMPIRICAL BUG PROOF:
        Line 66-69 of scripts/merge_and_retry.py:
            def is_definitive_success(saldo_str):
                if not saldo_str or pd.isna(saldo_str):
                    return False
                return "Tu Saldo es" in str(saldo_str)

        When saldo_str is 'Tu Saldo es 0,00 €':
        1. is_definitive_success returns True (FLAW!)
        2. is_retryable_failure returns False (FLAW!)
        """
        flawed_saldo = "Tu Saldo es 0,00 €"

        # Direct evaluation of current codebase function
        current_success = is_definitive_success(flawed_saldo)
        current_retryable = is_retryable_failure(flawed_saldo)

        assert current_success is True, "EMPIRICAL PROOF: is_definitive_success erroneously returns True for 0,00 €"
        assert current_retryable is False, "EMPIRICAL PROOF: is_retryable_failure erroneously returns False for 0,00 €"

    def test_impact_on_retry_filtering_collect_failed_accounts(self, tmp_path):
        """
        Demonstrate the blast radius:
        A Pass 1 shard containing a degraded 0,00 € account with card_number=None
        is NOT collected for retry under the current logic.
        """
        from scripts.merge_and_retry import collect_failed_accounts

        shards_dir = tmp_path / "pass1_shards"
        shards_dir.mkdir()

        # Shard with degraded zero account (Noelia's state in Pass 1)
        shard_df = pd.DataFrame([
            {
                "email": "noelia_gll@hotmail.com",
                "password": "pwd",
                "saldo": "Tu Saldo es 0,00 €",
                "card_number": None,
                "causa_error": "",
                "error_type": "ok"
            }
        ])
        shard_df.to_excel(shards_dir / "pass1_shard_0.xlsx", index=False)

        failed_accounts = collect_failed_accounts([str(shards_dir / "pass1_shard_0.xlsx")])

        # Under the current flawed logic, collect_failed_accounts checks is_retryable_failure("Tu Saldo es 0,00 €") -> False
        # Therefore, the degraded account is completely lost from the retry queue!
        unrecovered = [a for a in failed_accounts if a["email"] == "noelia_gll@hotmail.com"]
        assert len(unrecovered) == 0, "Proves that current logic loses degraded accounts from Pass 2 retry queue"

    def test_proposed_m4_remediated_contract(self):
        """
        Specification and empirical proof of the remediated M4 logic:
        is_definitive_success(saldo_str, tarjeta_str) must require a valid card for 0.00 € balances.
        """
        def remediated_is_definitive_success(saldo_str, tarjeta_str=None):
            if not saldo_str or pd.isna(saldo_str):
                return False
            if "Tu Saldo es" not in str(saldo_str):
                return False
            val = limpiar_saldo(saldo_str)
            if val is None:
                return False
            if val > 0:
                return True
            # For 0.00 €, must have verified card number (13 digits starting with 400 or 280)
            if val == 0.0:
                if tarjeta_str and re.match(r"^(400\d{10}|280\d{10})$", str(tarjeta_str).strip()):
                    return True
                return False
            return False

        def remediated_is_retryable_failure(saldo_str, tarjeta_str=None, causa_str="", err_type=""):
            if remediated_is_definitive_success(saldo_str, tarjeta_str):
                return False
            if is_definitive_error(saldo_str, causa_str, err_type):
                return False
            return True

        # 1. Positive balance is always definitive success (with or without card)
        assert remediated_is_definitive_success("Tu Saldo es 3,00 €", "4003009301402") is True
        assert remediated_is_definitive_success("Tu Saldo es 3,00 €", None) is True
        assert remediated_is_retryable_failure("Tu Saldo es 3,00 €", "4003009301402") is False

        # 2. Verified zero balance (with card) is definitive success
        assert remediated_is_definitive_success("Tu Saldo es 0,00 €", "4003009301402") is True
        assert remediated_is_definitive_success("Tu Saldo es 0,00 €", "4002001111111") is True
        assert remediated_is_retryable_failure("Tu Saldo es 0,00 €", "4003009301402") is False

        # 3. Degraded zero balance (without card) is NOT definitive success -> RETRYABLE!
        assert remediated_is_definitive_success("Tu Saldo es 0,00 €", None) is False
        assert remediated_is_definitive_success("Tu Saldo es 0,00 €", "") is False
        assert remediated_is_definitive_success("Tu Saldo es 0,00 €", float("nan")) is False
        assert remediated_is_retryable_failure("Tu Saldo es 0,00 €", None) is True
        assert remediated_is_retryable_failure("Tu Saldo es 0,00 €", "") is True

        # 4. Permanent errors remain non-retryable
        assert remediated_is_retryable_failure("Error: Cuenta bloqueada (Call Center)", None) is False
        assert remediated_is_retryable_failure("Error: Credenciales incorrectas", None) is False
