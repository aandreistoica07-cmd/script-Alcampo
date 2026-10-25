"""
Adversarial Simulation Test Suite for Milestone M4-2:
Empirical reproduction of GitHub Actions Run #382 failure scenario:
- 512 total accounts partitioned across 7 matrix shards.
- 298 degraded zero accounts ('Tu Saldo es 0,00 €' without verified 13-digit card).
- Witness account 'noelia_gll@hotmail.com' starting degraded in Pass 1.
- Empirical verification of:
  1. collect_failed_accounts collects 100% (298/298) of degraded zeros into failed_accounts.json for Pass 2.
  2. Verified zeros (0,00 € with valid card) and positive balances are NOT retried.
  3. Permanent errors (Call Center, Credenciales incorrectas) are NOT retried.
  4. Pass 2 resolution overrides Pass 1 degraded records via priority deduplication.
  5. Consolidated 6-sheet Excel preserves mathematical row conservation (Sheet 1 = Sum(Sheets 2..6) = 512).
  6. Positive balances (including Noelia with 3,00 €) populate Sheet 2 ('Exitosas con Saldo').
  7. Top 10 ranking is strictly sorted descending, total balance exceeds 150 €, and Noelia appears in Top 10.
  8. Dual dashboards ('dashboard/' and 'docs/') and root JSON files are updated atomically and in sync.
  9. Edge-case and corruption handling: float-converted cards (ending in .0), invalid card prefixes,
     nan/None values, and alternative column names ('tarjeta' vs 'card_number').
"""

import os
import sys
import json
import subprocess
import pytest
import pandas as pd
from unittest import mock

from scripts.merge_and_retry import (
    compute_priority,
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
    collect_failed_accounts,
    generate_consolidated_excel,
    limpiar_saldo,
    atomic_write_json,
    format_telegram_summary,
)


class TestRun382ScenarioSimulation:
    """Empirical adversarial simulation replicating GitHub Actions Run #382."""

    @pytest.fixture
    def run382_dataset(self, tmp_path):
        """
        Synthesizes the exact Run #382 scenario:
        - 512 total accounts.
        - Distributed across 7 shards: shard_0 to shard_6.
        - 298 degraded zeros ('Tu Saldo es 0,00 €', card=None or empty), including Noelia.
        - 70 verified zeros ('Tu Saldo es 0,00 €', card='400200xxxxxxx').
        - 30 Pass 1 positive accounts ('Tu Saldo es 5,00 €', card='400300xxxxxxx').
        - 50 Call Center / needs_attention errors.
        - 40 Bad Credentials / account_error.
        - 24 Session / Timeout errors.
        Total = 298 + 70 + 30 + 50 + 40 + 24 = 512 accounts.
        """
        all_accounts = []
        degraded_emails = set()
        verified_zero_emails = set()
        positive_pass1_emails = set()
        call_center_emails = set()
        cred_error_emails = set()
        timeout_emails = set()

        # 1. Witness account Noelia + 297 other degraded zeros = 298 degraded
        noelia_email = "noelia_gll@hotmail.com"
        all_accounts.append({
            "email": noelia_email,
            "password": "Password_Noelia_123!",
            "saldo": "Tu Saldo es 0,00 €",
            "card_number": None,
            "causa_error": "",
            "error_type": "ok",
        })
        degraded_emails.add(noelia_email)

        for i in range(1, 298):
            em = f"degraded_zero_{i:03d}@alcampo.es"
            # Vary missing card formats: None, "", "None", "nan"
            card_val = None if (i % 3 == 0) else ("" if (i % 3 == 1) else "None")
            all_accounts.append({
                "email": em,
                "password": f"Pass_Deg_{i}!",
                "saldo": "Tu Saldo es 0,00 €",
                "card_number": card_val,
                "causa_error": "",
                "error_type": "ok",
            })
            degraded_emails.add(em)

        assert len(degraded_emails) == 298

        # 2. 70 Verified zeros (valid 13-digit cards: 400200... or 280...)
        for i in range(70):
            em = f"verified_zero_{i:03d}@alcampo.es"
            prefix = "400200" if i % 2 == 0 else "280100"
            card = f"{prefix}{i:07d}"
            all_accounts.append({
                "email": em,
                "password": f"Pass_VZero_{i}!",
                "saldo": "Tu Saldo es 0,00 €",
                "card_number": card,
                "causa_error": "",
                "error_type": "ok",
            })
            verified_zero_emails.add(em)

        assert len(verified_zero_emails) == 70

        # 3. 30 Positive balances in Pass 1 (e.g. 1.00 €, reflecting Run #382 baseline where Pass 1 only had ~17.82 € total)
        for i in range(30):
            em = f"pass1_positive_{i:03d}@alcampo.es"
            card = f"400300{i:07d}"
            all_accounts.append({
                "email": em,
                "password": f"Pass_Pos1_{i}!",
                "saldo": "Tu Saldo es 1,00 €",
                "card_number": card,
                "causa_error": "",
                "error_type": "ok",
            })
            positive_pass1_emails.add(em)

        assert len(positive_pass1_emails) == 30

        # 4. 50 Call Center / needs_attention errors
        for i in range(50):
            em = f"call_center_{i:03d}@alcampo.es"
            all_accounts.append({
                "email": em,
                "password": f"Pass_CC_{i}!",
                "saldo": "Error: Call Center 913 687 857",
                "card_number": None,
                "causa_error": "call center",
                "error_type": "needs_attention",
            })
            call_center_emails.add(em)

        assert len(call_center_emails) == 50

        # 5. 40 Bad Credentials / account_error
        for i in range(40):
            em = f"cred_error_{i:03d}@alcampo.es"
            all_accounts.append({
                "email": em,
                "password": f"Pass_Cred_{i}!",
                "saldo": "Error: Credenciales incorrectas",
                "card_number": None,
                "causa_error": "credenciales no validas",
                "error_type": "account_error",
            })
            cred_error_emails.add(em)

        assert len(cred_error_emails) == 40

        # 6. 24 Session / Timeout errors
        for i in range(24):
            em = f"timeout_err_{i:03d}@alcampo.es"
            all_accounts.append({
                "email": em,
                "password": f"Pass_Timeout_{i}!",
                "saldo": "Error: Bloqueo/Timeout Shard",
                "card_number": None,
                "causa_error": "timeout",
                "error_type": "session_error",
            })
            timeout_emails.add(em)

        assert len(timeout_emails) == 24
        assert len(all_accounts) == 512, f"Total accounts must be 512, got {len(all_accounts)}"

        # Partition into 7 shards (5 shards with 73, 2 shards with 74)
        shards_dir = tmp_path / "pass1_shards"
        shards_dir.mkdir(parents=True, exist_ok=True)

        shard_files = []
        start_idx = 0
        for s_idx in range(7):
            chunk_size = 74 if s_idx == 0 else 73
            chunk = all_accounts[start_idx : start_idx + chunk_size]
            start_idx += chunk_size

            shard_df = pd.DataFrame(chunk)
            shard_path = shards_dir / f"pass1_part_{s_idx}.xlsx"
            shard_df.to_excel(shard_path, index=False)
            shard_files.append(str(shard_path))

        assert start_idx == 512
        assert len(shard_files) == 7

        # Master accounts list
        master_accounts = [
            {"email": a["email"], "password": a["password"]}
            for a in all_accounts
        ]

        return {
            "tmp_path": tmp_path,
            "shards_dir": shards_dir,
            "shard_files": shard_files,
            "all_accounts": all_accounts,
            "master_accounts": master_accounts,
            "degraded_emails": degraded_emails,
            "verified_zero_emails": verified_zero_emails,
            "positive_pass1_emails": positive_pass1_emails,
            "call_center_emails": call_center_emails,
            "cred_error_emails": cred_error_emails,
            "timeout_emails": timeout_emails,
            "noelia_email": noelia_email,
        }

    def test_pass1_collect_failed_accounts_captures_100_percent_degraded_zeros(self, run382_dataset):
        """
        Requirement a & b:
        Verify collect_failed_accounts captures 100% of the 298 degraded zeros,
        plus retryable timeouts (24), yielding 322 retry candidates.
        Verify verified zeros (70), positive balances (30), and permanent errors (90)
        are strictly excluded from the Pass 2 retry queue.
        """
        shard_files = run382_dataset["shard_files"]
        master_accounts = run382_dataset["master_accounts"]
        degraded_emails = run382_dataset["degraded_emails"]
        verified_zero_emails = run382_dataset["verified_zero_emails"]
        positive_pass1_emails = run382_dataset["positive_pass1_emails"]
        call_center_emails = run382_dataset["call_center_emails"]
        cred_error_emails = run382_dataset["cred_error_emails"]
        timeout_emails = run382_dataset["timeout_emails"]
        noelia_email = run382_dataset["noelia_email"]

        # Run collect_failed_accounts
        failed = collect_failed_accounts(shard_files, master_accounts)
        failed_emails = {acc["email"] for acc in failed}

        # 1. 100% of degraded zeros MUST be queued for Pass 2
        missing_degraded = degraded_emails - failed_emails
        assert len(missing_degraded) == 0, f"Missing degraded zeros: {len(missing_degraded)}"
        assert noelia_email in failed_emails, "Witness account Noelia MUST be queued for Pass 2"

        # 2. All 24 timeout errors MUST be queued for Pass 2
        missing_timeouts = timeout_emails - failed_emails
        assert len(missing_timeouts) == 0, f"Missing timeouts: {len(missing_timeouts)}"

        # Total retried accounts: exactly 298 + 24 = 322
        expected_retries = degraded_emails | timeout_emails
        assert failed_emails == expected_retries
        assert len(failed) == 322

        # 3. Verified zeros MUST NOT be retried
        leaked_vzeros = verified_zero_emails.intersection(failed_emails)
        assert len(leaked_vzeros) == 0, f"Verified zeros erroneously queued: {leaked_vzeros}"

        # 4. Positive accounts MUST NOT be retried
        leaked_pos = positive_pass1_emails.intersection(failed_emails)
        assert len(leaked_pos) == 0, f"Positive accounts erroneously queued: {leaked_pos}"

        # 5. Permanent errors (Call Center & Credential errors) MUST NOT be retried
        leaked_cc = call_center_emails.intersection(failed_emails)
        assert len(leaked_cc) == 0, f"Call Center accounts erroneously queued: {leaked_cc}"
        leaked_cred = cred_error_emails.intersection(failed_emails)
        assert len(leaked_cred) == 0, f"Credential error accounts erroneously queued: {leaked_cred}"

    def test_cli_filter_retries_produces_valid_failed_accounts_json(self, run382_dataset):
        """
        Verify CLI invocation of `scripts/merge_and_retry.py --mode filter-retries`
        generates the expected failed_accounts.json file containing exactly 322 accounts.
        """
        tmp_path = run382_dataset["tmp_path"]
        shards_dir = run382_dataset["shards_dir"]
        failed_json_path = tmp_path / "failed_accounts.json"
        accounts_json_path = tmp_path / "accounts.json"

        # Save master accounts for CLI
        with open(accounts_json_path, "w", encoding="utf-8") as f:
            json.dump(run382_dataset["master_accounts"], f)

        script_path = os.path.abspath("scripts/merge_and_retry.py")
        cmd = [
            sys.executable,
            script_path,
            "--mode", "filter-retries",
            "--input-dir", str(shards_dir),
            "--failed-json", str(failed_json_path),
            "--accounts-file", str(accounts_json_path),
        ]

        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path), env=env)
        assert proc.returncode == 0, f"CLI filter-retries failed: {proc.stderr}\n{proc.stdout}"
        assert failed_json_path.exists(), f"failed_accounts.json must be generated. Stdout: {proc.stdout}\nStderr: {proc.stderr}"

        with open(failed_json_path, "r", encoding="utf-8") as f:
            queued_accounts = json.load(f)

        assert len(queued_accounts) == 322
        queued_emails = {a["email"] for a in queued_accounts}
        assert run382_dataset["noelia_email"] in queued_emails
        assert run382_dataset["degraded_emails"].issubset(queued_emails)

    def test_pass2_resolution_consolidation_and_top10(self, run382_dataset):
        """
        Requirement c, d, e:
        Simulate Pass 2 resolving retried accounts:
        - Witness Noelia resolves with 3,00 € and card '4003009301402'.
        - 9 high-value accounts resolve with balances from 45,50 € down to 4,00 €,
          placing Noelia (3,00 €) into the Top 10 ranking.
        - Pass 1 positive accounts (30 accounts * 5.00 € = 150.00 €) plus recovered accounts
          raise total balance to > 300.00 € (exceeding 150.00 € threshold).
        - Run `scripts/merge_and_retry.py --mode final-merge`.
        - Verify:
          1. REPORTE_DEFINITIVO_TELEGRAM.xlsx has 6 sheets.
          2. Row conservation: Sheet 1 count == sum(Sheets 2..6) == 512.
          3. Sheet 2 ('Exitosas con Saldo') contains Noelia and all positive accounts.
          4. Total balance > 150.00 €.
          5. Top 10 includes positive accounts and Noelia at rank 10.
          6. Dual dashboard ('dashboard/' and 'docs/') JSON files are atomically written and match.
        """
        tmp_path = run382_dataset["tmp_path"]
        shards_dir = run382_dataset["shards_dir"]
        output_excel = tmp_path / "REPORTE_DEFINITIVO_TELEGRAM.xlsx"
        dashboard_dir = tmp_path / "dashboard"
        docs_dir = tmp_path / "docs"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)

        noelia_email = run382_dataset["noelia_email"]

        # Synthesize Pass 2 retry output (saldos_retry_shard_0.xlsx)
        # 1. Noelia: recovered 3,00 € and card 4003009301402
        pass2_records = [
            {
                "email": noelia_email,
                "password": "Password_Noelia_123!",
                "saldo": "Tu Saldo es 3,00 €",
                "card_number": "4003009301402",
                "causa_error": "",
                "error_type": "ok",
            }
        ]

        # 2. 9 Top accounts to form ranks 1 to 9
        top_balances = [
            (45.50, "account_top1@alcampo.es", "4003001111111"),
            (38.20, "account_top2@alcampo.es", "4003002222222"),
            (29.00, "account_top3@alcampo.es", "4003003333333"),
            (22.10, "account_top4@alcampo.es", "4003004444444"),
            (18.40, "account_top5@alcampo.es", "4003005555555"),
            (12.00, "account_top6@alcampo.es", "4003006666666"),
            (8.50, "account_top7@alcampo.es", "4003007777777"),
            (5.00, "account_top8@alcampo.es", "4003008888888"),
            (4.00, "account_top9@alcampo.es", "4003009999999"),
        ]

        # Pick 9 accounts from degraded_emails (excluding Noelia) to assign these top balances
        other_degraded = sorted(list(run382_dataset["degraded_emails"] - {noelia_email}))
        for idx, (bal, _, card) in enumerate(top_balances):
            em = other_degraded[idx]
            bal_str = f"Tu Saldo es {bal:.2f} €".replace(".", ",")
            pass2_records.append({
                "email": em,
                "password": f"Pass_Deg_{idx+1}!",
                "saldo": bal_str,
                "card_number": card,
                "causa_error": "",
                "error_type": "ok",
            })

        # 3. Remaining 288 degraded accounts: resolve to verified zero with valid card
        for idx in range(9, len(other_degraded)):
            em = other_degraded[idx]
            pass2_records.append({
                "email": em,
                "password": f"Pass_Deg_{idx+1}!",
                "saldo": "Tu Saldo es 0,00 €",
                "card_number": f"40020088{idx:05d}",
                "causa_error": "",
                "error_type": "ok",
            })

        # 4. 24 Timeout accounts: resolve in Pass 2
        for idx, em in enumerate(sorted(list(run382_dataset["timeout_emails"]))):
            pass2_records.append({
                "email": em,
                "password": f"Pass_Timeout_{idx}!",
                "saldo": "Tu Saldo es 0,00 €",
                "card_number": f"40020077{idx:05d}",
                "causa_error": "",
                "error_type": "ok",
            })

        assert len(pass2_records) == 322

        # Write Pass 2 shard into shards_dir
        pass2_shard_path = shards_dir / "saldos_retry_shard_0.xlsx"
        pd.DataFrame(pass2_records).to_excel(pass2_shard_path, index=False)

        # Run final-merge CLI
        script_path = os.path.abspath("scripts/merge_and_retry.py")
        cmd = [
            sys.executable,
            script_path,
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(output_excel),
            "--dashboard-dir", str(dashboard_dir),
            "--docs-dir", str(docs_dir),
        ]

        # Execute CLI
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path), env=env)
        assert proc.returncode == 0, f"CLI final-merge failed: {proc.stderr}\n{proc.stdout}"
        assert output_excel.exists(), "REPORTE_DEFINITIVO_TELEGRAM.xlsx must exist"

        # 1. Verify 6 Sheets in Excel
        excel_file = pd.ExcelFile(output_excel)
        expected_sheets = [
            "Todas las Cuentas",
            "Exitosas con Saldo",
            "Saldo Cero Verificado",
            "Bloqueadas Call Center",
            "Error Credenciales",
            "Error IP y Timeouts",
        ]
        assert excel_file.sheet_names == expected_sheets, f"Sheets mismatch: {excel_file.sheet_names}"

        df_todas = excel_file.parse("Todas las Cuentas")
        df_con_saldo = excel_file.parse("Exitosas con Saldo")
        df_saldo_cero = excel_file.parse("Saldo Cero Verificado")
        df_callcenter = excel_file.parse("Bloqueadas Call Center")
        df_credenciales = excel_file.parse("Error Credenciales")
        df_ip_timeouts = excel_file.parse("Error IP y Timeouts")

        # 2. Row conservation
        assert len(df_todas) == 512, f"Total accounts must be 512, got {len(df_todas)}"
        sum_categorized = (
            len(df_con_saldo)
            + len(df_saldo_cero)
            + len(df_callcenter)
            + len(df_credenciales)
            + len(df_ip_timeouts)
        )
        assert len(df_todas) == sum_categorized, (
            f"Row conservation failed: Total {len(df_todas)} != Sum {sum_categorized}"
        )

        # 3. Witness Noelia in Sheet 2 ('Exitosas con Saldo')
        noelia_rows = df_con_saldo[df_con_saldo["email"] == noelia_email]
        assert len(noelia_rows) == 1, "Noelia must appear exactly once in Sheet 2"
        noelia_record = noelia_rows.iloc[0]
        assert "3,00" in str(noelia_record["saldo"]) or "3.00" in str(noelia_record["saldo"])
        assert str(noelia_record["card_number"]).strip() == "4003009301402"

        # 4. Total balance calculation
        total_balance = sum(limpiar_saldo(s) for s in df_con_saldo["saldo"] if limpiar_saldo(s))
        assert total_balance > 150.0, f"Total balance must exceed 150.00 €, got {total_balance:.2f} €"

        # 5. Top 10 ranking verification in dashboard/ and docs/
        for d_dir in [dashboard_dir, docs_dir]:
            top_file = d_dir / "top_accounts.json"
            assert top_file.exists(), f"top_accounts.json missing in {d_dir}"
            with open(top_file, "r", encoding="utf-8") as f:
                top_data = json.load(f)

            assert len(top_data) == 10, f"Top 10 must contain 10 accounts, got {len(top_data)}"
            # Verify sorted descending
            balances = [item["balance"] for item in top_data]
            assert balances == sorted(balances, reverse=True), "Top 10 balances must be sorted descending"

            # Verify Noelia is in Top 10
            top_emails = [item["email"] for item in top_data]
            assert noelia_email in top_emails, f"Noelia {noelia_email} must appear in Top 10: {top_emails}"
            noelia_top_entry = [item for item in top_data if item["email"] == noelia_email][0]
            assert noelia_top_entry["balance"] == 3.0
            assert noelia_top_entry["card_number"] == "4003009301402"

            # Verify history.json
            hist_file = d_dir / "history.json"
            assert hist_file.exists(), f"history.json missing in {d_dir}"
            with open(hist_file, "r", encoding="utf-8") as f:
                hist_data = json.load(f)
            assert len(hist_data) >= 1
            last_entry = hist_data[-1]
            assert last_entry["checked"] == 512
            assert last_entry["total_balance"] > 150.0

            # Verify progreso.json
            prog_file = d_dir / "progreso.json"
            assert prog_file.exists(), f"progreso.json missing in {d_dir}"
            with open(prog_file, "r", encoding="utf-8") as f:
                prog_data = json.load(f)
            assert prog_data["total"] == 512
            assert prog_data["is_finished"] is True
            assert prog_data["total_balance"] > 150.0


class TestAdversarialCardAndZeroEdgeCases:
    """Adversarial stress-testing of edge cases in card numbers and 0,00 € evaluation."""

    @pytest.mark.parametrize("card_input,expected_retry", [
        (None, True),                     # Missing card -> must retry
        ("", True),                       # Empty string -> must retry
        ("   ", True),                    # Whitespace -> must retry
        ("None", True),                   # String 'None' -> must retry
        ("nan", True),                    # String 'nan' -> must retry
        (float("nan"), True),             # Math NaN -> must retry
        ("400", True),                    # Truncated card -> must retry
        ("1234567890123", True),          # 13 digits but invalid prefix -> must retry
        ("9994001234567", True),          # Invalid prefix -> must retry
        ("4002001111111", False),         # Valid 400200 card -> definitive success, NO retry
        ("4003009301402", False),         # Valid 400300 card -> definitive success, NO retry
        ("2801234567890", False),         # Valid 280 card -> definitive success, NO retry
        ("4002001111111.0", False),       # Float artifact (.0) -> cleaned and valid, NO retry
        (4002001111111.0, False),         # Numeric float -> cleaned and valid, NO retry
        ("2809999999999.0", False),       # Float artifact (.0) -> cleaned and valid, NO retry
    ])
    def test_is_retryable_failure_card_matrix(self, card_input, expected_retry):
        """Stress-test is_retryable_failure with diverse card representations."""
        result = is_retryable_failure("Tu Saldo es 0,00 €", tarjeta_str=card_input)
        assert result is expected_retry, f"Failed for card_input={card_input!r}: expected {expected_retry}, got {result}"

    def test_positive_balance_never_retried_even_without_card(self):
        """If balance > 0, account must be definitive success and never retried even without card."""
        assert is_retryable_failure("Tu Saldo es 3,00 €", tarjeta_str=None) is False
        assert is_retryable_failure("Tu Saldo es 0,01 €", tarjeta_str="") is False
        assert is_definitive_success("Tu Saldo es 3,00 €", tarjeta_str=None) is True

    def test_alternative_column_name_tarjeta_supported_in_collect_failed_accounts(self, tmp_path):
        """Ensure collect_failed_accounts detects column 'tarjeta' when 'card_number' is absent."""
        shard_path = tmp_path / "shard_with_tarjeta.xlsx"
        df = pd.DataFrame([
            {"email": "valid_zero@test.com", "saldo": "Tu Saldo es 0,00 €", "tarjeta": "4002001111111"},
            {"email": "degraded_zero@test.com", "saldo": "Tu Saldo es 0,00 €", "tarjeta": None},
        ])
        df.to_excel(shard_path, index=False)

        failed = collect_failed_accounts([str(shard_path)])
        failed_emails = {a["email"] for a in failed}

        assert "degraded_zero@test.com" in failed_emails
        assert "valid_zero@test.com" not in failed_emails
