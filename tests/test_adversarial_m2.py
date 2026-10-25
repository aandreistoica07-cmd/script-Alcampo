"""
Empirical Adversarial Test Suite for Milestone M2 (Dual-Layer Loyalty Engine & Card Regex).
Author: Dual-Layer Challenger 1 (critic, specialist).
Purpose: Stress-test extraer_tarjeta and _verify_and_hydrate_session with extreme, adversarial,
         and boundary inputs to verify correctness, robustness, and graceful degradation.
"""

import re
import time
import pytest
from unittest.mock import MagicMock
from selenium.common.exceptions import TimeoutException, WebDriverException

from scraper.script_optimizado import (
    extraer_tarjeta,
    _verify_and_hydrate_session,
    limpiar_saldo,
)


class MockAdversarialDriver:
    """Mock WebDriver designed for simulating adversarial DOM environments."""

    def __init__(self, initial_url="https://www.compraonline.alcampo.es/settings/loyalty", initial_html=""):
        self.current_url = initial_url
        self.page_source = initial_html
        self.get_history = []
        self.refresh_called = 0
        self.get_side_effect = None
        self.page_source_map = {}  # url -> html
        self.screenshots = []

    def get(self, url):
        self.get_history.append(url)
        if self.get_side_effect:
            if callable(self.get_side_effect):
                self.get_side_effect(url)
            else:
                raise self.get_side_effect
        self.current_url = url
        if url in self.page_source_map:
            self.page_source = self.page_source_map[url]

    def refresh(self):
        self.refresh_called += 1

    def find_elements(self, by, value):
        # Support basic mock finding for [data-test="loyalty-manage-button"]
        if 'loyalty-manage-button' in value and 'data-test="loyalty-manage-button"' in self.page_source:
            elem = MagicMock()
            m = re.search(r'data-test=["\']loyalty-manage-button["\'][^>]*href=["\']([^"\']+)["\']', self.page_source) or \
                re.search(r'href=["\']([^"\']+)["\'][^>]*data-test=["\']loyalty-manage-button["\']', self.page_source)
            elem.get_attribute.return_value = m.group(1) if m else None
            return [elem]
        return []

    def save_screenshot(self, filename):
        self.screenshots.append(filename)
        return True


# ==============================================================================
# 1. ADVERSARIAL STRESS-TESTS FOR extraer_tarjeta
# ==============================================================================

class TestExtraerTarjetaAdversarial:
    """Adversarial stress-testing of card number extraction from HTML."""

    @pytest.mark.parametrize("barcode", [
        "8410000000000",  # Standard Spanish retail EAN-13 (84 prefix)
        "8480000123456",  # Mercadona EAN-13
        "5000000000000",  # UK retail barcode
        "3000000000000",  # French retail barcode
        "4010000000000",  # German barcode (401 != 400)
        "4020000000000",  # German barcode (402 != 400)
        "1234567890123",  # Arbitrary 13-digit number
        "9999999999999",  # Arbitrary digits
    ])
    def test_rejects_foreign_and_product_barcodes_in_all_contexts(self, barcode):
        """Barcodes not belonging to Alcampo ranges (400 or 280) must strictly return None."""
        assert extraer_tarjeta(f'<div>{barcode}</div>') is None
        assert extraer_tarjeta(f'<span class="sana-sans-alt">{barcode}</span>') is None
        assert extraer_tarjeta(f'<span class="s1-subtitle">{barcode}</span>') is None
        assert extraer_tarjeta(f'<p>tarjeta {barcode}</p>') is None
        assert extraer_tarjeta(f'<div value="?clif={barcode}"></div>') is None
        assert extraer_tarjeta(f'{{"loyaltyCardNumber": "{barcode}"}}') is None

    @pytest.mark.parametrize("invalid_len", [
        "400300930140",     # 12 digits (too short)
        "40030093014029",   # 14 digits (too long)
        "40020012345",      # 11 digits
        "400200123456789",  # 15 digits
        "280123456789",     # 12 digits for 280
        "28012345678901",   # 14 digits for 280
    ])
    def test_rejects_invalid_length_numbers(self, invalid_len):
        """Numbers with non-13 digit length must never match."""
        assert extraer_tarjeta(f'<span>{invalid_len}</span>') is None
        assert extraer_tarjeta(f'<span class="sana-sans-alt">{invalid_len}</span>') is None
        assert extraer_tarjeta(f'<p>tarjeta asociada {invalid_len}</p>') is None

    def test_extreme_malformed_tags_and_nested_dom(self):
        """Malformed and broken HTML tags must not crash the parser and should extract valid card."""
        # Unclosed div, missing quotes, mixed case
        html_broken = (
            '<DIV class=sana-sans-alt>\n'
            '  <<<custom-tag>>>\n'
            '    4003009301402\n'
            '  </custom-tag>\n'
            '</DIV>'
        )
        assert extraer_tarjeta(html_broken) == "4003009301402"

        # Highly nested unclosed formatting tags
        html_nested = (
            '<div class="s1-subtitle">'
            '<b><i><strong><em>&nbsp; 4003009301402 &nbsp;</em></strong></i></b>'
            '</div>'
        )
        assert extraer_tarjeta(html_nested) == "4003009301402"

    def test_unicode_entities_and_unusual_whitespace(self):
        """Card numbers surrounded by non-breaking spaces, entities, and newlines must extract cleanly."""
        # Multiple non-breaking spaces and HTML entities
        html_entities = '<span>&gt;&nbsp;&nbsp;4003009301402&nbsp;&nbsp;&lt;</span>'
        assert extraer_tarjeta(html_entities) == "4003009301402"

        # Carriage returns, tabs, and zero-width spaces mixed with valid card
        html_whitespace = '<div>\r\n\t  \t4002001234567\r\n\t  </div>'
        assert extraer_tarjeta(html_whitespace) == "4002001234567"

    def test_multiple_cards_precedence_and_deterministic_resolution(self):
        """When multiple card lookups exist, extraction must prioritize canvas/query param, then specific classes."""
        # Case A: clif query param vs lower text card
        html_multi = (
            '<div value="?clif=4003009301402"><canvas></canvas></div>'
            '<p>tarjeta antigua 4002001111111</p>'
        )
        assert extraer_tarjeta(html_multi) == "4003009301402"

        # Case B: First valid card is returned without error when two cards exist
        html_two_cards = (
            '<span class="sana-sans-alt">4003001111111</span>'
            '<span class="s1-subtitle">4003002222222</span>'
        )
        assert extraer_tarjeta(html_two_cards) == "4003001111111"

    def test_barcode_lookalike_preceding_authentic_card(self):
        """A foreign barcode lookalike before a valid card must not shadow the valid card."""
        html_lookalike_first = (
            '<div class="product-ean">Barcode: 8410000000000</div>'
            '<div class="loyalty-card"><span class="sana-sans-alt">4003009301402</span></div>'
        )
        assert extraer_tarjeta(html_lookalike_first) == "4003009301402"

    @pytest.mark.parametrize("falsy_or_weird_input", [
        None,
        "",
        "   \t\n   ",
        1234567890123,
        ["4003009301402"],
        {"card": "4003009301402"},
        b"4003009301402",
    ])
    def test_falsy_and_non_string_types_safe_exit(self, falsy_or_weird_input):
        """Non-string or falsy input must return None without raising uncaught exceptions."""
        assert extraer_tarjeta(falsy_or_weird_input) is None

    def test_large_html_performance_no_catastrophic_backtracking(self):
        """A 1 MB HTML string with nested brackets must not cause catastrophic regex backtracking."""
        filler = "<div><span><span>No card here</span></span></div>\n" * 20000
        html_large = filler + '<span class="sana-sans-alt">4003009301402</span>' + filler
        start = time.time()
        res = extraer_tarjeta(html_large)
        duration = time.time() - start
        assert res == "4003009301402"
        assert duration < 2.0, f"Extraction took too long: {duration:.3f}s"


# ==============================================================================
# 2. ADVERSARIAL STRESS-TESTS FOR _verify_and_hydrate_session
# ==============================================================================

class TestVerifyAndHydrateSessionAdversarial:
    """Empirical verification of Dual-Layer session hydration with simulated DOMs."""

    def test_capa1_positive_balance_must_not_call_capa2(self):
        """Requirement: If Capa 1 returns positive balance, Capa 2 must NOT be called."""
        # Even if page contains loyalty-manage-button and error banner, positive balance takes precedence!
        dom_capa1_positive = (
            '<html><body>'
            '<span class="_text_cn5lb_1">Tu Saldo es 3,50 €</span>'
            '<a href="https://www.miportal.alcampo.es/es/cuenta/fidelidad" data-test="loyalty-manage-button">'
            'settings.loyalty.manage.alternative: Parece que hay algo que no va bien.'
            '</a>'
            '<span class="sana-sans-alt">4003009301402</span>'
            '</body></html>'
        )
        driver = MockAdversarialDriver(
            initial_url="https://www.compraonline.alcampo.es/settings/loyalty",
            initial_html=dom_capa1_positive
        )

        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.5, email="test@test.es")

        assert saldo == "Tu Saldo es 3,50 €"
        assert tarjeta == "4003009301402"
        # Verify driver.get was NOT called to navigate to Capa 2
        assert len(driver.get_history) == 0, f"Capa 2 was unexpectedly called: {driver.get_history}"
        assert driver.refresh_called == 0

    def test_capa1_zero_balance_with_alternative_banner_must_call_capa2(self):
        """Requirement: If Capa 1 returns 0,00 € with alternative banner, Capa 2 MUST be called."""
        oauth_target = "https://ar-customerdiamond-es.my.site.com/services/oauth2/authorize?destination=fidelidad"
        dom_capa1_zero_degraded = (
            '<html><body>'
            '<span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span>'
            f'<a href="{oauth_target}" data-test="loyalty-manage-button" '
            'aria-label="Parece que hay algo que no va bien. Ahora no es posible que utilices el saldo.">'
            '<span>Mi cuenta Club Alcampo</span></a>'
            '</body></html>'
        )
        dom_capa2_miportal = (
            '<html><body>'
            '<span> Saldo disponible </span>'
            '<span class="h4-headline sana-sans-alt"><span>3,00&nbsp;€</span></span>'
            '<span class="sana-sans-alt"> 4003009301402 </span>'
            '<div value="?clif=4003009301402"><canvas></canvas></div>'
            '</body></html>'
        )

        driver = MockAdversarialDriver(
            initial_url="https://www.compraonline.alcampo.es/settings/loyalty",
            initial_html=dom_capa1_zero_degraded
        )
        driver.page_source_map[oauth_target] = dom_capa2_miportal

        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.5, email="test_zero@test.es")

        # Must have navigated to Capa 2 target
        assert len(driver.get_history) >= 1
        assert driver.get_history[0] == oauth_target
        # Must have extracted genuine balance from Capa 2
        assert saldo == "Tu Saldo es 3,00 €"
        assert tarjeta == "4003009301402"

    def test_capa2_navigation_timeout_exception_degrades_gracefully(self):
        """Requirement: If Capa 2 navigation raises TimeoutException, must degrade gracefully."""
        dom_capa1_zero_degraded = (
            '<html><body>'
            '<span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span>'
            '<a href="https://www.miportal.alcampo.es/es/cuenta/fidelidad" data-test="loyalty-manage-button">'
            'settings.loyalty.manage.alternative'
            '</a>'
            '</body></html>'
        )
        driver = MockAdversarialDriver(
            initial_url="https://www.compraonline.alcampo.es/settings/loyalty",
            initial_html=dom_capa1_zero_degraded
        )
        # Simulate network timeout when navigating to Capa 2
        driver.get_side_effect = TimeoutException("Timed out waiting for page load in Capa 2")

        # Must NOT raise TimeoutException out of _verify_and_hydrate_session
        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.2, email="timeout@test.es")

        # Should degrade gracefully to original Capa 1 result
        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta is None

    def test_capa2_navigation_webdriver_exception_degrades_gracefully(self):
        """If Capa 2 navigation raises generic WebDriverException, must degrade gracefully."""
        dom_capa1_zero_degraded = (
            '<html><body>'
            '<span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span>'
            '<div data-test="loyalty-manage-button">settings.loyalty.manage.alternative</div>'
            '</body></html>'
        )
        driver = MockAdversarialDriver(
            initial_url="https://www.compraonline.alcampo.es/settings/loyalty",
            initial_html=dom_capa1_zero_degraded
        )
        driver.get_side_effect = WebDriverException("net::ERR_NAME_NOT_RESOLVED")

        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.2, email="dns_err@test.es")

        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta is None

    def test_capa2_polling_times_out_without_saldo_disponible_degrades_gracefully(self):
        """If Capa 2 loads but never renders 'Saldo disponible', extraction degrades without crash."""
        dom_capa1_zero_degraded = (
            '<html><body>'
            '<span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span>'
            '<a href="https://www.miportal.alcampo.es/es/cuenta/fidelidad" data-test="loyalty-manage-button">'
            'settings.loyalty.manage.alternative'
            '</a>'
            '</body></html>'
        )
        dom_capa2_blank_or_error = (
            '<html><body><p>Portal temporalmente en mantenimiento</p></body></html>'
        )
        driver = MockAdversarialDriver(
            initial_url="https://www.compraonline.alcampo.es/settings/loyalty",
            initial_html=dom_capa1_zero_degraded
        )
        driver.page_source_map["https://www.miportal.alcampo.es/es/cuenta/fidelidad"] = dom_capa2_blank_or_error

        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.3, email="poll_timeout@test.es")

        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta is None

    def test_legitimate_zero_balance_without_degradation_does_not_call_capa2(self):
        """A verified 0,00 € account with a card and without alternative banner must not call Capa 2."""
        dom_clean_zero = (
            '<html><body>'
            '<span class="_text_cn5lb_1">Tu Saldo es 0,00 €</span>'
            '<span class="sana-sans-alt">4003009301402</span>'
            '</body></html>'
        )
        driver = MockAdversarialDriver(
            initial_url="https://www.compraonline.alcampo.es/settings/loyalty",
            initial_html=dom_clean_zero
        )

        saldo, tarjeta = _verify_and_hydrate_session(driver, timeout_s=0.5, email="clean_zero@test.es")

        assert saldo == "Tu Saldo es 0,00 €"
        assert tarjeta == "4003009301402"
        # No Capa 2 navigation triggered
        assert len(driver.get_history) == 0
