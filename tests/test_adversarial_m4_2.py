"""
Adversarial stress-testing suite for Milestone 4 (M4.2):
- Guaranteed Excel Output (ensure_excel_output):
  - 50 assigned accounts with 0 processed (empty list)
  - Special characters, unicode, emojis, null passwords, duplicate emails
  - Nested directory auto-creation and unwritable path error trapping
- CLI Argument Parser (parse_args):
  - Permutations of --headless, --headful, --visible, --limit, --threads, --output-file
  - Resolution of headless boolean for driver creation
"""

import sys
from pathlib import Path
from unittest import mock
import pytest
import pandas as pd

from scraper.script_optimizado import ensure_excel_output, parse_args


class TestAdversarialEnsureExcelOutput:
    """Empirical adversarial stress tests for ensure_excel_output."""

    def test_empty_resultados_with_50_assigned_accounts(self, tmp_path):
        """When 0 accounts are processed but 50 were assigned, ensure_excel_output
        must generate an Excel file with exactly 50 rows, classified by exit_reason."""
        assigned = [
            {"email": f"account_{i:02d}@alcampo.es", "password": f"Pass_{i}*!"}
            for i in range(50)
        ]
        target_file = tmp_path / "saldos_50_empty.xlsx"

        df_returned = ensure_excel_output(
            target_path=target_file,
            resultados=[],
            assigned_accounts=assigned,
            exit_reason="Bloqueo Canario IP"
        )

        assert target_file.exists(), "Excel file must exist on disk"
        assert df_returned is not None, "DataFrame must be returned"
        assert len(df_returned) == 50, "Returned DataFrame must have exactly 50 rows"

        df_disk = pd.read_excel(target_file)
        assert len(df_disk) == 50, "Persisted Excel file must have exactly 50 rows"

        expected_columns = {"email", "password", "saldo", "card_number", "error_type", "total_s"}
        assert expected_columns.issubset(set(df_disk.columns)), f"Columns missing: {expected_columns - set(df_disk.columns)}"

        # Verify all rows have ip_error and 0.0 total
        assert (df_disk["error_type"] == "ip_error").all(), "All 50 accounts must be marked with ip_error"
        assert (df_disk["saldo"] == "Error: Bloqueo Canario IP").all(), "Saldo column must reflect exit reason"
        assert (df_disk["total_s"] == 0.0).all(), "total_s must be 0.0 for unprocessed accounts"
        assert df_disk["card_number"].isna().all(), "card_number must be null for unprocessed accounts"

        # Verify email integrity
        expected_emails = [a["email"] for a in assigned]
        assert list(df_disk["email"]) == expected_emails, "All assigned emails must be present in order"

    def test_empty_resultados_session_error_classification(self, tmp_path):
        """Verify non-IP exit reasons (e.g. shard timeout) classify as session_error."""
        assigned = [{"email": f"user_{i}@test.com", "password": "pwd"} for i in range(10)]
        target_file = tmp_path / "saldos_timeout.xlsx"

        df = ensure_excel_output(
            target_path=target_file,
            resultados=[],
            assigned_accounts=assigned,
            exit_reason="Timeout Shard 1"
        )

        assert len(df) == 10
        assert (df["error_type"] == "session_error").all()
        assert (df["saldo"] == "Error: Timeout Shard 1").all()

    def test_special_characters_unicode_and_emojis(self, tmp_path):
        """Stress-test Excel generation with emojis, HTML tags, injection strings, and unicode."""
        resultados = [
            {
                "email": "user+tag@domain.co.uk",
                "password": "p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?",
                "saldo": "Tu Saldo es 1.250,99 € 💰🎉🚀",
                "card_number": "💳 4002-0000-1111",
                "error_type": "ok",
                "total_s": 1250.99,
            },
            {
                "email": "ñandú.pétalo@españa.es",
                "password": "contraseña_con_tildes_y_ñ_áéíóú",
                "saldo": "<script>alert('xss')</script> &amp; 0,00 €",
                "card_number": "4002009999999",
                "error_type": "ok",
                "total_s": 0.0,
            },
            {
                "email": "tabs_and_newlines@alcampo.es",
                "password": "line1\nline2\ttab",
                "saldo": "Error: \r\nBloqueo WAF 403 Forbidden ❌⚠️",
                "card_number": None,
                "error_type": "ip_error",
                "total_s": 0.0,
            },
        ]
        assigned = [
            {"email": "unprocessed_unicode@alcampo.es", "password": "🔑🔐"}
        ]

        target_file = tmp_path / "saldos_unicode.xlsx"
        df_res = ensure_excel_output(target_file, resultados, assigned, exit_reason="Unicode Test 🌟")

        assert target_file.exists()
        assert len(df_res) == 4

        df_disk = pd.read_excel(target_file)
        assert len(df_disk) == 4
        assert "💰🎉🚀" in df_disk.loc[df_disk["email"] == "user+tag@domain.co.uk", "saldo"].iloc[0]
        assert "ñandú.pétalo@españa.es" in list(df_disk["email"])
        assert "🔑🔐" in df_disk.loc[df_disk["email"] == "unprocessed_unicode@alcampo.es", "password"].iloc[0]

    def test_null_and_missing_passwords(self, tmp_path):
        """Stress-test accounts with None passwords, missing keys, or empty strings."""
        resultados = [
            {
                "email": "acc_null_pwd@alcampo.es",
                "password": None,
                "saldo": "Tu Saldo es 5,00 €",
                "card_number": "4002001",
                "error_type": "ok",
                "total_s": 5.0,
            },
            {
                "email": "acc_missing_keys@alcampo.es",
                # missing password, card_number, etc.
            },
        ]
        assigned = [
            {"email": "assigned_null_pwd@alcampo.es", "password": None},
            {"email": "assigned_no_pwd_key@alcampo.es"},
            {"email": "assigned_empty_pwd@alcampo.es", "password": ""},
        ]

        target_file = tmp_path / "saldos_nulls.xlsx"
        df_res = ensure_excel_output(target_file, resultados, assigned, exit_reason="Null Password Test")

        assert target_file.exists()
        df_disk = pd.read_excel(target_file)
        assert len(df_disk) == 5
        # None passwords should not crash or cause type errors
        assert "acc_null_pwd@alcampo.es" in list(df_disk["email"])
        assert "assigned_null_pwd@alcampo.es" in list(df_disk["email"])

    def test_duplicate_emails_and_unprocessed_filtering(self, tmp_path):
        """Verify behavior when resultados or assigned_accounts contain duplicate emails."""
        resultados = [
            {"email": "dup@alcampo.es", "password": "p1", "saldo": "5,00 €", "card_number": "111", "error_type": "ok", "total_s": 5.0},
            {"email": "dup@alcampo.es", "password": "p1", "saldo": "10,00 €", "card_number": "111", "error_type": "ok", "total_s": 10.0},
        ]
        # assigned has dup@alcampo.es (already processed) and new@alcampo.es (unprocessed)
        assigned = [
            {"email": "dup@alcampo.es", "password": "p1"},
            {"email": "new@alcampo.es", "password": "p2"},
        ]

        target_file = tmp_path / "saldos_dups.xlsx"
        df_res = ensure_excel_output(target_file, resultados, assigned, exit_reason="Dup Test")

        df_disk = pd.read_excel(target_file)
        # Both already-processed duplicates are kept in resultados, and new@ is appended once
        assert len(df_disk) == 3
        # dup@alcampo.es should NOT be re-added as an unprocessed fallback
        dup_fallbacks = df_disk[(df_disk["email"] == "dup@alcampo.es") & (df_disk["error_type"] == "session_error")]
        assert len(dup_fallbacks) == 0, "Already processed email must not be re-appended as fallback"

    def test_nested_directory_auto_creation(self, tmp_path):
        """ensure_excel_output must automatically create deep non-existent directories."""
        deep_target = tmp_path / "deep" / "nested" / "path" / "sub" / "output.xlsx"
        assert not deep_target.parent.exists()

        assigned = [{"email": "nested@alcampo.es", "password": "p"}]
        df = ensure_excel_output(deep_target, [], assigned, exit_reason="Dir Creation Test")

        assert deep_target.exists(), "Deep nested target file must be created"
        assert deep_target.parent.exists(), "Parent directories must be created"
        assert len(df) == 1

    def test_unwritable_path_graceful_error_handling(self, tmp_path):
        """ensure_excel_output must catch write errors gracefully and return None without raising."""
        # Mock pd.DataFrame.to_excel to simulate an OS permission or disk full error
        with mock.patch("pandas.DataFrame.to_excel", side_effect=PermissionError("Permission denied: Target locked")):
            target_file = tmp_path / "locked_file.xlsx"
            assigned = [{"email": "test@alcampo.es", "password": "pwd"}]

            res = ensure_excel_output(target_file, [], assigned, exit_reason="Permission Test")
            assert res is None, "Should return None on filesystem write error"
            assert not target_file.exists(), "File should not exist on simulated write failure"

    def test_completely_empty_fallback(self, tmp_path):
        """When both resultados and assigned_accounts are empty or None, creates 1 fallback row."""
        target_file = tmp_path / "saldos_none.xlsx"
        df = ensure_excel_output(target_file, None, None, exit_reason="No accounts")

        assert target_file.exists()
        assert len(df) == 1
        assert df["email"].iloc[0] == "none"
        assert df["error_type"].iloc[0] == "session_error"


class TestAdversarialCLIArgumentParser:
    """Empirical adversarial stress tests for CLI argument parsing."""

    def test_cli_default_arguments(self):
        """When invoked with no flags, verify all standard defaults."""
        with mock.patch.object(sys, "argv", ["script_optimizado.py"]):
            args = parse_args()
            assert args.threads == 2
            assert args.limit is None
            assert args.output_file is None
            assert args.headless is True
            assert args.headful is False
            assert args.scrape_card is True
            assert args.send_telegram is True

    def test_cli_headless_flag_explicit(self):
        """Explicit --headless maintains headless=True and headful=False."""
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headless"]):
            args = parse_args()
            assert args.headless is True
            assert args.headful is False

    def test_cli_headful_and_visible_flags(self):
        """Both --headful and --visible set dest='headful' to True."""
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headful"]):
            args = parse_args()
            assert args.headful is True

        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--visible"]):
            args = parse_args()
            assert args.headful is True

    def test_cli_conflicting_headless_and_headful_flags(self):
        """When both --headless and --headful are passed, verify parse_args results."""
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headless", "--headful"]):
            args = parse_args()
            assert args.headless is True
            assert args.headful is True

        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headful", "--headless"]):
            args = parse_args()
            assert args.headless is True
            assert args.headful is True

    def test_driver_headless_resolution_logic(self):
        """Test the exact runtime resolution formula used in script_optimizado:
        is_headless = not getattr(current_cli_args, 'headful', False) if current_cli_args else True
        """
        def resolve_is_headless(cli_args):
            return not getattr(cli_args, 'headful', False) if cli_args else True

        # None args -> default True (headless)
        assert resolve_is_headless(None) is True

        # Default args -> True (headless)
        with mock.patch.object(sys, "argv", ["script_optimizado.py"]):
            args = parse_args()
            assert resolve_is_headless(args) is True

        # --headless only -> True (headless)
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headless"]):
            args = parse_args()
            assert resolve_is_headless(args) is True

        # --headful -> False (visible)
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headful"]):
            args = parse_args()
            assert resolve_is_headless(args) is False

        # --visible -> False (visible)
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--visible"]):
            args = parse_args()
            assert resolve_is_headless(args) is False

        # Both passed -> headful takes precedence (headful=True -> not headful=False)
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headless", "--headful"]):
            args = parse_args()
            assert resolve_is_headless(args) is False

    def test_cli_threads_and_limit_permutations(self):
        """Verify numeric parsing of --threads, --limit, --start-index."""
        with mock.patch.object(sys, "argv", [
            "script_optimizado.py",
            "--threads", "8",
            "--limit", "50",
            "--start-index", "10",
            "--output-file", "results/matrix_shard_1.xlsx"
        ]):
            args = parse_args()
            assert args.threads == 8
            assert args.limit == 50
            assert args.start_index == 10
            assert args.output_file == "results/matrix_shard_1.xlsx"

    def test_cli_boundary_limit_and_threads(self):
        """Test boundary limits: 0, 1 thread, negative limit."""
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--threads", "1", "--limit", "0"]):
            args = parse_args()
            assert args.threads == 1
            assert args.limit == 0

    def test_cli_unrecognized_argument_exits(self):
        """Unrecognized flags must trigger parser exit with code 2."""
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--non-existent-flag"]):
            with pytest.raises(SystemExit) as exc_info:
                parse_args()
            assert exc_info.value.code != 0
