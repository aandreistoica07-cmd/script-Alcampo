"""
Unit tests for scraper utilities: limpiar_saldo, extraer_tarjeta, and mask_email.
Tests run in-memory with zero external Chrome or network dependencies.
"""

import sys
from unittest import mock
import pytest
import pandas as pd
from scraper.script_optimizado import (
    limpiar_saldo,
    extraer_tarjeta,
    mask_email,
    ensure_excel_output,
    _verify_and_hydrate_session,
    parse_args,
)


class TestLimpiarSaldo:
    """Test suite for balance cleaning and currency normalization."""

    def test_standard_euro_format_with_comma(self):
        assert limpiar_saldo("Tu Saldo es 12,50 €") == 12.50
        assert limpiar_saldo("Saldo disponible: 5,99 €") == 5.99

    def test_euro_format_with_dot(self):
        assert limpiar_saldo("Saldo: 25.80 €") == 25.80

    def test_zero_euro_balance(self):
        assert limpiar_saldo("0,00 €") == 0.0
        assert limpiar_saldo("0.00 €") == 0.0
        assert limpiar_saldo("0 €") == 0.0
        assert limpiar_saldo("Tu Saldo es 0,00 €") == 0.0

    def test_integer_balance(self):
        assert limpiar_saldo("Saldo: 100 €") == 100.0

    def test_error_and_not_found_strings(self):
        assert limpiar_saldo("Error: Bloqueo/Timeout") is None
        assert limpiar_saldo("No encontrado") is None
        assert limpiar_saldo("Error: Credenciales no válidas") is None

    def test_empty_and_none_inputs(self):
        assert limpiar_saldo(None) is None
        assert limpiar_saldo("") is None
        assert limpiar_saldo("   ") is None

    def test_string_without_digits(self):
        assert limpiar_saldo("Saldo no disponible temporalmente") is None


class TestExtraerTarjeta:
    """Test suite for Alcampo 13-digit loyalty card extraction from HTML."""

    def test_extract_from_sana_sans_class(self):
        html = '<div class="card-info"><span class="sana-sans-alt"> 4002001234567 </span></div>'
        assert extraer_tarjeta(html) == "4002001234567"

    def test_extract_from_s1_subtitle_class(self):
        html = '<span class="s1-subtitle main-text"> 4002009876543 </span>'
        assert extraer_tarjeta(html) == "4002009876543"

    def test_extract_from_prefix_regex(self):
        html = '<p>El número de tarjeta asociado es 4002007654321 en tu cuenta Club Alcampo.</p>'
        assert extraer_tarjeta(html) == "4002007654321"

    def test_extract_from_next_data_json(self):
        html = '<script id="__NEXT_DATA__">{"props":{"pageProps":{"loyaltyCardNumber":"4002005555555"}}}</script>'
        assert extraer_tarjeta(html) == "4002005555555"

    def test_extract_from_barcode_json(self):
        html = '<div><script>{"barcode": "4002009999999"}</script></div>'
        assert extraer_tarjeta(html) == "4002009999999"

    def test_no_card_found(self):
        assert extraer_tarjeta("<html><body>No loyalty card here</body></html>") is None
        assert extraer_tarjeta("") is None
        assert extraer_tarjeta(None) is None


class TestMaskEmail:
    """Test suite for PII email masking."""

    def test_standard_email_masking(self):
        assert mask_email("usuario@alcampo.es") == "us***o@alcampo.es"
        assert mask_email("alberto.garcia@gmail.com") == "al***a@gmail.com"

    def test_short_local_part(self):
        assert mask_email("ab@domain.com") == "a***@domain.com"
        assert mask_email("x@test.org") == "x***@test.org"

    def test_invalid_and_empty_inputs(self):
        assert mask_email("") == "***"
        assert mask_email(None) == "***"
        assert mask_email("not_an_email") == "***"


class TestEnsureExcelOutput:
    """Test suite for ensure_excel_output guaranteed output artifact creation."""

    def test_ensure_excel_output_partial_run_all_accounts_preserved(self, tmp_path):
        """When 10 accounts are assigned but only 3 processed before IP canary quarantine,
        ensure_excel_output generates an Excel file containing all 10 accounts, with 7
        marked with the exit reason and error_type."""
        assigned = [{"email": f"acc_{i}@alcampo.es", "password": f"pwd_{i}"} for i in range(10)]
        resultados = [
            {"email": "acc_0@alcampo.es", "password": "pwd_0", "saldo": "Tu Saldo es 18,50 €", "card_number": "4002001111111", "error_type": "ok", "total_s": 4.5},
            {"email": "acc_1@alcampo.es", "password": "pwd_1", "saldo": "Tu Saldo es 0,00 €", "card_number": "4002002222222", "error_type": "ok", "total_s": 5.1},
            {"email": "acc_2@alcampo.es", "password": "pwd_2", "saldo": "Error: Credenciales incorrectas", "card_number": None, "error_type": "account_error", "total_s": 3.2},
        ]

        target_file = tmp_path / "saldos_canary_test.xlsx"
        df_result = ensure_excel_output(target_file, resultados, assigned, exit_reason="Bloqueo Canario IP")

        assert target_file.exists(), "Excel file must be physically created on disk"
        df = pd.read_excel(target_file)
        assert len(df) == 10, "All 10 assigned accounts must be present in the Excel file"

        # Check first 3 processed accounts
        assert df.loc[df["email"] == "acc_0@alcampo.es", "saldo"].iloc[0] == "Tu Saldo es 18,50 €"
        assert df.loc[df["email"] == "acc_0@alcampo.es", "error_type"].iloc[0] == "ok"
        assert df.loc[df["email"] == "acc_1@alcampo.es", "saldo"].iloc[0] == "Tu Saldo es 0,00 €"
        assert df.loc[df["email"] == "acc_1@alcampo.es", "error_type"].iloc[0] == "ok"
        assert df.loc[df["email"] == "acc_2@alcampo.es", "saldo"].iloc[0] == "Error: Credenciales incorrectas"
        assert df.loc[df["email"] == "acc_2@alcampo.es", "error_type"].iloc[0] == "account_error"

        # Check 7 unprocessed accounts
        fallback_rows = df[df["email"].isin([f"acc_{i}@alcampo.es" for i in range(3, 10)])]
        assert len(fallback_rows) == 7
        assert (fallback_rows["saldo"] == "Error: Bloqueo Canario IP").all()
        assert (fallback_rows["error_type"] == "ip_error").all()

    def test_ensure_excel_output_non_ip_interruption_tags_session_error(self, tmp_path):
        assigned = [{"email": f"acc_{i}@alcampo.es", "password": f"pwd_{i}"} for i in range(5)]
        resultados = [
            {"email": "acc_0@alcampo.es", "password": "pwd_0", "saldo": "Tu Saldo es 7,00 €", "card_number": "4002003333333", "error_type": "ok", "total_s": 3.0}
        ]

        target_file = tmp_path / "saldos_shard_timeout.xlsx"
        ensure_excel_output(target_file, resultados, assigned, exit_reason="Interrupción Shard")

        df = pd.read_excel(target_file)
        assert len(df) == 5

        fallback_rows = df[df["email"].isin([f"acc_{i}@alcampo.es" for i in range(1, 5)])]
        assert len(fallback_rows) == 4
        assert (fallback_rows["saldo"] == "Error: Interrupción Shard").all()
        assert (fallback_rows["error_type"] == "session_error").all()

    def test_ensure_excel_output_zero_processed_accounts(self, tmp_path):
        assigned = [{"email": f"acc_{i}@alcampo.es", "password": f"pwd_{i}"} for i in range(4)]
        target_file = tmp_path / "saldos_zero.xlsx"
        ensure_excel_output(target_file, [], assigned, exit_reason="Bloqueo Canario IP")

        df = pd.read_excel(target_file)
        assert len(df) == 4
        assert (df["saldo"] == "Error: Bloqueo Canario IP").all()
        assert (df["error_type"] == "ip_error").all()

    def test_ensure_excel_output_completely_empty(self, tmp_path):
        target_file = tmp_path / "saldos_empty.xlsx"
        ensure_excel_output(target_file, [], [], exit_reason="Desconocido")

        df = pd.read_excel(target_file)
        assert len(df) == 1
        assert df["email"].iloc[0] == "none"
        assert df["error_type"].iloc[0] == "session_error"


class MockHydrationDriver:
    """Mock WebDriver to test _verify_and_hydrate_session logic without real Chrome."""
    def __init__(self, current_url="https://www.compraonline.alcampo.es/settings/loyalty", pages=None):
        self.current_url = current_url
        self.pages = pages or []
        self.page_idx = 0
        self.refresh_count = 0
        self.navigated_urls = []

    @property
    def page_source(self):
        if self.page_idx < len(self.pages):
            return self.pages[self.page_idx]
        return self.pages[-1] if self.pages else ""

    def refresh(self):
        self.refresh_count += 1
        if self.page_idx + 1 < len(self.pages):
            self.page_idx += 1

    def get(self, url):
        self.navigated_urls.append(url)
        self.current_url = url
        if self.page_idx + 1 < len(self.pages):
            self.page_idx += 1


class TestVerifyAndHydrateSessionAndCLIFlags:
    """Test suite for deep session hydration and CLI headless/headful flags."""

    def test_hydrate_immediate_valid_positive_balance_no_refresh(self):
        # When balance is > 0, it is not suspicious and returns immediately
        page = '<div><p>Tu Saldo es 12,50 €</p></div>'
        driver = MockHydrationDriver(pages=[page])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.5)
        assert saldo == "Tu Saldo es 12,50 €"
        assert card is None
        assert driver.refresh_count == 0
        assert driver.navigated_urls == []

    def test_hydrate_suspicious_zero_balance_recovers_after_refresh(self):
        # 1st read: 0,00 € without card (suspicious)
        # 2nd read (after refresh): 0,00 € with valid card
        p1 = '<div><p>Tu Saldo es 0,00 €</p></div>'
        p2 = '<div><p>Tu Saldo es 0,00 €</p><span class="sana-sans-alt">4002001234567</span></div>'
        driver = MockHydrationDriver(pages=[p1, p2])

        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.5)
        assert saldo == "Tu Saldo es 0,00 €"
        assert card == "4002001234567"
        assert driver.refresh_count == 1

    def test_hydrate_not_found_navigates_to_home_and_recovers(self):
        # 1st read: No balance found
        # 2nd read (after refresh): still not found
        # 3rd read (after home -> loyalty): balance and card recovered
        p1 = '<div><p>Cargando perfil...</p></div>'
        p2 = '<div><p>Cargando perfil...</p></div>'
        p3 = '<div><p>Tu Saldo es 25,00 €</p><span class="s1-subtitle">4002009876543</span></div>'
        driver = MockHydrationDriver(pages=[p1, p2, p3])

        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.5)
        assert saldo == "Tu Saldo es 25,00 €"
        assert card == "4002009876543"
        assert driver.refresh_count == 1
        assert "https://www.compraonline.alcampo.es/" in driver.navigated_urls
        assert "https://www.compraonline.alcampo.es/settings/loyalty" in driver.navigated_urls

    def test_cli_flags_headless_default_and_headful_variants(self):
        with mock.patch.object(sys, "argv", ["script_optimizado.py"]):
            args = parse_args()
            assert args.headless is True
            assert args.headful is False

        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headful"]):
            args = parse_args()
            assert args.headful is True

        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--visible"]):
            args = parse_args()
            assert args.headful is True


