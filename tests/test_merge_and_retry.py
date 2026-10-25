"""
Unit tests for merge_and_retry:
1. Deduplication priority logic (Pass 2 success overrides Pass 1 error, etc.)
2. Telegram HTML entity escaping with special characters (<, >, &)
3. Incomplete shard account recovery in check-timeouts
4. 6-sheet Excel structure and row routing
Runs in-memory and with temp files, zero external Chrome or network dependencies.
"""

import os
import json
import html
import pytest
import pandas as pd
from scripts.merge_and_retry import (
    compute_priority,
    format_telegram_summary,
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
    load_master_accounts,
    limpiar_saldo,
    generate_consolidated_excel,
    collect_failed_accounts,
    atomic_write_json,
    smart_truncate_telegram_html,
)


def deduplicate_records(records_with_file):
    """
    Consolidates list of dicts: [{'filename': ..., 'email': ..., 'saldo': ..., ...}]
    following the priority rules of merge_and_retry.py.
    """
    df = pd.DataFrame(records_with_file)
    df["_priority"] = [compute_priority(r["filename"], r.get("saldo", "")) for r in records_with_file]
    df.sort_values(by=["_priority"], inplace=True)
    df.drop_duplicates(subset=["email"], keep="last", inplace=True)
    df.drop(columns=["_priority"], inplace=True)
    return df.to_dict(orient="records")


class TestDeduplicationPriority:
    """Test suite for multi-pass shard deduplication and priority resolution."""

    def test_success_in_pass1_beats_error_in_pass1(self):
        records = [
            {"filename": "pass1_shard_0.xlsx", "email": "user1@alcampo.es", "saldo": "Error: Timeout", "card_number": None},
            {"filename": "pass1_shard_1.xlsx", "email": "user1@alcampo.es", "saldo": "Tu Saldo es 15,00 €", "card_number": "4002001111111"},
        ]
        deduped = deduplicate_records(records)
        assert len(deduped) == 1
        assert deduped[0]["saldo"] == "Tu Saldo es 15,00 €"
        assert deduped[0]["card_number"] == "4002001111111"

    def test_pass2_retry_success_beats_pass1_timeout(self):
        records = [
            {"filename": "saldos_pass1_shard_0.xlsx", "email": "user2@alcampo.es", "saldo": "Error: Bloqueo/Timeout", "card_number": None},
            {"filename": "saldos_retry_shard_0.xlsx", "email": "user2@alcampo.es", "saldo": "Tu Saldo es 42,50 €", "card_number": "4002002222222"},
        ]
        deduped = deduplicate_records(records)
        assert len(deduped) == 1
        assert deduped[0]["saldo"] == "Tu Saldo es 42,50 €"
        assert deduped[0]["filename"] == "saldos_retry_shard_0.xlsx"

    def test_pass2_error_overrides_pass1_error(self):
        # When both fail, Pass 2 has fresher diagnostic error and higher priority
        records = [
            {"filename": "pass1_shard_0.xlsx", "email": "user3@alcampo.es", "saldo": "Error: Timeout", "card_number": None},
            {"filename": "saldos_retry_shard_0.xlsx", "email": "user3@alcampo.es", "saldo": "Error: Credenciales no válidas", "card_number": None},
        ]
        deduped = deduplicate_records(records)
        assert len(deduped) == 1
        assert deduped[0]["saldo"] == "Error: Credenciales no válidas"
        assert deduped[0]["filename"] == "saldos_retry_shard_0.xlsx"

    def test_pass1_success_beats_pass2_error(self):
        # If Pass 1 already had success, an accidental retry error must NOT overwrite the success
        records = [
            {"filename": "pass1_shard_0.xlsx", "email": "user4@alcampo.es", "saldo": "Tu Saldo es 99,00 €", "card_number": "4002004444444"},
            {"filename": "saldos_retry_shard_0.xlsx", "email": "user4@alcampo.es", "saldo": "Error: Timeout", "card_number": None},
        ]
        deduped = deduplicate_records(records)
        assert len(deduped) == 1
        assert deduped[0]["saldo"] == "Tu Saldo es 99,00 €"

    def test_multi_account_deduplication(self):
        records = [
            {"filename": "pass1_shard_0.xlsx", "email": "a@alcampo.es", "saldo": "Tu Saldo es 10,00 €"},
            {"filename": "pass1_shard_1.xlsx", "email": "b@alcampo.es", "saldo": "Error: Timeout"},
            {"filename": "saldos_retry_shard_1.xlsx", "email": "b@alcampo.es", "saldo": "Tu Saldo es 20,00 €"},
            {"filename": "pass1_shard_2.xlsx", "email": "c@alcampo.es", "saldo": "Tu Saldo es 0,00 €"},
        ]
        deduped = deduplicate_records(records)
        assert len(deduped) == 3
        emails = {r["email"] for r in deduped}
        assert emails == {"a@alcampo.es", "b@alcampo.es", "c@alcampo.es"}
        b_acc = [r for r in deduped if r["email"] == "b@alcampo.es"][0]
        assert b_acc["saldo"] == "Tu Saldo es 20,00 €"

    def test_pass2_filename_variants(self):
        # Test pass2 naming variants like 'pass2-retry-shard-0.xlsx'
        p1 = compute_priority("pass1_shard_0.xlsx", "Error: Timeout")
        p2 = compute_priority("pass2-retry-shard-0.xlsx", "Error: Timeout")
        p3 = compute_priority("pass2-retry-shard-0.xlsx", "Tu Saldo es 5,00 €")
        assert p2 > p1
        assert p3 > p2


class TestTelegramHTMLEntityEscaping:
    """Test suite for sanitizing variables embedded in Telegram HTML notifications."""

    def test_escape_special_characters(self):
        raw_error = "Error: Element <div id='alert'> & 'call_center' > timeout"
        escaped = html.escape(raw_error)

        assert "<" not in escaped
        assert ">" not in escaped
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped

    def test_clean_telegram_message_formatting(self):
        # Simulates Telegram notification building with dynamic user/error content
        user_input = "<script>alert('pwned')</script>&test"
        clean_user = html.escape(user_input)

        telegram_msg = f"<b>Usuario:</b> <code>{clean_user}</code>\n<b>Estado:</b> OK"
        # The deliberate tags remain intact
        assert "<b>Usuario:</b>" in telegram_msg
        assert "<code>" in telegram_msg
        # The malicious/untrusted tags are sanitized
        assert "<script>" not in telegram_msg
        assert "&lt;script&gt;" in telegram_msg

    def test_format_telegram_summary_sanitizes_emails_and_diagnostics(self):
        # Dynamic emails and diagnostic summaries containing HTML special characters
        top_10 = [
            (25.50, "<user1>&danger@domain.com", "pass123", "4002001111111"),
            (10.00, "user2<admin>@domain.com", "pass456", "4002002222222"),
        ]
        error_summary = "Failed accounts: <div class='err'>Timeout & 429</div>"
        
        msg = format_telegram_summary(
            total=10,
            saldo_total=35.50,
            cuentas_dinero=2,
            cuentas_cero=5,
            cuentas_error=3,
            top_10=top_10,
            error_summary=error_summary
        )

        # Dynamic fields must be escaped
        assert "&lt;user1&gt;&amp;danger@domain.com" in msg
        assert "<user1>" not in msg
        assert "&lt;admin&gt;" in msg
        assert "<admin>" not in msg
        assert ("&lt;div class=&#x27;err&#x27;&gt;Timeout &amp; 429&lt;/div&gt;" in msg or
                "&lt;div class='err'&gt;Timeout &amp; 429&lt;/div&gt;" in msg)
        assert "<div" not in msg

        # Structural formatting tags must be preserved
        assert "<b>RESUMEN CONSOLIDADO FINAL (2 PASADAS MATRIZ)</b>" in msg
        assert "<b>Saldo Total Extraído:</b> 35.50 €" in msg
        assert "<b>Top 10 Cuentas con Mayor Saldo:</b>" in msg

    def test_format_telegram_summary_empty_top10(self):
        msg = format_telegram_summary(
            total=5,
            saldo_total=0.0,
            cuentas_dinero=0,
            cuentas_cero=5,
            cuentas_error=0,
            top_10=[]
        )
        assert "N/A" in msg
        assert "✅ Cuentas totales: 5" in msg


class TestIncompleteShardAccountRecovery:
    """Test suite for recovering missing accounts when shards crash or time out early."""

    def test_definitive_and_retryable_classification_helpers(self):
        # 1-argument backward compatibility
        assert is_definitive_success("Tu Saldo es 10,00 €") is True
        assert is_definitive_success("Tu Saldo es 0,00 €") is True
        assert is_definitive_success("Error: Timeout") is False

        # 2-argument card validation (Milestone M4)
        assert is_definitive_success("Tu Saldo es 10,00 €", "4003009301402") is True
        assert is_definitive_success("Tu Saldo es 10,00 €", None) is True
        assert is_definitive_success("Tu Saldo es 0,00 €", "4003009301402") is True
        assert is_definitive_success("Tu Saldo es 0,00 €", "4002001111111") is True
        assert is_definitive_success("Tu Saldo es 0,00 €", "2801234567890") is True
        assert is_definitive_success("Tu Saldo es 0,00 €", 4003009301402.0) is True
        assert is_definitive_success("Tu Saldo es 0,00 €", None) is False
        assert is_definitive_success("Tu Saldo es 0,00 €", "") is False
        assert is_definitive_success("Tu Saldo es 0,00 €", "invalid_card") is False

        assert is_definitive_error("Error: Credenciales incorrectas") is True
        assert is_definitive_error("Error: Cuenta bloqueada (Call Center)") is True
        assert is_definitive_error("Error: Requiere 2FA/Email") is True
        assert is_definitive_error("Error: Bloqueo/Timeout") is False
        assert is_definitive_error("Error: HTTP Status 429") is False

        # Retryable classification with and without card awareness
        assert is_retryable_failure("Error: Bloqueo/Timeout") is True
        assert is_retryable_failure("Error: Saldo no hidratado en DOM") is True
        assert is_retryable_failure("Error: HTTP Status 429", err_type="ip_error") is True
        assert is_retryable_failure("Tu Saldo es 10,00 €") is False
        assert is_retryable_failure("Error: Credenciales incorrectas") is False
        assert is_retryable_failure("Error: Cuenta bloqueada (Call Center)") is False
        # Degraded zero without card is retryable in Pass 2
        assert is_retryable_failure("Tu Saldo es 0,00 €", tarjeta_str=None) is True
        assert is_retryable_failure("Tu Saldo es 0,00 €", tarjeta_str="") is True
        # Verified zero with card is definitive success, thus not retryable
        assert is_retryable_failure("Tu Saldo es 0,00 €", tarjeta_str="4003009301402") is False
        assert is_retryable_failure("Tu Saldo es 0,00 €", "4003009301402") is False

    def test_incomplete_shard_rescues_missing_accounts(self, tmp_path):
        # Setup master accounts: 5 accounts
        master_accounts = [
            {"email": "ok@alcampo.es", "password": "p1"},
            {"email": "timeout@alcampo.es", "password": "p2"},
            {"email": "cred_err@alcampo.es", "password": "p3"},
            {"email": "missing1@alcampo.es", "password": "p4"},
            {"email": "missing2@alcampo.es", "password": "p5"},
        ]
        master_file = tmp_path / "master_accounts.json"
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(master_accounts, f)

        # Shard 0 only processed 3 accounts (crashed before reaching missing1 and missing2)
        shard_dir = tmp_path / "artifacts"
        shard_dir.mkdir()
        shard_data = [
            {"email": "ok@alcampo.es", "password": "p1", "saldo": "Tu Saldo es 12,00 €", "causa_error": "", "error_type": "ok"},
            {"email": "timeout@alcampo.es", "password": "p2", "saldo": "Error: Bloqueo/Timeout", "causa_error": "Timeout", "error_type": "session_error"},
            {"email": "cred_err@alcampo.es", "password": "p3", "saldo": "Error: Credenciales incorrectas", "causa_error": "Auth", "error_type": "account_error"},
        ]
        pd.DataFrame(shard_data).to_excel(shard_dir / "pass1_shard_0.xlsx", index=False)

        # Simulate check-timeouts logic
        loaded_master = load_master_accounts(str(master_file))
        assert len(loaded_master) == 5

        # Directly invoke the production script's collect_failed_accounts function
        failed_accounts = collect_failed_accounts([shard_dir / "pass1_shard_0.xlsx"], loaded_master)

        failed_emails = {a["email"] for a in failed_accounts}
        # The failed list must include:
        # - timeout@alcampo.es (retryable error)
        # - missing1@alcampo.es (unreached by shard)
        # - missing2@alcampo.es (unreached by shard)
        assert failed_emails == {"timeout@alcampo.es", "missing1@alcampo.es", "missing2@alcampo.es"}
        # Must NOT include definitive accounts
        assert "ok@alcampo.es" not in failed_emails
        assert "cred_err@alcampo.es" not in failed_emails

    def test_collect_failed_accounts_enqueues_degraded_zero_without_card(self, tmp_path):
        """
        Confirms that degraded 0,00 € accounts without a verified 13-digit card
        are enqueued into failed_accounts for Pass 2 retry, while genuine 0,00 € accounts
        with a valid card (400300... / 400200... / 280...) are treated as definitive successes.
        """
        shard_dir = tmp_path / "shards"
        shard_dir.mkdir()

        shard_data = [
            # Degraded 0,00 € without card (like witness account Noelia in Pass 1) -> MUST RETRY
            {"email": "degraded_zero@alcampo.es", "password": "p1", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok", "card_number": None},
            # Degraded 0,00 € with empty string card -> MUST RETRY
            {"email": "degraded_empty@alcampo.es", "password": "p2", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok", "card_number": ""},
            # Verified genuine 0,00 € with valid 13-digit card -> DEFINITIVE SUCCESS (DO NOT RETRY)
            {"email": "verified_zero@alcampo.es", "password": "p3", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok", "card_number": "4003009301402"},
            # Verified positive balance without card -> DEFINITIVE SUCCESS (DO NOT RETRY)
            {"email": "positive_balance@alcampo.es", "password": "p4", "saldo": "Tu Saldo es 3,00 €", "causa_error": "", "error_type": "ok", "card_number": None},
        ]
        shard_file = shard_dir / "pass1_shard_0.xlsx"
        pd.DataFrame(shard_data).to_excel(shard_file, index=False)

        failed_accounts = collect_failed_accounts([shard_file])
        failed_emails = {a["email"] for a in failed_accounts}

        assert "degraded_zero@alcampo.es" in failed_emails, "Degraded 0,00 € without card must be enqueued for Pass 2 retry"
        assert "degraded_empty@alcampo.es" in failed_emails, "Degraded 0,00 € with empty card must be enqueued for Pass 2 retry"
        assert "verified_zero@alcampo.es" not in failed_emails, "Verified 0,00 € with valid card must NOT be retried"
        assert "positive_balance@alcampo.es" not in failed_emails, "Positive balance account must NOT be retried"


class TestConsolidatedExcelStructureAndRouting:
    """Test suite for the 6-sheet Excel workbook structure and row routing."""

    def test_six_sheet_excel_structure_and_row_routing(self, tmp_path):
        out_excel = tmp_path / "CONSOLIDATED_TEST.xlsx"

        records = [
            {"email": "pos1@alcampo.es", "password": "p1", "saldo": "Tu Saldo es 25,50 €", "causa_error": "", "error_type": "ok", "card_number": "4002001111"},
            {"email": "pos2@alcampo.es", "password": "p2", "saldo": "Tu Saldo es 1,00 €", "causa_error": "", "error_type": "ok", "card_number": "4002002222"},
            {"email": "zero@alcampo.es", "password": "p3", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok", "card_number": "4002003333"},
            {"email": "cc1@alcampo.es", "password": "p4", "saldo": "Error: Cuenta bloqueada (Call Center)", "causa_error": "Call Center", "error_type": "needs_attention", "card_number": None},
            {"email": "cc2@alcampo.es", "password": "p5", "saldo": "Error: Requiere código de verificación 2FA", "causa_error": "2FA", "error_type": "needs_attention", "card_number": None},
            {"email": "cred@alcampo.es", "password": "p6", "saldo": "Error: Credenciales incorrectas", "causa_error": "Auth", "error_type": "account_error", "card_number": None},
            {"email": "timeout@alcampo.es", "password": "p7", "saldo": "Error: Bloqueo/Timeout", "causa_error": "Timeout", "error_type": "session_error", "card_number": None},
            {"email": "waf@alcampo.es", "password": "p8", "saldo": "Error: HTTP Status 429", "causa_error": "Too Many Requests", "error_type": "ip_error", "card_number": None},
        ]

        df_all = pd.DataFrame(records)

        # Directly invoke the production script's generate_consolidated_excel function
        sheets = generate_consolidated_excel(df_all, str(out_excel))

        # Inspect generated workbook on disk
        excel_file = pd.ExcelFile(out_excel)
        expected_sheets = [
            "Todas las Cuentas",
            "Exitosas con Saldo",
            "Saldo Cero Verificado",
            "Bloqueadas Call Center",
            "Error Credenciales",
            "Error IP y Timeouts"
        ]
        assert excel_file.sheet_names == expected_sheets

        # Verify row counts and routing
        s_all = pd.read_excel(excel_file, sheet_name="Todas las Cuentas")
        s_pos = pd.read_excel(excel_file, sheet_name="Exitosas con Saldo")
        s_zero = pd.read_excel(excel_file, sheet_name="Saldo Cero Verificado")
        s_cc = pd.read_excel(excel_file, sheet_name="Bloqueadas Call Center")
        s_cred = pd.read_excel(excel_file, sheet_name="Error Credenciales")
        s_ipto = pd.read_excel(excel_file, sheet_name="Error IP y Timeouts")

        assert len(s_all) == 8
        assert len(s_pos) == 2  # pos1, pos2
        assert len(s_zero) == 1  # zero
        assert len(s_cc) == 2    # cc1, cc2
        assert len(s_cred) == 1  # cred
        assert len(s_ipto) == 2  # timeout, waf

        # Conservation of rows: sum of 5 sub-sheets == master sheet
        assert len(s_pos) + len(s_zero) + len(s_cc) + len(s_cred) + len(s_ipto) == len(s_all)

        # Check no temporary column leaked
        temp_cols = ["_priority", "_saldo_val", "_is_success", "_is_callcenter", "_is_credenciales"]
        for c in temp_cols:
            assert c not in s_all.columns
            assert c not in s_pos.columns

        # Verify exact members
        assert set(s_pos["email"]) == {"pos1@alcampo.es", "pos2@alcampo.es"}
        assert set(s_zero["email"]) == {"zero@alcampo.es"}
        assert set(s_cc["email"]) == {"cc1@alcampo.es", "cc2@alcampo.es"}
        assert set(s_cred["email"]) == {"cred@alcampo.es"}
        assert set(s_ipto["email"]) == {"timeout@alcampo.es", "waf@alcampo.es"}


class TestDirectoryIsolationAndNegativeArtifactHandling:
    """Negative tests to guarantee that empty or missing input directories do NOT ingest root/historical files."""

    def test_empty_or_fake_input_dir_finds_zero_files_and_ingests_no_root_artifacts(self, tmp_path):
        """
        When --input-dir is non-existent or empty, merge_and_retry MUST NOT fall back
        to scanning '.' or 'scraper', preventing ingestion of historical files like
        REPORTE_DEFINITIVO_766_CUENTAS_TELEGRAM.xlsx.
        """
        import subprocess
        import sys
        fake_empty_dir = tmp_path / "empty_shards_dir"
        fake_empty_dir.mkdir()
        out_excel = tmp_path / "SHOULD_NOT_BE_CREATED.xlsx"

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["TELEGRAM_TOKEN"] = "none"
        env["FIREBASE_DB_URL"] = ""
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(repo_root, "scripts", "merge_and_retry.py"),
            "--mode", "final-merge",
            "--input-dir", str(fake_empty_dir),
            "--output-excel", str(out_excel)
        ]
        # Run explicitly from repo_root
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=repo_root, encoding="utf-8", errors="replace")
        assert res.returncode == 0
        assert "No se encontraron archivos para consolidar" in res.stdout
        assert not out_excel.exists(), "Output Excel must NOT be created when input directory has zero shard files"

    def test_shard_pattern_filtering_rejects_unrelated_excel_files(self, tmp_path):
        """
        Files in the input directory that do NOT match shard naming patterns (e.g. historical reports)
        must be excluded from consolidation.
        """
        import subprocess
        import sys
        shards_dir = tmp_path / "shards"
        shards_dir.mkdir()

        # Unrelated file without shard naming pattern
        unrelated_df = pd.DataFrame([{"email": "unrelated@test.com", "saldo": "Tu Saldo es 50,00 €"}])
        unrelated_df.to_excel(shards_dir / "historical_report.xlsx", index=False)

        # Valid shard file with pattern
        valid_df = pd.DataFrame([{"email": "valid@test.com", "saldo": "Tu Saldo es 10,00 €"}])
        valid_df.to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        out_excel = tmp_path / "FILTERED_OUTPUT.xlsx"
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["TELEGRAM_TOKEN"] = "none"
        env["FIREBASE_DB_URL"] = ""
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(repo_root, "scripts", "merge_and_retry.py"),
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
            "--dashboard-dir", str(tmp_path / "dashboard"),
            "--docs-dir", str(tmp_path / "docs")
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=repo_root, encoding="utf-8", errors="replace")
        assert res.returncode == 0
        assert out_excel.exists()

        df_out = pd.read_excel(out_excel, sheet_name="Todas las Cuentas")
        assert len(df_out) == 1
        assert df_out.iloc[0]["email"] == "valid@test.com"
        assert "unrelated@test.com" not in set(df_out["email"])

    def test_check_timeouts_empty_dir_does_not_leak_root_files(self, tmp_path):
        """
        Verifies that check-timeouts on an empty directory does not leak root files into failed accounts.
        """
        import subprocess
        import sys
        fake_empty_dir = tmp_path / "empty_check_dir"
        fake_empty_dir.mkdir()
        failed_json = tmp_path / "failed_out.json"

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(repo_root, "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(fake_empty_dir),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=repo_root, encoding="utf-8", errors="replace")
        assert res.returncode == 0
        assert "Inspeccionando 0 archivo(s)" in res.stdout


class TestDualDashboardAndSmartTruncation:
    """Test suite for Milestone M4 dual dashboard sync and smart Telegram HTML truncation."""

    def test_atomic_write_json_creates_atomic_file(self, tmp_path):
        target_file = tmp_path / "nested" / "test_data.json"
        sample_data = {"key": "value", "list": [1, 2, 3], "nested": {"a": "b"}}

        atomic_write_json(str(target_file), sample_data, indent=2)

        assert target_file.exists()
        with open(target_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == sample_data

    def test_smart_truncate_telegram_html_entity_and_tag_safety(self):
        # 1. Under max_len returns unchanged
        short_msg = "<b>Title</b>\nBody text with &amp; entity."
        assert smart_truncate_telegram_html(short_msg, max_len=3980) == short_msg

        # 2. Huge message with opened tags and entities truncates strictly <= 3980
        massive_body = "<b>Important</b> <code>" + ("&amp; " * 800) + "</code>"
        truncated = smart_truncate_telegram_html(massive_body, max_len=3980)

        assert len(truncated) <= 3980
        assert truncated.endswith("\n... [truncado]")
        # Check no raw unescaped '&'
        # An unescaped ampersand would be '&' followed by non-entity chars or at the end
        import re
        assert not re.search(r"&(?![a-zA-Z0-9#]+;)", truncated.replace("... [truncado]", "")), "No split or raw ampersands"
        # Check that open tags are balanced
        open_b = truncated.count("<b>")
        close_b = truncated.count("</b>")
        assert open_b == close_b, f"Tags <b> must balance: {open_b} open vs {close_b} closed"
        open_code = truncated.count("<code>")
        close_code = truncated.count("</code>")
        assert open_code == close_code, f"Tags <code> must balance: {open_code} open vs {close_code} closed"

    def test_filter_retries_cli_mode_accepted(self, tmp_path):
        """CLI mode 'filter-retries' must be supported without argparse error."""
        import subprocess
        import sys
        fake_empty_dir = tmp_path / "empty_filter_dir"
        fake_empty_dir.mkdir()
        failed_json = tmp_path / "failed_filter.json"

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(repo_root, "scripts", "merge_and_retry.py"),
            "--mode", "filter-retries",
            "--input-dir", str(fake_empty_dir),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=repo_root, encoding="utf-8", errors="replace")
        assert res.returncode == 0
        assert "Inspeccionando 0 archivo(s)" in res.stdout

    def test_final_merge_dual_dashboard_and_docs_sync(self, tmp_path):
        """
        Verifies that final-merge writes top_accounts.json, history.json, and progreso.json
        to both --dashboard-dir and --docs-dir atomically.
        """
        import subprocess
        import sys
        shards_dir = tmp_path / "shards"
        shards_dir.mkdir()
        dashboard_dir = tmp_path / "dashboard"
        docs_dir = tmp_path / "docs"
        out_excel = tmp_path / "REPORTE_TEST.xlsx"

        # Create mock shard with positive account and card
        shard_df = pd.DataFrame([
            {"email": "top1@test.com", "password": "p1", "saldo": "Tu Saldo es 15,50 €", "card_number": "4003009301402", "causa_error": "", "error_type": "ok"},
            {"email": "zero@test.com", "password": "p2", "saldo": "Tu Saldo es 0,00 €", "card_number": "4002001111111", "causa_error": "", "error_type": "ok"},
        ])
        shard_df.to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["TELEGRAM_TOKEN"] = "none"
        env["FIREBASE_DB_URL"] = ""
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(repo_root, "scripts", "merge_and_retry.py"),
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_excel),
            "--dashboard-dir", str(dashboard_dir),
            "--docs-dir", str(docs_dir)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=repo_root, encoding="utf-8", errors="replace")
        assert res.returncode == 0

        # Verify dual synchronization in dashboard/
        assert (dashboard_dir / "top_accounts.json").exists()
        assert (dashboard_dir / "history.json").exists()
        assert (dashboard_dir / "progreso.json").exists()

        # Verify dual synchronization in docs/
        assert (docs_dir / "top_accounts.json").exists()
        assert (docs_dir / "history.json").exists()
        assert (docs_dir / "progreso.json").exists()

        # Check content in docs/top_accounts.json
        with open(docs_dir / "top_accounts.json", "r", encoding="utf-8") as f:
            top_data = json.load(f)
        assert len(top_data) == 1
        assert top_data[0]["email"] == "top1@test.com"
        assert top_data[0]["balance"] == 15.50
        assert top_data[0]["card_number"] == "4003009301402"
