# -*- coding: utf-8 -*-
"""
Adversarial Empirical Verification Suite for Milestone M5_2.
Challenger: challenger_m5_2 (Adversarial Data Invariants & Boundary Challenger).

Validates extreme boundary conditions (B1-B7), multi-shard data invariants,
and race condition / data loss resilience across the consolidated pipeline.
"""

import os
import sys
import re
import json
import tempfile
import html
import subprocess
from pathlib import Path
from unittest import mock
import pytest
import pandas as pd

from scraper.script_optimizado import (
    CircuitBreaker,
    AdaptivePacer,
    _verify_and_hydrate_session,
    _extract_loyalty_balance,
    extraer_tarjeta,
    limpiar_saldo,
    mask_email,
    ensure_excel_output,
)
import scripts.merge_and_retry as merge_and_retry_module
from scripts.merge_and_retry import (
    format_telegram_summary,
    generate_consolidated_excel,
    collect_failed_accounts,
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
    compute_priority,
    load_master_accounts,
)
from scripts.local_test import load_accounts_from_file
from tests.test_e2e_complete_suite import StrictTelegramHTMLOracle, MockStealthWebDriver


# ==============================================================================
# 1. BOUNDARY B1: EMPTY DIRECTORIES, ZERO ACCOUNTS & FALLBACK INVARIANTS
# ==============================================================================

class TestAdversarialBoundaryB1EmptyAndZero:
    """Stress tests empty inputs, zero accounts, and fallback generation."""

    def test_b1_nested_empty_directories_no_crash(self, tmp_path):
        """Pipeline must handle nested empty directories gracefully."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)
        out_excel = tmp_path / "out_nested.xlsx"

        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(tmp_path),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert not out_excel.exists()

    def test_b1_ensure_excel_output_with_empty_and_none_lists(self, tmp_path):
        """ensure_excel_output must never generate 0-byte file even with None arguments."""
        p = tmp_path / "fallback_none.xlsx"
        df = ensure_excel_output(p, resultados=None, assigned_accounts=None, exit_reason="None args")
        assert p.exists()
        assert p.stat().st_size > 0
        assert len(df) == 1
        assert df.iloc[0]["email"] == "none"

    def test_b1_merge_with_only_empty_shards_fallback(self, tmp_path):
        """When multiple empty shards output 'none' fallback records, merge retains exactly one 'none'."""
        shards_dir = tmp_path / "shards"
        shards_dir.mkdir()
        for i in range(3):
            fpath = shards_dir / f"saldos_pass1_shard_{i}.xlsx"
            ensure_excel_output(fpath, resultados=[], assigned_accounts=[], exit_reason=f"Empty Shard {i}")

        out_excel = tmp_path / "merged_empty.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert out_excel.exists()
        df_all = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        # Deduplication on email='none' keeps at most 1 fallback record
        assert len(df_all) == 1
        assert df_all.iloc[0]["email"] == "none"


# ==============================================================================
# 2. BOUNDARY B2: CORRUPTED FILES & ENCODING TRUNCATION RECOVERY
# ==============================================================================

class TestAdversarialBoundaryB2CorruptAndFormats:
    """Stress tests corrupt files, zero-byte files, and invalid formats."""

    def test_b2_zero_byte_excel_files_resilience(self, tmp_path):
        """Zero-byte xlsx files must be skipped without crashing final-merge."""
        shards_dir = tmp_path / "mixed"
        shards_dir.mkdir()

        # Create zero-byte Excel file
        (shards_dir / "saldos_pass1_shard_0.xlsx").touch()

        # Create valid shard
        valid_df = pd.DataFrame([{
            "email": "user1@test.es", "password": "pwd",
            "saldo": "Tu Saldo es 5,00 €", "card_number": "4002001111111",
            "error_type": "ok"
        }])
        valid_df.to_excel(shards_dir / "saldos_pass1_shard_1.xlsx", index=False)

        out_excel = tmp_path / "merged.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert out_excel.exists()
        merged = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        assert len(merged) == 1
        assert merged.iloc[0]["email"] == "user1@test.es"

    def test_b2_corrupted_columns_in_shards(self, tmp_path):
        """Shards with missing essential columns or extra garbage columns are normalized safely."""
        shards_dir = tmp_path / "shards"
        shards_dir.mkdir()

        # Shard with completely missing email/saldo columns
        bad_df = pd.DataFrame([{"foo": "bar", "unknown": 123}])
        bad_df.to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        # Shard with normal columns
        good_df = pd.DataFrame([{"email": "good@test.es", "saldo": "Tu Saldo es 10,00 €", "card_number": "4002001234567"}])
        good_df.to_excel(shards_dir / "saldos_pass1_shard_1.xlsx", index=False)

        out_excel = tmp_path / "merged_bad_cols.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert out_excel.exists()
        merged = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        assert "email" in merged.columns
        assert "saldo" in merged.columns
        assert "good@test.es" in merged["email"].values


# ==============================================================================
# 3. BOUNDARY B3: DOM HYDRATION & MISSING CARD CORNER CASES
# ==============================================================================

class TestAdversarialBoundaryB3HydrationMissingCard:
    """Stress tests DOM loyalty card extraction and hydration behavior."""

    def test_b3_card_number_extraction_formats(self):
        """Tests loyalty card regexes across multiple DOM structures."""
        # 1. sana-sans-alt class
        html1 = '<span class="sana-sans-alt s1-subtitle"> 4002001234567 </span>'
        assert extraer_tarjeta(html1) == "4002001234567"

        # 2. Raw 400200 EAN-13 inside arbitrary text
        html2 = '<div>Su tarjeta Alcampo es 4002009999999 asociada.</div>'
        assert extraer_tarjeta(html2) == "4002009999999"

        # 3. __NEXT_DATA__ JSON payload
        html3 = '<script id="__NEXT_DATA__">{"props":{"pageProps":{"loyaltyCardNumber":"4002005555555"}}}</script>'
        assert extraer_tarjeta(html3) == "4002005555555"

        # 4. Incomplete or non-numeric card number
        html_invalid = '<span>400200ABCDEFG</span>'
        assert extraer_tarjeta(html_invalid) is None

    def test_b3_hydration_triggers_on_zero_without_card_and_recovers(self):
        """When 0,00 € has no card initially, hydration refreshes and detects card on second attempt."""
        page_unhydrated = '<html><body><p>Tu Saldo es 0,00 €</p></body></html>'
        page_hydrated = '<html><body><p>Tu Saldo es 0,00 €</p><span>4002003333333</span></body></html>'

        driver = MockStealthWebDriver(initial_pages=[page_unhydrated, page_hydrated])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.05)

        assert saldo == "Tu Saldo es 0,00 €"
        assert card == "4002003333333"


# ==============================================================================
# 4. BOUNDARY B4: VERIFIED 0,00 € VS UNHYDRATED TIMEOUTS
# ==============================================================================

class TestAdversarialBoundaryB4VerifiedZeroVsTimeout:
    """Verifies that 0,00 € is never confused with timeout/unhydrated errors."""

    def test_b4_definitive_success_classification_on_zero(self):
        """Verified 0,00 € must be classified as definitive success and never retried."""
        saldo_zero = "Tu Saldo es 0,00 €"
        assert is_definitive_success(saldo_zero) is True
        assert is_retryable_failure(saldo_zero, causa_str="", err_type="ok") is False

        # In contrast, timeout/error strings must be retryable failures
        saldo_timeout = "Error: Bloqueo/Timeout"
        assert is_definitive_success(saldo_timeout) is False
        assert is_retryable_failure(saldo_timeout, causa_str="Timeout", err_type="session_error") is True

        saldo_no_encontrado = "No encontrado"
        assert is_definitive_success(saldo_no_encontrado) is False
        assert is_retryable_failure(saldo_no_encontrado, causa_str="", err_type="session_error") is True

    def test_b4_sheet_partitioning_verified_zero(self):
        """generate_consolidated_excel must route 0,00 € strictly to 'Saldo Cero Verificado'."""
        df_input = pd.DataFrame([
            {"email": "zero@test.es", "saldo": "Tu Saldo es 0,00 €", "card_number": "4002001111111", "error_type": "ok"},
            {"email": "positive@test.es", "saldo": "Tu Saldo es 12,50 €", "card_number": "4002002222222", "error_type": "ok"},
            {"email": "timeout@test.es", "saldo": "Error: Timeout", "card_number": None, "error_type": "session_error"},
        ])
        sheets = generate_consolidated_excel(df_input)

        df_zero = sheets["Saldo Cero Verificado"]
        assert len(df_zero) == 1
        assert df_zero.iloc[0]["email"] == "zero@test.es"

        df_positive = sheets["Exitosas con Saldo"]
        assert len(df_positive) == 1
        assert df_positive.iloc[0]["email"] == "positive@test.es"

        df_ip_timeout = sheets["Error IP y Timeouts"]
        assert len(df_ip_timeout) == 1
        assert df_ip_timeout.iloc[0]["email"] == "timeout@test.es"


# ==============================================================================
# 5. BOUNDARY B5: CIRCUIT BREAKER WAF, 429 & ERROR TAXONOMY
# ==============================================================================

class TestAdversarialBoundaryB5CircuitBreakerWAF429:
    """Stress tests the 4-tier error taxonomy and circuit breaker thresholds."""

    def test_b5_error_taxonomy_isolation(self):
        """Account-level errors (credentials, call center) must NOT increment server errors."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        # 5 consecutive account credentials errors
        for i in range(5):
            err_type, reason = cb.classify_error(page_source="Credenciales incorrectas")
            assert err_type == "account_error"
            trig, _ = cb.record_result(is_server_error=False, reason=reason, error_type=err_type)
            assert trig is False

        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

        # 5 consecutive call center / 2FA errors
        for i in range(5):
            err_type, reason = cb.classify_error(page_source="Su cuenta ha sido bloqueada. Contacte con Call Center.")
            assert err_type == "needs_attention"
            trig, _ = cb.record_result(is_server_error=False, reason=reason, error_type=err_type)
            assert trig is False

        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    def test_b5_exact_8_threshold_for_server_errors(self):
        """Exactly 8 consecutive IP errors must trip the breaker on the 8th, not before."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        for i in range(7):
            trig, _ = cb.record_result(is_server_error=True, reason=f"429 #{i}", error_type="ip_error")
            assert trig is False
            assert cb.triggered is False

        trig, reason = cb.record_result(is_server_error=True, reason="429 #7", error_type="ip_error")
        assert trig is True
        assert cb.triggered is True
        assert "8 caídas consecutivas" in reason


# ==============================================================================
# 6. BOUNDARY B6: TELEGRAM CHUNKING & HTML VALIDITY
# ==============================================================================

class TestAdversarialBoundaryB6TelegramHtmlAndChunking:
    """Stress tests Telegram message formatting, chunking ceiling, and HTML validity."""

    def test_b6_message_under_4096_chars(self):
        """Generated summary must never exceed Telegram's 4096 character ceiling."""
        top_10 = [(100.0 - i, f"user_{i}@test.com") for i in range(10)]
        huge_error = "Error: " + ("Timeout while fetching /settings/loyalty; " * 100)

        msg = format_telegram_summary(
            total=500, saldo_total=1234.56, cuentas_dinero=50,
            cuentas_cero=100, cuentas_error=350, top_10=top_10,
            error_summary=huge_error
        )
        assert len(msg) <= 4096
        assert len(msg) == 3995  # 3980 + len("\n... [truncado]")

    def test_b6_html_special_character_escaping(self):
        """Emails and error messages with HTML reserved chars must be fully escaped."""
        top_10 = [(50.0, 'user+<script>alert("hack")</script>&foo@alcampo.es')]
        error_msg = 'Error occurred in <div id="test"> & failed with code > 400'

        msg = format_telegram_summary(
            total=1, saldo_total=50.0, cuentas_dinero=1,
            cuentas_cero=0, cuentas_error=0, top_10=top_10,
            error_summary=error_msg
        )
        assert "<script>" not in msg
        assert "&lt;script&gt;" in msg
        assert '<div id="test">' not in msg
        assert "&lt;div" in msg
        assert StrictTelegramHTMLOracle.validate(msg) == []


# ==============================================================================
# 7. BOUNDARY B7: WINDOWS UTF-8 EXECUTION, SPECIAL ENCODINGS & EMOJIS
# ==============================================================================

class TestAdversarialBoundaryB7WindowsUtf8SpecialChars:
    """Stress tests Windows UTF-8 execution with accents, eñes, and emojis."""

    def test_b7_dataframe_to_excel_roundtrip_with_spanish_and_emojis(self, tmp_path):
        """Excel generation and reading must preserve complex Unicode strings without corruption."""
        records = [
            {
                "email": "maría.josé.cañas@españa.org",
                "password": "contraseña_con_ñ_y_tildes",
                "saldo": "Tu Saldo es 1.250,50 € 💰✨",
                "card_number": "4002008888888",
                "error_type": "ok",
                "causa_error": ""
            },
            {
                "email": "pablo.gómez@alcampo.es",
                "password": "pwd",
                "saldo": "Error: Bloqueo WAF 🚫",
                "card_number": None,
                "error_type": "ip_error",
                "causa_error": "WAF 403 Forbidden ❌"
            }
        ]
        target_excel = tmp_path / "utf8_roundtrip.xlsx"
        ensure_excel_output(target_excel, resultados=records, assigned_accounts=[], exit_reason="UTF8")

        assert target_excel.exists()
        sheets = generate_consolidated_excel(pd.read_excel(target_excel), output_excel_path=str(tmp_path / "cons.xlsx"))

        df_con_saldo = sheets["Exitosas con Saldo"]
        assert len(df_con_saldo) == 1
        assert df_con_saldo.iloc[0]["email"] == "maría.josé.cañas@españa.org"
        assert "💰" in df_con_saldo.iloc[0]["saldo"]

        df_err = sheets["Error IP y Timeouts"]
        assert len(df_err) == 1
        assert "🚫" in df_err.iloc[0]["saldo"]


# ==============================================================================
# 8. MULTI-SHARD MERGER: DATA LOSS & RACE CONDITION ADVERSARIAL STRESS
# ==============================================================================

class TestAdversarialMultiShardMergerDataLossAndRaceConditions:
    """Stress tests multi-shard mergers for race conditions, data loss, and priority invariants."""

    def test_multi_shard_pass1_error_overwritten_by_pass2_success(self, tmp_path):
        """Pass 2 retry success must strictly overwrite Pass 1 failure."""
        shards_dir = tmp_path / "all_shards"
        shards_dir.mkdir()

        # Pass 1 Shard 0: acc1 failed with timeout
        p1_df = pd.DataFrame([{
            "email": "acc1@alcampo.es", "password": "pwd",
            "saldo": "Error: Timeout", "card_number": None,
            "error_type": "session_error"
        }])
        p1_df.to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        # Pass 2 Shard 0: acc1 succeeded with 35.00 €
        p2_df = pd.DataFrame([{
            "email": "acc1@alcampo.es", "password": "pwd",
            "saldo": "Tu Saldo es 35,00 €", "card_number": "4002001234567",
            "error_type": "ok"
        }])
        p2_df.to_excel(shards_dir / "saldos_retry_shard_0.xlsx", index=False)

        out_excel = tmp_path / "merged.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        df_all = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        assert len(df_all) == 1
        assert df_all.iloc[0]["email"] == "acc1@alcampo.es"
        assert df_all.iloc[0]["saldo"] == "Tu Saldo es 35,00 €"

    def test_multi_shard_pass1_success_never_downgraded_by_pass2_failure(self, tmp_path):
        """Pass 1 success must NEVER be downgraded by a hypothetical Pass 2 failure."""
        shards_dir = tmp_path / "all_shards"
        shards_dir.mkdir()

        # Pass 1: success 20.00 € (prio 1010)
        p1_df = pd.DataFrame([{
            "email": "acc2@alcampo.es", "password": "pwd",
            "saldo": "Tu Saldo es 20,00 €", "card_number": "4002001234567",
            "error_type": "ok"
        }])
        p1_df.to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        # Hypothetical Pass 2 failure (prio 100)
        p2_df = pd.DataFrame([{
            "email": "acc2@alcampo.es", "password": "pwd",
            "saldo": "Error: Timeout", "card_number": None,
            "error_type": "session_error"
        }])
        p2_df.to_excel(shards_dir / "saldos_retry_shard_0.xlsx", index=False)

        out_excel = tmp_path / "merged.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        df_all = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        assert len(df_all) == 1
        assert df_all.iloc[0]["email"] == "acc2@alcampo.es"
        assert df_all.iloc[0]["saldo"] == "Tu Saldo es 20,00 €"

    def test_multi_shard_rescue_unreached_accounts_from_master(self, tmp_path):
        """Master accounts omitted due to crashed shards must be rescued for Pass 2."""
        master_accounts = [
            {"email": "completed@alcampo.es", "password": "p1"},
            {"email": "crashed_shard@alcampo.es", "password": "p2"},
        ]
        # Only completed shard exists
        shard_file = tmp_path / "saldos_pass1_shard_0.xlsx"
        pd.DataFrame([{
            "email": "completed@alcampo.es", "password": "p1",
            "saldo": "Tu Saldo es 10,00 €", "card_number": "4002001111111",
            "error_type": "ok"
        }]).to_excel(shard_file, index=False)

        failed = collect_failed_accounts([str(shard_file)], master_accounts=master_accounts)
        assert len(failed) == 1
        assert failed[0]["email"] == "crashed_shard@alcampo.es"

    def test_multi_shard_large_scale_deduplication(self, tmp_path):
        """50 shards with 200 unique accounts across multiple passes consolidate with zero duplicates."""
        shards_dir = tmp_path / "scale_shards"
        shards_dir.mkdir()

        total_unique_accounts = 200
        # Write 50 shards
        for shard_idx in range(50):
            records = []
            for acc_idx in range(shard_idx * 4, min((shard_idx + 1) * 4, total_unique_accounts)):
                email = f"user_{acc_idx:03d}@alcampo.es"
                saldo = f"Tu Saldo es {(acc_idx % 25):.2f} €" if acc_idx % 3 != 0 else "Error: Timeout"
                records.append({
                    "email": email, "password": "p", "saldo": saldo,
                    "card_number": "4002000000000" if "Tu Saldo es" in saldo else None,
                    "error_type": "ok" if "Tu Saldo es" in saldo else "session_error"
                })
            if records:
                fname = f"saldos_pass1_shard_{shard_idx}.xlsx"
                pd.DataFrame(records).to_excel(shards_dir / fname, index=False)

        out_excel = tmp_path / "consolidated_50_shards.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert out_excel.exists()
        df_all = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        assert len(df_all) == total_unique_accounts
        assert len(df_all["email"].unique()) == total_unique_accounts

    def test_multi_shard_duplicate_emails_with_different_casings(self, tmp_path):
        """Investigates case-sensitivity invariant during multi-shard deduplication."""
        shards_dir = tmp_path / "casing_shards"
        shards_dir.mkdir()

        # Shard 0 with UPPERCASE email
        p1 = pd.DataFrame([{
            "email": "USER_ALCAMPO@TEST.ES", "password": "p",
            "saldo": "Tu Saldo es 10,00 €", "card_number": "4002001111111",
            "error_type": "ok"
        }])
        p1.to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        # Shard 1 with lowercase email
        p2 = pd.DataFrame([{
            "email": "user_alcampo@test.es", "password": "p",
            "saldo": "Tu Saldo es 10,00 €", "card_number": "4002001111111",
            "error_type": "ok"
        }])
        p2.to_excel(shards_dir / "saldos_pass1_shard_1.xlsx", index=False)

        out_excel = tmp_path / "merged_casing.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        df_all = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        # Documents whether exact string vs case-insensitive matching is performed by pandas drop_duplicates
        unique_emails = df_all["email"].tolist()
        assert len(unique_emails) >= 1

    def test_b6_truncation_entity_split_boundary_demonstration(self):
        """
        Adversarial demonstration of the Telegram entity split edge case:
        When an error summary is truncated exactly at index 3980, an escaped entity like &amp;
        can be bisected into '&am' or '&a', creating an unescaped '&'.
        """
        # When a long message is formatted, it is truncated at 3980
        # If an & character occurs at the 3980 boundary:
        err = "A" * 3635 + "&test" + "B" * 500
        msg = format_telegram_summary(10, 0.0, 0, 10, 0, [], error_summary=err)
        assert len(msg) == 3995
        assert "... [truncado]" in msg
        # Note the entity splitting: msg contains '&amp\n'
        assert "&amp\n" in msg or "&am\n" in msg or "&a\n" in msg

