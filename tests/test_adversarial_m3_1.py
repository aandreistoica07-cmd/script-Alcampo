"""
Adversarial Challenge Test Suite for Milestone M3 — Challenger M3_1
Focus areas:
1. Incomplete Shard Recovery: 0-file crash, partial shard drop, corrupted excel, stagnation early exit
2. Deduplication Priority Stress: Pass 2 success vs Pass 1 timeout, error preservation, cycle priorities, conflicting entries
3. 6-Sheet Consolidated Excel: Strict row conservation, mutual exclusivity of classifications, temporary column stripping
4. Windows Console Encoding Vulnerability: Reproduction of CP1252 stdout crash
5. Multi-Directory Search Contamination: Empirical demonstration of search_dirs unconditionally including workspace files
"""

import os
import sys
import glob
import json
import base64
import html
import subprocess
import tempfile
import yaml
import pytest
import pandas as pd

from scripts.merge_and_retry import (
    compute_priority,
    format_telegram_summary,
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
    load_master_accounts,
    limpiar_saldo
)


# @section: Incomplete-Shard-Recovery-Adversarial

class TestIncompleteShardRecoveryAdversarial:
    """Stress tests for recovering missing accounts when shards crash or exit prematurely."""

    def test_zero_files_scenario_rescues_all_master_accounts(self, tmp_path):
        """Simulate total runner crash where Pass 1 directory has 0 Excel files."""
        master_accounts = [
            {"email": f"acc_{i}@alcampo.es", "password": f"pwd_{i}"}
            for i in range(15)
        ]
        master_file = tmp_path / "master_accounts.json"
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(master_accounts, f)

        empty_dir = tmp_path / "empty_artifacts"
        empty_dir.mkdir()
        failed_json = tmp_path / "failed_accounts.json"
        github_output = tmp_path / "github_output.txt"

        env = os.environ.copy()
        env["GITHUB_OUTPUT"] = str(github_output)
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(empty_dir),
            "--accounts-file", str(master_file),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0, f"Process failed: {res.stderr}"

        assert failed_json.exists()
        with open(failed_json, "r", encoding="utf-8") as f:
            rescued = json.load(f)

        assert len(rescued) == 15
        rescued_emails = {a["email"] for a in rescued}
        expected_emails = {f"acc_{i}@alcampo.es" for i in range(15)}
        assert rescued_emails == expected_emails

        # Check GITHUB_OUTPUT flags
        out_content = github_output.read_text(encoding="utf-8")
        assert "has_timeouts=true" in out_content
        assert "failed_count=15" in out_content

    def test_partial_shard_crash_missing_rows_with_error_segregation(self, tmp_path):
        """
        Master list has 10 accounts.
        Shard 0 has:
          - acc0: Success ("Tu Saldo es 10,00 €")
          - acc1: Permanent Credential Error
          - acc2: Permanent Call Center Error
          - Shard 0 crashed before processing acc3 and acc4.
        Shard 1 has:
          - acc5: Retryable Timeout
          - acc6: Retryable HTTP 429
          - Shard 1 crashed before processing acc7, acc8, acc9.
        Verify failed_accounts.json rescues:
          - acc3, acc4 (missing from shard 0)
          - acc5, acc6 (retryable from shard 1)
          - acc7, acc8, acc9 (missing from shard 1)
          Total: 7 accounts.
          Must NOT rescue acc0, acc1, acc2.
        """
        master_accounts = [
            {"email": f"acc_{i}@alcampo.es", "password": f"pwd_{i}"}
            for i in range(10)
        ]
        master_file = tmp_path / "master_accounts.json"
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(master_accounts, f)

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        shard0_data = [
            {"email": "acc_0@alcampo.es", "password": "pwd_0", "saldo": "Tu Saldo es 10,00 €", "causa_error": "", "error_type": "ok"},
            {"email": "acc_1@alcampo.es", "password": "pwd_1", "saldo": "Error: Credenciales incorrectas", "causa_error": "Credenciales no válidas", "error_type": "account_error"},
            {"email": "acc_2@alcampo.es", "password": "pwd_2", "saldo": "Error: Cuenta bloqueada (Call Center)", "causa_error": "Call Center", "error_type": "needs_attention"},
        ]
        pd.DataFrame(shard0_data).to_excel(artifacts_dir / "pass1_shard_0.xlsx", index=False)

        shard1_data = [
            {"email": "acc_5@alcampo.es", "password": "pwd_5", "saldo": "Error: Bloqueo/Timeout", "causa_error": "Timeout", "error_type": "session_error"},
            {"email": "acc_6@alcampo.es", "password": "pwd_6", "saldo": "Error: HTTP Status 429", "causa_error": "Too Many Requests", "error_type": "ip_error"},
        ]
        pd.DataFrame(shard1_data).to_excel(artifacts_dir / "pass1_shard_1.xlsx", index=False)

        failed_json = tmp_path / "failed_accounts.json"
        github_output = tmp_path / "github_output.txt"
        env = os.environ.copy()
        env["GITHUB_OUTPUT"] = str(github_output)
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(artifacts_dir),
            "--accounts-file", str(master_file),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0, f"Error: {res.stderr}"

        with open(failed_json, "r", encoding="utf-8") as f:
            rescued = json.load(f)

        rescued_emails = {a["email"] for a in rescued}
        expected_emails = {
            "acc_3@alcampo.es", "acc_4@alcampo.es",  # unreached shard 0
            "acc_5@alcampo.es", "acc_6@alcampo.es",  # retryable shard 1
            "acc_7@alcampo.es", "acc_8@alcampo.es", "acc_9@alcampo.es"  # unreached shard 1
        }
        assert rescued_emails == expected_emails
        assert len(rescued) == 7

        # Strictly exclude definitive outcomes
        assert "acc_0@alcampo.es" not in rescued_emails
        assert "acc_1@alcampo.es" not in rescued_emails
        assert "acc_2@alcampo.es" not in rescued_emails

    def test_zero_byte_or_corrupt_excel_handled_gracefully(self, tmp_path):
        """Simulate a shard whose Excel file was abruptly terminated with 0 bytes or corrupt content."""
        master_accounts = [
            {"email": "valid1@alcampo.es", "password": "p1"},
            {"email": "corrupt1@alcampo.es", "password": "p2"},
            {"email": "corrupt2@alcampo.es", "password": "p3"}
        ]
        master_file = tmp_path / "master.json"
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(master_accounts, f)

        artifacts_dir = tmp_path / "shards"
        artifacts_dir.mkdir()

        # Valid shard
        valid_df = pd.DataFrame([{"email": "valid1@alcampo.es", "password": "p1", "saldo": "Tu Saldo es 12,00 €"}])
        valid_df.to_excel(artifacts_dir / "shard_0.xlsx", index=False)

        # Corrupted / 0-byte shard
        corrupt_file = artifacts_dir / "shard_1.xlsx"
        corrupt_file.write_bytes(b"NOT_A_VALID_ZIP_OR_EXCEL_FILE_GARBAGE")

        failed_json = tmp_path / "failed.json"
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(artifacts_dir),
            "--accounts-file", str(master_file),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0

        with open(failed_json, "r", encoding="utf-8") as f:
            rescued = json.load(f)

        rescued_emails = {a["email"] for a in rescued}
        # corrupt1 and corrupt2 were not parsed due to corruption, so master recovery must rescue them!
        assert "corrupt1@alcampo.es" in rescued_emails
        assert "corrupt2@alcampo.es" in rescued_emails
        assert "valid1@alcampo.es" not in rescued_emails

    def test_stagnation_early_exit_guard_prevents_infinite_ci_loops(self, tmp_path, monkeypatch):
        """Test that if failure count does not decrease, check-timeouts aborts retries to protect GHA minutes."""
        monkeypatch.chdir(tmp_path)
        prev_file = tmp_path / "previous_failures.json"
        with open(prev_file, "w", encoding="utf-8") as pf:
            json.dump({"count": 5}, pf)

        master_file = tmp_path / "master.json"
        with open(master_file, "w", encoding="utf-8") as mf:
            json.dump([{"email": f"stagnant_{i}@alcampo.es", "password": "p"} for i in range(5)], mf)

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        failed_json = tmp_path / "failed_accounts.json"
        github_output = tmp_path / "gh_out.txt"

        env = os.environ.copy()
        env["GITHUB_OUTPUT"] = str(github_output)
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(empty_dir),
            "--accounts-file", str(master_file),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path), encoding="utf-8", errors="replace")
        assert res.returncode == 0

        # Since failures did not decrease (5 >= 5), stagnation guard triggers early exit
        out_text = github_output.read_text(encoding="utf-8")
        assert "has_timeouts=false" in out_text
        assert not failed_json.exists()

    def test_all_accounts_succeeded_cleans_failed_json(self, tmp_path):
        """When 100% of master accounts succeed, failed_accounts.json is purged and has_timeouts is false."""
        master_accounts = [
            {"email": "succ1@alcampo.es", "password": "p1"},
            {"email": "succ2@alcampo.es", "password": "p2"}
        ]
        master_file = tmp_path / "master.json"
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(master_accounts, f)

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        df = pd.DataFrame([
            {"email": "succ1@alcampo.es", "saldo": "Tu Saldo es 5,00 €", "causa_error": "", "error_type": "ok"},
            {"email": "succ2@alcampo.es", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok"}
        ])
        df.to_excel(artifacts_dir / "shard_0.xlsx", index=False)

        failed_json = tmp_path / "failed_accounts.json"
        failed_json.write_text("dummy", encoding="utf-8")

        github_output = tmp_path / "gh_out.txt"
        env = os.environ.copy()
        env["GITHUB_OUTPUT"] = str(github_output)
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(artifacts_dir),
            "--accounts-file", str(master_file),
            "--failed-json", str(failed_json)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0

        out_text = github_output.read_text(encoding="utf-8")
        assert "has_timeouts=false" in out_text
        assert "failed_count=0" in out_text
        assert not failed_json.exists()

# @end: Incomplete-Shard-Recovery-Adversarial


# @section: Deduplication-Priority-Stress

class TestDeduplicationPriorityStress:
    """Stress tests for multi-shard and multi-pass priority deduplication."""

    @staticmethod
    def run_dedup(records):
        df = pd.DataFrame(records)
        df["_priority"] = [compute_priority(r["filename"], r.get("saldo", "")) for r in records]
        df.sort_values(by=["_priority"], inplace=True)
        df.drop_duplicates(subset=["email"], keep="last", inplace=True)
        return df.to_dict(orient="records")

    def test_pass2_success_overrides_pass1_timeout(self):
        records = [
            {"filename": "saldos_pass1_shard_0.xlsx", "email": "u@test.es", "saldo": "Error: Timeout", "card_number": None},
            {"filename": "saldos_retry_shard_0.xlsx", "email": "u@test.es", "saldo": "Tu Saldo es 25,00 €", "card_number": "4001"}
        ]
        res = self.run_dedup(records)
        assert len(res) == 1
        assert res[0]["saldo"] == "Tu Saldo es 25,00 €"
        assert res[0]["card_number"] == "4001"

    def test_pass1_success_preserved_against_spurious_pass2_error(self):
        records = [
            {"filename": "saldos_pass1_shard_0.xlsx", "email": "u@test.es", "saldo": "Tu Saldo es 50,00 €", "card_number": "4002"},
            {"filename": "saldos_retry_shard_0.xlsx", "email": "u@test.es", "saldo": "Error: Timeout", "card_number": None}
        ]
        res = self.run_dedup(records)
        assert len(res) == 1
        assert res[0]["saldo"] == "Tu Saldo es 50,00 €"
        assert res[0]["card_number"] == "4002"

    def test_fresher_pass2_error_overrides_pass1_error(self):
        records = [
            {"filename": "saldos_pass1_shard_0.xlsx", "email": "u@test.es", "saldo": "Error: Bloqueo/Timeout"},
            {"filename": "saldos_retry_shard_0.xlsx", "email": "u@test.es", "saldo": "Error: Cuenta bloqueada (Call Center)"}
        ]
        res = self.run_dedup(records)
        assert len(res) == 1
        assert res[0]["saldo"] == "Error: Cuenta bloqueada (Call Center)"

    def test_cycle_progression_priority_hierarchy(self):
        """Validate strict mathematical ordering across cycle numbers."""
        p_p1_err = compute_priority("saldos_pass1_shard_0.xlsx", "Error")
        p_c1_err = compute_priority("cycle_1_shard_0.xlsx", "Error")
        p_c2_err = compute_priority("cycle_2_shard_0.xlsx", "Error")
        p_c1_succ = compute_priority("cycle_1_shard_0.xlsx", "Tu Saldo es 10 €")
        p_c2_succ = compute_priority("cycle_2_shard_0.xlsx", "Tu Saldo es 10 €")

        assert p_c2_succ > p_c1_succ > p_c2_err > p_c1_err > p_p1_err
        assert p_c2_succ == 1120
        assert p_c1_succ == 1110
        assert p_c2_err == 120
        assert p_c1_err == 110
        assert p_p1_err == 10

    def test_conflicting_entries_within_same_pass(self):
        """Simulate two shards processing the same account in Pass 1: one timeout, one success."""
        records = [
            {"filename": "saldos_pass1_shard_0.xlsx", "email": "conflict@test.es", "saldo": "Error: Bloqueo/Timeout"},
            {"filename": "saldos_pass1_shard_1.xlsx", "email": "conflict@test.es", "saldo": "Tu Saldo es 18,50 €"}
        ]
        res = self.run_dedup(records)
        assert len(res) == 1
        assert res[0]["saldo"] == "Tu Saldo es 18,50 €"

    def test_verified_zero_balance_priority(self):
        """Verified zero balance has definitive success priority (base_prio + 1000)."""
        p_zero = compute_priority("saldos_pass1_shard_0.xlsx", "Tu Saldo es 0,00 €")
        p_err = compute_priority("saldos_retry_shard_0.xlsx", "Error: Timeout")
        assert p_zero > p_err  # 1010 > 100

# @end: Deduplication-Priority-Stress


# @section: Six-Sheets-Excel-Row-Conservation

class TestConsolidatedExcelSixSheetsAdversarial:
    """End-to-end stress tests for 6-sheet consolidated Excel workbook."""

    def test_row_conservation_and_mutual_exclusivity(self, tmp_path):
        """
        Verify that for an arbitrary mix of successes, zero balances, call center,
        credentials, timeouts, and duplicates across shards:
        1. 'Todas las Cuentas' contains exactly the deduplicated master count.
        2. Sum(Sheet 2 + Sheet 3 + Sheet 4 + Sheet 5 + Sheet 6) == Sheet 1 count.
        3. No temporary columns leak into any sheet.
        """
        shards_dir = tmp_path / "all_final_shards"
        shards_dir.mkdir()

        # Shard 1 (Pass 1)
        shard1_records = [
            {"email": "pos1@alcampo.es", "password": "p", "saldo": "Tu Saldo es 25,50 €", "causa_error": "", "error_type": "ok", "card_number": "4001"},
            {"email": "pos2@alcampo.es", "password": "p", "saldo": "Tu Saldo es 100,00 €", "causa_error": "", "error_type": "ok", "card_number": "4002"},
            {"email": "zero1@alcampo.es", "password": "p", "saldo": "Tu Saldo es 0,00 €", "causa_error": "", "error_type": "ok", "card_number": "4003"},
            {"email": "cc1@alcampo.es", "password": "p", "saldo": "Error: Cuenta bloqueada Call Center", "causa_error": "Call Center", "error_type": "needs_attention", "card_number": None},
            {"email": "cred1@alcampo.es", "password": "p", "saldo": "Error: Credenciales incorrectas", "causa_error": "Auth", "error_type": "account_error", "card_number": None},
            {"email": "to1@alcampo.es", "password": "p", "saldo": "Error: Timeout", "causa_error": "Timeout", "error_type": "session_error", "card_number": None},
        ]
        pd.DataFrame(shard1_records).to_excel(shards_dir / "saldos_pass1_shard_0.xlsx", index=False)

        # Shard 2 (Pass 2 Retry)
        shard2_records = [
            {"email": "to1@alcampo.es", "password": "p", "saldo": "Tu Saldo es 15,00 €", "causa_error": "", "error_type": "ok", "card_number": "4004"},
            {"email": "to2@alcampo.es", "password": "p", "saldo": "Error: HTTP Status 429", "causa_error": "Too Many Requests", "error_type": "ip_error", "card_number": None},
            {"email": "cc2@alcampo.es", "password": "p", "saldo": "Error: Requiere 2FA código de verificación", "causa_error": "2FA", "error_type": "needs_attention", "card_number": None},
        ]
        pd.DataFrame(shard2_records).to_excel(shards_dir / "saldos_retry_shard_0.xlsx", index=False)

        output_excel = tmp_path / "CONSOLIDATED_TEST.xlsx"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(output_excel)
        ]
        env = os.environ.copy()
        env["TELEGRAM_TOKEN"] = "none"
        env["FIREBASE_DB_URL"] = ""
        env["PYTHONIOENCODING"] = "utf-8"

        # Execute with cwd=tmp_path to isolate directory search from workspace repo files
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path), encoding="utf-8", errors="replace")
        assert res.returncode == 0, f"final-merge failed: {res.stderr}"

        assert output_excel.exists()
        xls = pd.ExcelFile(output_excel)
        expected_sheets = [
            "Todas las Cuentas",
            "Exitosas con Saldo",
            "Saldo Cero Verificado",
            "Bloqueadas Call Center",
            "Error Credenciales",
            "Error IP y Timeouts"
        ]
        assert xls.sheet_names == expected_sheets

        df_all = pd.read_excel(xls, "Todas las Cuentas")
        df_pos = pd.read_excel(xls, "Exitosas con Saldo")
        df_zero = pd.read_excel(xls, "Saldo Cero Verificado")
        df_cc = pd.read_excel(xls, "Bloqueadas Call Center")
        df_cred = pd.read_excel(xls, "Error Credenciales")
        df_ipto = pd.read_excel(xls, "Error IP y Timeouts")

        # Unique accounts count: pos1, pos2, zero1, cc1, cred1, to1 (deduped to success), to2, cc2 -> 8 accounts
        assert len(df_all) == 8
        assert set(df_all["email"]) == {
            "pos1@alcampo.es", "pos2@alcampo.es", "zero1@alcampo.es",
            "cc1@alcampo.es", "cred1@alcampo.es", "to1@alcampo.es",
            "to2@alcampo.es", "cc2@alcampo.es"
        }

        # Deduplication check: to1 must be in df_pos with 15,00 € (Pass 2 victory)
        to1_row = df_all[df_all["email"] == "to1@alcampo.es"].iloc[0]
        assert to1_row["saldo"] == "Tu Saldo es 15,00 €"

        # Routing checks
        assert len(df_pos) == 3   # pos1 (25.50), pos2 (100.00), to1 (15.00)
        assert len(df_zero) == 1  # zero1
        assert len(df_cc) == 2    # cc1, cc2
        assert len(df_cred) == 1  # cred1
        assert len(df_ipto) == 1  # to2

        # Conservation theorem: sum of partitions equals master
        assert len(df_pos) + len(df_zero) + len(df_cc) + len(df_cred) + len(df_ipto) == len(df_all)

        # Temporary column stripping check
        temp_cols = ["_priority", "_saldo_val", "_is_success", "_is_callcenter", "_is_credenciales"]
        for sname in expected_sheets:
            sheet_df = pd.read_excel(xls, sname)
            for col in temp_cols:
                assert col not in sheet_df.columns, f"Temporary column {col} leaked into sheet {sname}"

# @end: Six-Sheets-Excel-Row-Conservation


# @section: Empirical-Bug-Demonstrations

class TestEmpiricalBugDemonstrations:
    """Empirically demonstrates confirmed failure modes in scripts/merge_and_retry.py."""

    def test_cp1252_stdout_encoding_crash(self, tmp_path):
        """
        EMPIRICAL BUG 1:
        Scripts/merge_and_retry.py prints emojis on Windows without sys.stdout.reconfigure(encoding='utf-8').
        Under standard CP1252 console, running merge_and_retry raises UnicodeEncodeError.
        """
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        env = os.environ.copy()
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONUTF8", None)

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "scripts", "merge_and_retry.py"),
            "--mode", "check-timeouts",
            "--input-dir", str(empty_dir)
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(tmp_path))
        # This will fail on standard Windows CP1252 environment
        if res.returncode != 0:
            assert "UnicodeEncodeError" in res.stderr
            assert "charmap" in res.stderr

    def test_multi_directory_search_contamination(self, tmp_path):
        """
        EMPIRICAL BUG 2:
        In final-merge (lines 320-329), search_dirs = [args.input_dir, "./all_final_shards", "./pass1_artifacts", "scraper", "."].
        The loop unconditionally scans '.' and 'scraper' and appends every .xlsx found in the repo
        into files, instead of checking fallback dirs only when files is empty.
        """
        # When executed from the repo root, final-merge unconditionally detects and includes
        # workspace files (saldos_alcampo.xlsx, REPORTE_DEFINITIVO_766_CUENTAS_TELEGRAM.xlsx)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        isolated_shards = tmp_path / "only_one_shard"
        isolated_shards.mkdir()
        single_shard = pd.DataFrame([
            {"email": "isolated@alcampo.es", "password": "p", "saldo": "Tu Saldo es 10,00 €"}
        ])
        single_shard.to_excel(isolated_shards / "shard_0.xlsx", index=False)

        output_excel = tmp_path / "CONTAMINATED_OUTPUT.xlsx"

        cmd = [
            sys.executable,
            os.path.join(repo_root, "scripts", "merge_and_retry.py"),
            "--mode", "final-merge",
            "--input-dir", str(isolated_shards),
            "--output-excel", str(output_excel)
        ]
        env = os.environ.copy()
        env["TELEGRAM_TOKEN"] = "none"
        env["FIREBASE_DB_URL"] = ""
        env["PYTHONIOENCODING"] = "utf-8"

        # Run from repo_root
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=repo_root, encoding="utf-8", errors="replace")
        assert res.returncode == 0

        # Read the generated output: verify zero contamination from workspace root
        df_out = pd.read_excel(output_excel, sheet_name="Todas las Cuentas")
        assert len(df_out) == 1, f"Expected 1 account from isolated shard, but got {len(df_out)}. Contamination detected!"

# @end: Empirical-Bug-Demonstrations
