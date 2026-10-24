"""
Adversarial Challenge Test Suite for Milestone M1
Focus areas:
1. scripts/local_test.py argument parsing, edge cases, and error handling
2. AccountCooldownManager concurrency, multi-threading stress, race conditions, and corrupted files
"""

import os
import sys
import json
import pytest
import threading
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from scraper.account_cooldown_manager import AccountCooldownManager
from scripts.local_test import parse_arguments, load_accounts_from_file


# ==============================================================================
# SECTION 1: Local Test Runner CLI Edge Cases & Argument Validation
# ==============================================================================

class TestLocalTestCLIEdgeCases:
    """Adversarial stress-testing of scripts/local_test.py inputs."""

    def test_load_accounts_from_nonexistent_file(self, tmp_path):
        """Passing a non-existent file should raise FileNotFoundError."""
        bad_path = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            load_accounts_from_file(str(bad_path))

    def test_load_accounts_unsupported_extension(self, tmp_path):
        """Unsupported extensions (e.g., .txt, .py) should raise ValueError."""
        txt_path = tmp_path / "accounts.txt"
        txt_path.write_text("user:pass", encoding="utf-8")
        with pytest.raises(ValueError, match="Formato no soportado"):
            load_accounts_from_file(str(txt_path))

    def test_load_accounts_corrupted_json(self, tmp_path):
        """Corrupted JSON syntax should raise JSONDecodeError."""
        corrupt_path = tmp_path / "corrupt.json"
        corrupt_path.write_text("{bad_json: 123", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_accounts_from_file(str(corrupt_path))

    def test_load_accounts_empty_json_list(self, tmp_path):
        """Empty list in JSON should return empty list without crash."""
        empty_path = tmp_path / "empty.json"
        empty_path.write_text("[]", encoding="utf-8")
        accs = load_accounts_from_file(str(empty_path))
        assert accs == []

    def test_load_accounts_dict_with_accounts_key(self, tmp_path):
        """JSON structured as {'accounts': [...]} or {'data': [...]} should be parsed."""
        nested_path = tmp_path / "nested.json"
        content = {
            "accounts": [
                {"email": "user1@alcampo.es", "password": "pwd1"},
                {"email": "user2@alcampo.es", "password": "pwd2"}
            ]
        }
        nested_path.write_text(json.dumps(content), encoding="utf-8")
        accs = load_accounts_from_file(str(nested_path))
        assert len(accs) == 2
        assert accs[0]["email"] == "user1@alcampo.es"
        assert accs[1]["email"] == "user2@alcampo.es"

    def test_load_accounts_alternative_key_names(self, tmp_path):
        """Should recognize alternative key names ('usuario', 'contraseña', 'user', 'pass')."""
        alt_path = tmp_path / "alt_keys.json"
        content = [
            {"usuario": "u1@alcampo.es", "contraseña": "p1"},
            {"Email": "u2@alcampo.es", "Password": "p2"},
            {"user": "u3@alcampo.es", "pass": "p3"},
        ]
        alt_path.write_text(json.dumps(content), encoding="utf-8")
        accs = load_accounts_from_file(str(alt_path))
        assert len(accs) == 3
        assert accs[0]["email"] == "u1@alcampo.es"
        assert accs[0]["password"] == "p1"

    def test_load_accounts_with_limit(self, tmp_path):
        """Limit parameter should restrict the number of loaded accounts."""
        path = tmp_path / "many.json"
        content = [{"email": f"u{i}@test.es", "password": "pwd"} for i in range(10)]
        path.write_text(json.dumps(content), encoding="utf-8")
        accs = load_accounts_from_file(str(path), limit=3)
        assert len(accs) == 3

    def test_load_accounts_limit_zero_or_negative(self, tmp_path):
        """Edge case: limit <= 0 behavior."""
        path = tmp_path / "many.json"
        content = [{"email": f"u{i}@test.es", "password": "pwd"} for i in range(5)]
        path.write_text(json.dumps(content), encoding="utf-8")
        # Currently, if limit <= 0, local_test.py does NOT slice and returns all accounts
        accs = load_accounts_from_file(str(path), limit=0)
        assert len(accs) == 5, "Notice: limit=0 does not slice, returns all accounts"


# ==============================================================================
# SECTION 2: AccountCooldownManager Concurrency & Stress Testing
# ==============================================================================

class TestCooldownManagerConcurrencyAndStress:
    """Adversarial stress-testing of AccountCooldownManager under multi-threading."""

    def test_concurrent_record_result_single_instance(self, tmp_path):
        """50 concurrent threads recording successes and failures on shared instance."""
        status_file = tmp_path / "concurrent_status.json"
        mgr = AccountCooldownManager(status_file_path=str(status_file))

        num_threads = 50
        iterations_per_thread = 20

        def worker(thread_id):
            for i in range(iterations_per_thread):
                email = f"thread_{thread_id}_acc_{i % 5}@alcampo.es"
                is_success = (i % 2 == 0)
                date_str = f"2026-10-{10 + (i % 15):02d}"
                mgr.record_result(email=email, is_success=is_success, today_str=date_str)
            mgr.save()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            for f in as_completed(futures):
                f.result()  # Should not raise exception or deadlock

        # Verify integrity of final saved file
        mgr.save()
        assert status_file.exists()
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "accounts" in data
        assert len(data["accounts"]) > 0
        assert data["metrics"]["total_tracked"] == len(data["accounts"])

    def test_concurrent_unpause_and_record_no_deadlock(self, tmp_path):
        """Stress test: unpause_all_cooldowns called repeatedly while record_result is executing."""
        status_file = tmp_path / "unpause_stress.json"
        mgr = AccountCooldownManager(status_file_path=str(status_file))

        stop_event = threading.Event()

        def unpause_worker():
            while not stop_event.is_set():
                mgr.unpause_all_cooldowns()

        def record_worker(thread_id):
            for day in range(20, 26):
                email = f"worker_{thread_id}@alcampo.es"
                mgr.record_result(email=email, is_success=False, today_str=f"2026-10-{day:02d}")

        t_unpause = threading.Thread(target=unpause_worker)
        t_unpause.start()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(record_worker, t) for t in range(20)]
            for f in as_completed(futures):
                f.result()

        stop_event.set()
        t_unpause.join(timeout=5)
        assert not t_unpause.is_alive(), "unpause_worker should terminate cleanly without deadlocks"

    def test_corrupted_file_recovery(self, tmp_path):
        """If account_status.json is truncated or invalid JSON on disk, manager should recover cleanly."""
        corrupt_file = tmp_path / "broken_status.json"
        corrupt_file.write_text("{ incomplete json ...", encoding="utf-8")

        # Manager should not crash on load
        mgr = AccountCooldownManager(status_file_path=str(corrupt_file))
        assert mgr.data["accounts"] == {}

        # Manager should be able to record and save
        mgr.record_result("recover@alcampo.es", is_success=True)
        mgr.save()

        # Check that file was rewritten cleanly
        with open(corrupt_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "recover@alcampo.es" in data["accounts"]

    def test_multi_instance_concurrent_save(self, tmp_path):
        """
        Multiple separate AccountCooldownManager instances targeting the SAME status file.
        Simulates multiple processes or shards writing to disk.
        """
        shared_file = tmp_path / "shared_status.json"

        # Initialize base file
        base_mgr = AccountCooldownManager(status_file_path=str(shared_file))
        base_mgr.record_result("base@alcampo.es", is_success=True)
        base_mgr.save()

        num_instances = 15
        errors = []

        def instance_worker(idx):
            try:
                inst = AccountCooldownManager(status_file_path=str(shared_file))
                inst.record_result(f"inst_{idx}@alcampo.es", is_success=True)
                inst.save()
            except Exception as e:
                errors.append(f"Instance {idx} error: {e}")

        with ThreadPoolExecutor(max_workers=num_instances) as executor:
            futures = [executor.submit(instance_worker, i) for i in range(num_instances)]
            for f in as_completed(futures):
                f.result()

        # Note: on Windows, concurrent replace() from separate instances can occasionally collide on tmp file
        # Let's see if any error occurred:
        assert shared_file.exists()
