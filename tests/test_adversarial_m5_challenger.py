"""
Adversarial Challenge Test Suite for Milestone M5_1 (White-Box Coverage Audit & Tier 5 Adversarial Challenger)
Focus areas:
1. scripts/local_test.py and scripts/merge_and_retry.py extreme inputs and boundary conditions
2. AccountCooldownManager and CircuitBreaker high-concurrency stress, lock contention, and invariants
3. Corrupted, partial, or malformed Excel shards and master recovery in merge_and_retry.py
"""

import os
import sys
import json
import time
import math
import tempfile
import threading
from pathlib import Path
from unittest import mock
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import pandas as pd

from scraper.account_cooldown_manager import AccountCooldownManager
from scraper.script_optimizado import CircuitBreaker
from scripts.local_test import (
    load_accounts_from_file,
    export_to_excel,
    print_summary_table,
    parse_arguments,
)
from scripts.merge_and_retry import (
    collect_failed_accounts,
    generate_consolidated_excel,
    compute_priority,
    format_telegram_summary,
    is_definitive_success,
    is_definitive_error,
    is_retryable_failure,
    limpiar_saldo,
)


# ==============================================================================
# SECTION 1: Extreme Inputs in scripts/local_test.py
# ==============================================================================

class TestLocalTestExtremeInputsAdversarial:
    """Stress tests challenging assumptions in scripts/local_test.py with adversarial inputs."""

    def test_load_accounts_csv_extreme_inputs_and_malformed_cells(self, tmp_path):
        """CSV with numeric emails, leading/trailing whitespace, NaN, and Spanish unicode passwords."""
        csv_file = tmp_path / "extreme_accounts.csv"
        csv_content = (
            "email,password\n"
            "   user_spaces@alcampo.es   ,  pwd_with_spaces  \n"
            "987654321,123456\n"  # Numeric email and password
            "josé.niño@españa.es,contraseña_con_ñ_y_€!@#\n"  # Spanish chars + euro
            ",\n"  # Empty row
            "missing_pwd@alcampo.es,\n"  # Missing password
            ",missing_email_pwd\n"  # Missing email
            "valid@alcampo.es,valid_pwd\n"
        )
        csv_file.write_text(csv_content, encoding="utf-8")

        accs = load_accounts_from_file(str(csv_file))

        # Only rows where both email and password are truthy strings should be loaded
        emails = [a["email"] for a in accs]
        assert "user_spaces@alcampo.es" in emails
        assert "987654321" in emails
        assert "josé.niño@españa.es" in emails
        assert "valid@alcampo.es" in emails
        assert "" not in emails
        # Ensure password with spaces is stripped
        user_sp = next(a for a in accs if a["email"] == "user_spaces@alcampo.es")
        assert user_sp["password"] == "pwd_with_spaces"

    def test_load_accounts_excel_extreme_inputs_and_formulas(self, tmp_path):
        """Excel with numeric types, formula strings, empty rows, and unicode."""
        excel_file = tmp_path / "extreme_accounts.xlsx"
        df_raw = pd.DataFrame([
            {"email": "formula@alcampo.es", "password": "=SUM(1,2)"},
            {"email": "numeric_pwd@alcampo.es", "password": 987654},
            {"email": None, "password": "no_email"},
            {"email": "no_pwd@alcampo.es", "password": None},
            {"email": "emoji@alcampo.es", "password": "p@ss💰💳🚀"},
        ])
        df_raw.to_excel(excel_file, index=False)

        accs = load_accounts_from_file(str(excel_file))
        # Note: pandas converts empty cells to float('nan'). In Python, bool(float('nan')) is True.
        # Consequently, load_accounts_from_file ingests empty cells as the string 'nan'.
        assert len(accs) == 5
        emails = {a["email"] for a in accs}
        assert "formula@alcampo.es" in emails
        assert "numeric_pwd@alcampo.es" in emails
        assert "emoji@alcampo.es" in emails
        assert "nan" in emails, "Empirical observation: empty Excel cells evaluate to truthy float('nan') and become 'nan'"
        num_acc = next(a for a in accs if a["email"] == "numeric_pwd@alcampo.es")
        assert num_acc["password"] == "987654"

    def test_load_accounts_json_root_types_and_edge_structures(self, tmp_path):
        """JSON where root is not a list/dict, or dict has no list values."""
        # Case A: JSON is integer
        int_file = tmp_path / "int_root.json"
        int_file.write_text("12345", encoding="utf-8")
        assert load_accounts_from_file(str(int_file)) == []

        # Case B: JSON is boolean
        bool_file = tmp_path / "bool_root.json"
        bool_file.write_text("true", encoding="utf-8")
        assert load_accounts_from_file(str(bool_file)) == []

        # Case C: JSON is dict with non-list values
        dict_file = tmp_path / "dict_no_list.json"
        dict_file.write_text(json.dumps({"status": "ok", "count": 0}), encoding="utf-8")
        assert load_accounts_from_file(str(dict_file)) == []

    def test_export_to_excel_empty_results_and_none_fields(self, tmp_path):
        """export_to_excel with 0 results or None fields should write a clean valid Excel file."""
        out_excel = tmp_path / "subfolder" / "results.xlsx"

        # Case A: Empty results list
        export_to_excel([], str(out_excel))
        assert out_excel.exists()
        df_empty = pd.read_excel(out_excel)
        assert len(df_empty) == 0

        # Case B: Results with None fields and extreme values
        results = [
            {
                "email": "test@alcampo.es",
                "password": "pwd",
                "balance": None,
                "card_number": None,
                "status": "failed",
                "error_type": "ip_error",
                "error_reason": "HTTP 429",
                "duration": 0.0,
            },
            {
                "email": "rich@alcampo.es",
                "password": "pwd",
                "balance": 999999.99,
                "card_number": "4002001111111",
                "status": "success",
                "error_type": "none",
                "error_reason": None,
                "duration": 12.34,
            }
        ]
        out_excel_2 = tmp_path / "results_rich.xlsx"
        export_to_excel(results, str(out_excel_2))
        assert out_excel_2.exists()
        df_read = pd.read_excel(out_excel_2)
        assert len(df_read) == 2
        assert df_read.iloc[0]["saldo"] == "0,00 €"
        assert "999999.99" in str(df_read.iloc[1]["saldo"])

    def test_print_summary_table_zero_division_and_none_balances(self, capsys):
        """print_summary_table should handle empty results and None balances without ZeroDivisionError."""
        # Case A: Empty results
        print_summary_table([])
        captured = capsys.readouterr()
        assert "Total Cuentas: 0 | Éxitos: 0 | Saldo Acumulado: 0.00 €" in captured.out

        # Case B: Mix of None balances and extreme balances
        results = [
            {"masked_email": "t***1@a***.es", "balance": None, "card_number": None, "status": "failed", "duration": 0.1},
            {"masked_email": "t***2@a***.es", "balance": 0.0, "card_number": "4002000000000", "status": "success", "duration": 2.5},
            {"masked_email": "t***3@a***.es", "balance": 50.25, "card_number": "4002001111111", "status": "success", "duration": 1.2},
        ]
        print_summary_table(results)
        captured = capsys.readouterr()
        assert "Total Cuentas: 3 | Éxitos: 2 | Saldo Acumulado: 50.25 €" in captured.out

    def test_parse_arguments_boundary_flags(self):
        """Test parse_arguments with extreme flag combinations."""
        test_cases = [
            ["scripts/local_test.py", "--email", "user@test.es", "--password", "pwd", "--headless", "--timeout", "10"],
            ["scripts/local_test.py", "--input-file", "accs.json", "--limit", "5", "--slowmo", "1.5"],
            ["scripts/local_test.py", "--headful", "--output-excel", "out.xlsx"],
        ]
        for argv in test_cases:
            with mock.patch("sys.argv", argv):
                args = parse_arguments()
                assert args is not None


# ==============================================================================
# SECTION 2: Concurrency & Lock Contention in AccountCooldownManager
# ==============================================================================

class TestAccountCooldownManagerConcurrencyAndContention:
    """Stress tests challenging thread-safety, lock contention, and invariants of AccountCooldownManager."""

    def test_high_concurrency_record_result_data_invariants(self, tmp_path):
        """50 concurrent threads executing 1,000 operations on shared AccountCooldownManager.
        Verifies no data races, accurate counters, and valid metrics."""
        status_file = tmp_path / "concurrent_manager_status.json"
        mgr = AccountCooldownManager(status_file_path=str(status_file))

        num_threads = 50
        ops_per_thread = 20
        accounts_pool = [f"shared_user_{i}@alcampo.es" for i in range(10)]

        def worker(thread_id):
            for op in range(ops_per_thread):
                acc = accounts_pool[(thread_id + op) % len(accounts_pool)]
                is_succ = (op % 3 == 0)
                date_str = f"2026-10-{(10 + (op % 10)):02d}"
                err = None if is_succ else f"Thread {thread_id} error"
                mgr.record_result(email=acc, is_success=is_succ, error_msg=err, today_str=date_str)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            for f in as_completed(futures):
                f.result()  # Must not raise exceptions

        mgr.save()

        # Invariant checks
        with mgr.lock:
            accounts_data = mgr.data["accounts"]
            assert len(accounts_data) == len(accounts_pool)

            total_recorded_checks = 0
            for email, rec in accounts_data.items():
                total_checks = rec["total_checks"]
                total_success = rec["total_success"]
                total_failures = rec["total_failures"]
                # Invariant: total_checks == total_success + total_failures
                assert total_checks == total_success + total_failures, (
                    f"Invariant violated for {email}: {total_checks} != {total_success} + {total_failures}"
                )
                total_recorded_checks += total_checks

            # Invariant: exactly 50 * 20 = 1000 checks performed
            assert total_recorded_checks == num_threads * ops_per_thread

            # Invariant: metrics consistent with accounts dictionary
            assert mgr.data["metrics"]["total_tracked"] == len(accounts_pool)
            assert (
                mgr.data["metrics"]["active_count"] + mgr.data["metrics"]["cooling_down_count"]
                == len(accounts_pool)
            )

    def test_heavy_lock_contention_unpause_filter_save_simultaneous(self, tmp_path):
        """Simultaneous high-frequency contention between record_result, filter_accounts_for_run,
        unpause_all_cooldowns, and save across 30 concurrent threads."""
        status_file = tmp_path / "contention_stress.json"
        mgr = AccountCooldownManager(status_file_path=str(status_file))

        # Pre-seed 20 accounts
        accounts_list = [{"email": f"acc_{i}@alcampo.es"} for i in range(20)]
        for a in accounts_list:
            mgr.record_result(a["email"], is_success=False, today_str="2026-10-20")
        mgr.save()

        stop_barrier = threading.Event()
        errors = []

        def recorder_thread(tid):
            try:
                iteration = 0
                while not stop_barrier.is_set() and iteration < 50:
                    email = f"acc_{iteration % 20}@alcampo.es"
                    mgr.record_result(email, is_success=(iteration % 4 == 0), today_str=f"2026-10-{(21 + (iteration % 8)):02d}")
                    iteration += 1
            except Exception as e:
                errors.append(f"Recorder {tid}: {e}")

        def reader_thread(tid):
            try:
                iteration = 0
                while not stop_barrier.is_set() and iteration < 50:
                    mgr.filter_accounts_for_run(accounts_list, today_str="2026-10-25")
                    iteration += 1
            except Exception as e:
                errors.append(f"Reader {tid}: {e}")

        def unpause_thread(tid):
            try:
                iteration = 0
                while not stop_barrier.is_set() and iteration < 10:
                    mgr.unpause_all_cooldowns()
                    time.sleep(0.005)
                    iteration += 1
            except Exception as e:
                errors.append(f"Unpause {tid}: {e}")

        threads = []
        for i in range(15):
            threads.append(threading.Thread(target=recorder_thread, args=(i,)))
        for i in range(10):
            threads.append(threading.Thread(target=reader_thread, args=(i,)))
        for i in range(5):
            threads.append(threading.Thread(target=unpause_thread, args=(i,)))

        for t in threads:
            t.start()

        # Let them run concurrently
        for t in threads:
            t.join(timeout=10)

        stop_barrier.set()
        assert errors == [], f"Thread contention errors encountered: {errors}"

    def test_cooldown_manager_input_sanitization_and_date_boundaries(self, tmp_path):
        """Sanitization of whitespace around email, multiple checks on same date, and recovery."""
        mgr = AccountCooldownManager(status_file_path=str(tmp_path / "sanitize.json"))

        email_dirty = "   user_clean@alcampo.es \t \n"
        email_clean = "user_clean@alcampo.es"

        # Check 1: Leading/trailing whitespace should be stripped
        mgr.record_result(email_dirty, is_success=False, today_str="2026-10-20")
        acc = mgr.get_account_status(email_clean)
        assert acc is not None
        assert acc["consecutive_failures"] == 1

        # Check 2: Repeated failure on the SAME date does NOT increment consecutive_failures
        mgr.record_result(email_clean, is_success=False, today_str="2026-10-20")
        assert mgr.get_account_status(email_clean)["consecutive_failures"] == 1
        assert mgr.get_account_status(email_clean)["total_failures"] == 2

        # Check 3: Failures on distinct consecutive dates up to 5 days
        for day in [21, 22, 23, 24]:
            res = mgr.record_result(email_clean, is_success=False, today_str=f"2026-10-{day:02d}")

        assert res["action"] == "entered_cooldown"
        assert res["status"] == "cooling_down"
        assert res["cooldown_until"] == "2026-10-29"

        # Check 4: Success while cooling_down recovers the account immediately
        res_rec = mgr.record_result(email_clean, is_success=True, today_str="2026-10-25")
        assert res_rec["action"] == "recovered"
        assert res_rec["status"] == "active"
        assert res_rec["consecutive_failures"] == 0


# ==============================================================================
# SECTION 3: Concurrency & Lock Contention in CircuitBreaker
# ==============================================================================

class TestCircuitBreakerConcurrencyAndLockContention:
    """Stress tests challenging CircuitBreaker thread safety, boundary races, and error classification."""

    def test_circuit_breaker_high_concurrency_race(self):
        """50 concurrent threads executing 1,000 record_result calls on a single CircuitBreaker.
        Validates total_processed, total_server_errors, and thread-safe locking."""
        cb = CircuitBreaker(max_consecutive_failures=20, max_failure_ratio=0.80, min_processed_threshold=100)

        num_threads = 50
        ops_per_thread = 20

        def worker(tid):
            for i in range(ops_per_thread):
                is_server = ((tid + i) % 5 == 0)
                err_type = "ip_error" if is_server else "ok"
                cb.record_result(is_server_error=is_server, reason="Stress test", error_type=err_type)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        # Invariant checks
        with cb.lock:
            assert cb.total_processed == num_threads * ops_per_thread
            expected_server_errors = sum(
                1 for t in range(num_threads) for i in range(ops_per_thread) if (t + i) % 5 == 0
            )
            assert cb.total_server_errors == expected_server_errors

    def test_circuit_breaker_consecutive_trip_exact_boundary_race(self):
        """Pre-fill CircuitBreaker to threshold - 1, then race 20 threads to trip it.
        Validates that transition to triggered=True happens safely with valid trigger_reason."""
        cb = CircuitBreaker(max_consecutive_failures=5, max_failure_ratio=0.50, min_processed_threshold=10)

        # Pre-fill with 4 consecutive errors
        for _ in range(4):
            cb.record_result(is_server_error=True, reason="WAF 429", error_type="ip_error")
        assert cb.triggered is False

        # Race 20 threads to trigger the 5th error
        def trip_worker():
            return cb.record_result(is_server_error=True, reason="Cloudflare 503", error_type="ip_error")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(trip_worker) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        assert cb.triggered is True
        assert "caídas consecutivas" in cb.trigger_reason or "% de errores" in cb.trigger_reason
        # At least one call must have returned (True, reason)
        assert any(r[0] is True for r in results)

    def test_circuit_breaker_classify_error_extreme_inputs(self):
        """classify_error should handle None, non-standard types, and massive HTML without unhandled exceptions."""
        cb = CircuitBreaker()

        # Case A: None page_source and None error_msg
        category, reason = cb.classify_error(status_code=None, page_source=None, error_msg=None)
        assert category in ("needs_attention", "account_error", "session_error", "ip_error")

        # Case B: HTTP status code variations
        for code in [403, 429, 500, 502, 503, 504, 520, 521, 522, 524, 525, 526]:
            cat, rsn = cb.classify_error(status_code=code)
            assert cat == "ip_error"
            assert str(code) in rsn

        # Case C: Massive 500KB HTML string
        huge_html = "<html><body>" + ("<div>Normal content</div>" * 25000) + "</body></html>"
        cat, rsn = cb.classify_error(page_source=huge_html)
        assert cat == "account_error"

        # Case D: Massive HTML with embedded Cloudflare Ray ID
        huge_cf = huge_html + "<span>Cloudflare Ray ID: 987654321</span>"
        cat, rsn = cb.classify_error(page_source=huge_cf)
        assert cat == "ip_error"

        # Case E: String status_code triggers TypeError in Python 3 comparison
        with pytest.raises(TypeError, match="not supported between instances of 'int' and 'str'"):
            cb.classify_error(status_code="500")


# ==============================================================================
# SECTION 4: Corrupted, Partial & Extreme Excel Files in merge_and_retry.py
# ==============================================================================

class TestMergeAndRetryCorruptedAndPartialExcelAdversarial:
    """Stress tests challenging merge_and_retry.py with corrupted files, missing columns, and data recovery."""

    def test_corrupted_excel_shards_resilience_and_partial_recovery(self, tmp_path):
        """Directory containing 0-byte, random noise, and truncated zip shards alongside a valid shard."""
        shards_dir = tmp_path / "shards"
        shards_dir.mkdir()

        # 1. Corrupted shard: 0 bytes
        f_empty = shards_dir / "shard_0_pass1.xlsx"
        f_empty.write_bytes(b"")

        # 2. Corrupted shard: random binary noise
        f_noise = shards_dir / "shard_1_pass1.xlsx"
        f_noise.write_bytes(b"\x00\xff\xfe\x12\x34\x56\x78\x9a\xbc\xde\xf0" * 20)

        # 3. Corrupted shard: truncated zip header
        f_trunc = shards_dir / "shard_2_pass1.xlsx"
        f_trunc.write_bytes(b"PK\x03\x04\x14\x00\x08\x00")

        # 4. Valid shard with 1 success and 1 session error
        f_valid = shards_dir / "shard_3_pass1.xlsx"
        df_valid = pd.DataFrame([
            {"email": "succ@alcampo.es", "password": "p1", "saldo": "Tu Saldo es 15,50 €", "causa_error": "", "error_type": "ok"},
            {"email": "retry_me@alcampo.es", "password": "p2", "saldo": "Error: Timeout", "causa_error": "Timeout", "error_type": "session_error"},
        ])
        df_valid.to_excel(f_valid, index=False)

        # Master accounts containing unreached account
        master_accounts = [
            {"email": "succ@alcampo.es", "password": "p1"},
            {"email": "retry_me@alcampo.es", "password": "p2"},
            {"email": "unreached@alcampo.es", "password": "p3"},
        ]

        # Scan shards
        files = [str(f_empty), str(f_noise), str(f_trunc), str(f_valid)]
        failed = collect_failed_accounts(files, master_accounts=master_accounts)

        # 'succ@alcampo.es' must NOT be collected (definitive success)
        # 'retry_me@alcampo.es' must be collected (retryable session_error)
        # 'unreached@alcampo.es' must be rescued (omitted from shards)
        failed_emails = {a["email"] for a in failed}
        assert "succ@alcampo.es" not in failed_emails
        assert "retry_me@alcampo.es" in failed_emails
        assert "unreached@alcampo.es" in failed_emails

    def test_all_shards_corrupted_rescues_100_percent_of_master_accounts(self, tmp_path):
        """If 100% of shard Excel files are completely corrupted, all master accounts must be rescued."""
        corrupt_dir = tmp_path / "all_corrupted"
        corrupt_dir.mkdir()

        corrupt_files = []
        for i in range(5):
            f = corrupt_dir / f"shard_{i}_pass1.xlsx"
            f.write_bytes(b"NON_EXCEL_TRASH_DATA" * 5)
            corrupt_files.append(str(f))

        master_accounts = [
            {"email": f"rescued_{i}@alcampo.es", "password": f"pwd_{i}"}
            for i in range(12)
        ]

        failed = collect_failed_accounts(corrupt_files, master_accounts=master_accounts)
        assert len(failed) == 12
        failed_emails = {a["email"] for a in failed}
        expected_emails = {f"rescued_{i}@alcampo.es" for i in range(12)}
        assert failed_emails == expected_emails

    def test_partial_excel_missing_all_expected_columns(self, tmp_path):
        """Excel shards missing standard columns must not crash collect_failed_accounts or generate_consolidated_excel."""
        bad_col_file = tmp_path / "bad_cols_shard.xlsx"
        df_bad = pd.DataFrame([
            {"unexpected_col_A": 123, "unexpected_col_B": "foo"},
            {"unexpected_col_A": 456, "unexpected_col_B": "bar"},
        ])
        df_bad.to_excel(bad_col_file, index=False)

        # 1. collect_failed_accounts ignores rows with missing email
        failed = collect_failed_accounts([str(bad_col_file)])
        assert failed == []

        # 2. generate_consolidated_excel fills missing columns and routes safely to Sheet 6
        sheets = generate_consolidated_excel(df_bad)
        assert len(sheets["Todas las Cuentas"]) == 2
        # Since missing email/saldo is not success, not callcenter, not credenciales, goes to Sheet 6
        assert len(sheets["Error IP y Timeouts"]) == 2

    def test_generate_consolidated_excel_extreme_scale_row_conservation_and_mutual_exclusivity(self, tmp_path):
        """1,000 accounts dataset: verify strict row conservation, mutual exclusivity, and column stripping."""
        rows = []
        for i in range(1000):
            mod = i % 5
            if mod == 0:
                rows.append({"email": f"pos_{i}@test.es", "saldo": f"Tu Saldo es {i * 1.5:.2f} €", "card_number": "4002001111111", "causa_error": "", "error_type": "ok"})
            elif mod == 1:
                rows.append({"email": f"zero_{i}@test.es", "saldo": "Tu Saldo es 0,00 €", "card_number": "4002002222222", "causa_error": "", "error_type": "ok"})
            elif mod == 2:
                rows.append({"email": f"cc_{i}@test.es", "saldo": "Error: Call Center", "card_number": None, "causa_error": "Cuenta bloqueada Call Center", "error_type": "needs_attention"})
            elif mod == 3:
                rows.append({"email": f"cred_{i}@test.es", "saldo": "Error: Credenciales", "card_number": None, "causa_error": "Usuario o contraseña incorrectos", "error_type": "account_error"})
            else:
                rows.append({"email": f"ip_{i}@test.es", "saldo": "Error: Timeout", "card_number": None, "causa_error": "Cloudflare Ray ID 429", "error_type": "ip_error"})

        df_master = pd.DataFrame(rows)
        out_path = tmp_path / "consolidated_1000.xlsx"
        sheets = generate_consolidated_excel(df_master, str(out_path))

        assert out_path.exists()

        # Invariant 1: Row conservation
        total_rows = len(sheets["Todas las Cuentas"])
        cat_sum = (
            len(sheets["Exitosas con Saldo"])
            + len(sheets["Saldo Cero Verificado"])
            + len(sheets["Bloqueadas Call Center"])
            + len(sheets["Error Credenciales"])
            + len(sheets["Error IP y Timeouts"])
        )
        assert total_rows == 1000
        assert cat_sum == 1000, f"Row conservation violated: {total_rows} != {cat_sum}"

        # Invariant 2: Mutual exclusivity (disjoint email sets across Sheets 2 to 6)
        s_pos = set(sheets["Exitosas con Saldo"]["email"])
        s_zero = set(sheets["Saldo Cero Verificado"]["email"])
        s_cc = set(sheets["Bloqueadas Call Center"]["email"])
        s_cred = set(sheets["Error Credenciales"]["email"])
        s_ip = set(sheets["Error IP y Timeouts"]["email"])

        assert s_pos.isdisjoint(s_zero)
        assert s_pos.isdisjoint(s_cc)
        assert s_pos.isdisjoint(s_cred)
        assert s_pos.isdisjoint(s_ip)
        assert s_zero.isdisjoint(s_cc)
        assert s_zero.isdisjoint(s_cred)
        assert s_zero.isdisjoint(s_ip)
        assert s_cc.isdisjoint(s_cred)
        assert s_cc.isdisjoint(s_ip)
        assert s_cred.isdisjoint(s_ip)

        # Invariant 3: Stripping of temporary columns
        forbidden_cols = {"_priority", "_saldo_val", "_is_success", "_is_callcenter", "_is_credenciales"}
        for sname, sdf in sheets.items():
            intersection = forbidden_cols.intersection(sdf.columns)
            assert len(intersection) == 0, f"Sheet '{sname}' leaked temporary columns: {intersection}"

    def test_compute_priority_extreme_filename_variations(self):
        """compute_priority should handle malformed filenames, extreme cycle numbers, and success boosts."""
        # Baseline priority
        assert compute_priority("shard_1_pass1.xlsx", "Error") == 10

        # Success boost (+1000)
        assert compute_priority("shard_1_pass1.xlsx", "Tu Saldo es 10,00 €") == 1010

        # Pass 2 and retry filenames (base 100)
        assert compute_priority("pass2_shard_1.xlsx", "Error") == 100
        assert compute_priority("retry_shard.xlsx", "Error") == 100
        assert compute_priority("pass2_shard_1.xlsx", "Tu Saldo es 5,00 €") == 1100

        # Cycles progression (100 + c_num * 10)
        assert compute_priority("cycle_1.xlsx", "Error") == 110
        assert compute_priority("cycle_3.xlsx", "Error") == 130
        assert compute_priority("cycle_10.xlsx", "Error") == 200

        # Malformed cycle filename falls back gracefully to 100
        assert compute_priority("cycle_notanumber.xlsx", "Error") == 100

    def test_collect_failed_accounts_null_email_in_master_accounts(self):
        """Adversarial check: master_accounts containing None or 'nan' email strings.
        Empirical finding: str(acc.get('email', '')).strip() stringifies None into 'None'."""
        master_with_null = [
            {"email": None, "password": "pwd1"},
            {"email": "valid@alcampo.es", "password": "pwd2"},
        ]
        failed = collect_failed_accounts([], master_accounts=master_with_null)
        failed_emails = {a["email"] for a in failed}
        assert "valid@alcampo.es" in failed_emails
        assert "None" in failed_emails, "Empirical observation: None email in master accounts becomes literal 'None'"

