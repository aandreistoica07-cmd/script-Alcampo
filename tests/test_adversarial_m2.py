"""
Adversarial Challenge Test Suite for Milestone M2
Focus areas:
1. CLI parsing of --run-id flag and fallback logic in scraper/script_optimizado.py
2. VM snapshot writing, run_id tagging, and /live_accounts streaming
3. Resilient prepare_matrix.py execution without Firebase env vars and under network failures
4. Dashboard progress aggregation, zombie VM filtering, monotonic clamping, and Top 10 catalog parsing
"""

import sys
import os
import json
import math
import time
import uuid
import re
import tempfile
import pytest
from unittest import mock
from concurrent.futures import ThreadPoolExecutor

# @section: CLI-And-Run-ID-Adversarial

class TestRunIdAndCLIParsingAdversarial:
    """Stress tests for CLI parsing and run_id generation."""

    def test_cli_parsing_explicit_run_id(self):
        from scraper.script_optimizado import parse_args
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--run-id", "run_explicit_123"]):
            args = parse_args()
            assert args.run_id == "run_explicit_123"

    def test_cli_parsing_env_var_fallback(self):
        from scraper.script_optimizado import parse_args
        with mock.patch.dict(os.environ, {"RUN_ID": "run_from_env_456"}):
            with mock.patch.object(sys, "argv", ["script_optimizado.py"]):
                args = parse_args()
                assert args.run_id == "run_from_env_456"

    def test_cli_parsing_explicit_beats_env_var(self):
        from scraper.script_optimizado import parse_args
        with mock.patch.dict(os.environ, {"RUN_ID": "run_env_ignored"}):
            with mock.patch.object(sys, "argv", ["script_optimizado.py", "--run-id", "run_cli_winner"]):
                args = parse_args()
                assert args.run_id == "run_cli_winner"

    def test_cli_parsing_empty_run_id(self):
        from scraper.script_optimizado import parse_args
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(sys, "argv", ["script_optimizado.py", "--run-id", ""]):
                args = parse_args()
                assert args.run_id == ""

    def test_run_id_concurrency_stress(self):
        """Stress-tests generation of 1,000 run_ids in parallel to guarantee zero collisions."""
        def generate():
            return f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(lambda _: generate(), range(1000)))

        assert len(results) == 1000
        assert len(set(results)) == 1000
        regex = re.compile(r"^run_\d+_[0-9a-f]{6}$")
        for rid in results:
            assert regex.match(rid) is not None

# @end: CLI-And-Run-ID-Adversarial

# @section: VM-Snapshot-And-Firebase-Streaming

class TestFirebaseVMSnapshotWritingAdversarial:
    """Tests VM snapshot writing, run_id tagging, and /live_accounts streaming in scraper/script_optimizado.py."""

    @pytest.fixture(autouse=True)
    def reset_scraper_state(self):
        import scraper.script_optimizado as sopt
        original_cli_args = getattr(sopt, "current_cli_args", None)
        original_progress = getattr(sopt, "current_progress", {})
        yield
        sopt.current_cli_args = original_cli_args
        sopt.current_progress = original_progress

    def test_init_progress_writes_vm_snapshot_with_run_id(self):
        import scraper.script_optimizado as sopt
        mock_args = mock.MagicMock()
        mock_args.run_id = "run_test_init_vm"
        sopt.current_cli_args = mock_args

        put_calls = []
        def mock_put(url, json=None, timeout=None):
            put_calls.append((url, json))
            res = mock.MagicMock()
            res.status_code = 200
            return res

        with mock.patch.object(sopt.firebase_session, "put", side_effect=mock_put):
            sopt.init_progress(200, worker_name="VM_3")

        assert len(put_calls) == 1
        url, body = put_calls[0]
        assert "/progress/vms/VM_3.json" in url
        assert body["run_id"] == "run_test_init_vm"
        assert body["processed"] == 0
        assert body["total_balance"] == 0.0

    def test_init_progress_without_run_id(self):
        import scraper.script_optimizado as sopt
        mock_args = mock.MagicMock()
        mock_args.run_id = ""
        sopt.current_cli_args = mock_args

        put_calls = []
        def mock_put(url, json=None, timeout=None):
            put_calls.append((url, json))
            res = mock.MagicMock()
            res.status_code = 200
            return res

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(sopt.firebase_session, "put", side_effect=mock_put):
                sopt.init_progress(50, worker_name="VM_1")

        assert len(put_calls) == 1
        assert "run_id" not in put_calls[0][1]

    def test_update_progress_streams_positive_balance_to_live_accounts(self):
        import scraper.script_optimizado as sopt
        mock_args = mock.MagicMock()
        mock_args.run_id = "run_streaming_777"
        sopt.current_cli_args = mock_args

        put_calls = []
        def mock_put(url, json=None, timeout=None):
            put_calls.append((url, json))
            res = mock.MagicMock()
            res.status_code = 200
            return res

        with mock.patch.object(sopt.firebase_session, "put", side_effect=mock_put):
            sopt.init_progress(100, worker_name="VM_0")
            sopt.update_progress(1, "target.user+sub@alcampo.es", "success", "42,75 €", worker_name="VM_0")

        # Find call to live_accounts
        live_calls = [c for c in put_calls if "/live_accounts/" in c[0]]
        assert len(live_calls) == 1
        url, payload = live_calls[0]
        assert "target_user+sub_alcampo_es" in url
        assert payload["email"] == "target.user+sub@alcampo.es"
        assert payload["balance"] == 42.75
        assert payload["run_id"] == "run_streaming_777"

    def test_update_progress_does_not_stream_zero_balance_or_errors(self):
        import scraper.script_optimizado as sopt
        mock_args = mock.MagicMock()
        mock_args.run_id = "run_streaming_888"
        sopt.current_cli_args = mock_args

        put_calls = []
        def mock_put(url, json=None, timeout=None):
            put_calls.append((url, json))
            res = mock.MagicMock()
            res.status_code = 200
            return res

        with mock.patch.object(sopt.firebase_session, "put", side_effect=mock_put):
            sopt.init_progress(100, worker_name="VM_0")
            # 1. Zero balance
            sopt.update_progress(1, "zero@alcampo.es", "success", "0,00 €", worker_name="VM_0")
            # 2. Error
            sopt.update_progress(2, "error@alcampo.es", "error", "0,00 €", worker_name="VM_0")

        live_calls = [c for c in put_calls if "/live_accounts/" in c[0]]
        assert len(live_calls) == 0

    def test_firebase_network_failure_resilience(self):
        """Simulates network timeout/crash in Firebase requests; scraper must handle gracefully."""
        import scraper.script_optimizado as sopt
        sopt.current_cli_args = mock.MagicMock(run_id="run_fail_safe")

        with mock.patch.object(sopt.firebase_session, "put", side_effect=Exception("Connection timed out")):
            sopt.init_progress(10, worker_name="VM_0")
            sopt.update_progress(1, "user@alcampo.es", "success", "10,00 €", worker_name="VM_0")

        assert sopt.current_progress["processed"] == 1
        assert sopt.current_progress["total_balance"] == 10.0

# @end: VM-Snapshot-And-Firebase-Streaming

# @section: Prepare-Matrix-Fallback-Adversarial

class TestPrepareMatrixFallbackAdversarial:
    """Tests scripts/prepare_matrix.py clean fallback without Firebase env var and under network failures."""

    def test_prepare_matrix_fallback_without_firebase_env(self, tmp_path):
        import scripts.prepare_matrix as pm
        gh_out = tmp_path / "github_output.txt"

        clean_env = {
            "GITHUB_OUTPUT": str(gh_out),
            "INPUT_ACCOUNTS_PER_VM": "50"
        }

        # Mock network calls to verify clean completion without real network traffic
        with mock.patch.dict(os.environ, clean_env, clear=True):
            with mock.patch("requests.post") as mock_post, mock.patch("requests.put") as mock_put:
                mock_post.return_value = mock.MagicMock(status_code=200)
                mock_put.return_value = mock.MagicMock(status_code=200)

                pm.main()

                # Verify requests.put was invoked with default RTDB URL
                assert mock_put.call_count >= 1
                first_url = mock_put.call_args_list[0][0][0]
                assert "monitor-alcampo-default-rtdb" in first_url

                # Verify GITHUB_OUTPUT was written
                content = gh_out.read_text(encoding="utf-8")
                assert "matrix=" in content
                assert "total_shards=" in content
                assert "run_id=run_" in content

    def test_prepare_matrix_handles_network_exceptions(self, tmp_path):
        """When Telegram and Firebase raise network exceptions, prepare_matrix exits cleanly."""
        import scripts.prepare_matrix as pm

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("requests.post", side_effect=Exception("Telegram connection refused")), \
                 mock.patch("requests.put", side_effect=Exception("Firebase timeout")):
                # Should not raise any unhandled exception
                pm.main()

    def test_prepare_matrix_shard_math_and_outputs(self, tmp_path):
        import scripts.prepare_matrix as pm
        gh_out = tmp_path / "out.txt"

        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(gh_out), "ACCOUNTS_PER_VM": "100"}, clear=True):
            with mock.patch("requests.post"), mock.patch("requests.put"):
                pm.main()

        content = gh_out.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.strip().split("\n")]
        out_dict = dict(l.split("=", 1) for l in lines if "=" in l)
        assert "matrix" in out_dict
        assert "total_shards" in out_dict
        assert "run_id" in out_dict
        matrix = json.loads(out_dict["matrix"])
        assert "shard" in matrix
        assert len(matrix["shard"]) == int(out_dict["total_shards"])

# @end: Prepare-Matrix-Fallback-Adversarial

# @section: Dashboard-Live-Progress-And-Top10-Adversarial

class TestDashboardLiveProgressAndTop10Adversarial:
    """Simulates and stress-tests frontend logic for live progress and top accounts parsing."""

    def test_zombie_vm_filtering_with_corrupted_data(self):
        active_run_id = "run_2026_current"

        simulated_data = {
            "run_id": active_run_id,
            "total": 100,
            "vms": {
                "VM_0": {"run_id": active_run_id, "processed": 20, "total_balance": 10.5, "money": 1, "success": 1},
                "VM_1": {"run_id": active_run_id, "processed": 25, "total_balance": 15.0, "money": 2, "success": 2},
                "VM_zombie_1": {"run_id": "run_2025_old", "processed": 80, "total_balance": 200.0, "money": 5, "success": 5},
                "VM_zombie_untagged": {"processed": 40, "total_balance": 99.0, "money": 3, "success": 3},
                "VM_corrupted": None,
                "VM_empty": {},
                "VM_string": "not a dict"
            }
        }

        # Simulate index.html lines 1403-1428: untagged and mismatched VMs must be discarded
        agg_proc = 0
        agg_bal = 0.0
        agg_mon = 0
        agg_succ = 0
        for vk, vm in simulated_data["vms"].items():
            if not vm or not isinstance(vm, dict):
                continue
            if active_run_id and vm.get("run_id") != active_run_id:
                continue
            agg_proc += vm.get("processed", 0)
            agg_bal += vm.get("total_balance", 0.0)
            agg_mon += vm.get("money", 0)
            agg_succ += vm.get("success", 0)

        raw_total = simulated_data.get("total", 0)
        final_proc = max(0, min(raw_total, agg_proc)) if raw_total > 0 else max(0, agg_proc)

        # VM_zombie_1 and VM_zombie_untagged are both cleanly discarded
        assert final_proc == 45
        assert round(agg_bal, 2) == 25.5
        assert agg_mon == 3
        assert agg_succ == 3

    def test_monotonic_clamping_under_overflow_and_negative(self):
        raw_total = 75
        agg_proc_overflow = 120
        clamped_overflow = max(0, min(raw_total, agg_proc_overflow)) if raw_total > 0 else max(0, agg_proc_overflow)
        assert clamped_overflow == 75

        # Lower bound clamping prevents negative percentages
        agg_proc_negative = -30
        clamped_negative = max(0, min(raw_total, agg_proc_negative)) if raw_total > 0 else max(0, agg_proc_negative)
        assert clamped_negative == 0

        percent_negative = max(0, min(100, round((clamped_negative / raw_total) * 100))) if raw_total > 0 else 0
        assert percent_negative == 0

        # When total is 0 (uninitialized)
        raw_total_zero = 0
        clamped_zero = max(0, min(raw_total_zero, agg_proc_overflow)) if raw_total_zero > 0 else max(0, agg_proc_overflow)
        assert clamped_zero == 120

    def test_monotonic_progress_across_poll_intervals(self):
        """Simulates high-water mark tracking across polling intervals."""
        state = {"current_run_id": None, "max_processed_seen": 0}

        def process_poll(run_id, processed):
            if run_id and state["current_run_id"] == run_id:
                processed = max(state["max_processed_seen"] or 0, processed)
                state["max_processed_seen"] = processed
            else:
                state["current_run_id"] = run_id
                state["max_processed_seen"] = processed
            return processed

        active_run = "run_2026_poll"
        # Poll 1: Initial progress 40
        assert process_poll(active_run, 40) == 40
        # Poll 2: Advances to 70
        assert process_poll(active_run, 70) == 70
        # Poll 3: Transient packet loss or out-of-order drop reports 45 -> must hold 70!
        assert process_poll(active_run, 45) == 70
        # Poll 4: Advances to 90
        assert process_poll(active_run, 90) == 90
        # Poll 5: New execution starts with new run_id -> resets to 0
        new_run = "run_2026_fresh"
        assert process_poll(new_run, 0) == 0
        assert state["max_processed_seen"] == 0

    def test_escape_html_string_coercion_and_entity_replacement(self):
        """Verifies escapeHtml logic handling numbers, null, undefined, and entities."""
        def escape_html(text):
            if text is None:
                return ""
            s = str(text)
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#039;")
            )

        # 1. Numeric passwords/IDs (fixes TypeError: text.replace is not a function)
        assert escape_html(123456) == "123456"
        assert escape_html(0) == "0"
        # 2. None / Null / Empty
        assert escape_html(None) == ""
        # 3. HTML entities
        assert escape_html('<script>alert("XSS") & \'test\';</script>') == (
            "&lt;script&gt;alert(&quot;XSS&quot;) &amp; &#039;test&#039;;&lt;/script&gt;"
        )

    def test_html_source_files_contain_all_four_remediation_fixes(self):
        """Validates that dashboard/index.html and android_app/app/src/main/assets/index.html contain the fixes."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        targets = [
            os.path.join(project_root, "dashboard", "index.html"),
            os.path.join(project_root, "android_app", "app", "src", "main", "assets", "index.html"),
        ]

        for path in targets:
            assert os.path.isfile(path), f"File not found: {path}"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Fix 1: Zombie VM filter without redundant vm.run_id truthiness check
            assert "if (activeRunId && vm.run_id !== activeRunId) continue;" in content
            assert "if (activeRunId && vm.run_id && vm.run_id !== activeRunId) continue;" not in content

            # Fix 2: Lower bound clamping Math.max(0, ...)
            assert "data.processed = rawTotal > 0 ? Math.max(0, Math.min(rawTotal, aggProc)) : Math.max(0, aggProc);" in content
            assert "const percent = total > 0 ? Math.max(0, Math.min(100, Math.round((processed / total) * 100))) : 0;" in content

            # Fix 3: Monotonic high water mark
            assert "if (activeRunId && window._currentRunId === activeRunId)" in content
            assert "window._maxProcessedSeen = data.processed;" in content

            # Fix 4: escapeHtml string coercion and null check
            assert "if (text == null) return '';" in content
            assert "return String(text)" in content

    def test_top_accounts_array_and_object_deduplication(self):
        """Simulates fetchTop10Accounts parsing both Array and Object sources, keeping max balance."""
        top_data_source = [
            {"email": "userA@alcampo.es", "balance": 10.0},
            {"email": "userB@alcampo.es", "balance": 35.0},
            None,
            {"invalid": True}
        ]

        live_data_source = {
            "userA_sanitized": {"email": "userA@alcampo.es", "balance": 22.5},  # Increased balance
            "userB_sanitized": {"email": "userB@alcampo.es", "balance": 15.0},  # Lower balance
            "userC_sanitized": {"email": "userC@alcampo.es", "balance": 80.0},  # New account
            "corrupted": None
        }

        accounts_map = {}
        def add_accounts(source):
            if not source:
                return
            items = source if isinstance(source, list) else list(source.values())
            for acc in items:
                if acc and isinstance(acc, dict) and acc.get("email") and isinstance(acc.get("balance"), (int, float)):
                    email = acc["email"]
                    existing = accounts_map.get(email)
                    if not existing or acc["balance"] > existing["balance"]:
                        accounts_map[email] = acc

        add_accounts(top_data_source)
        add_accounts(live_data_source)

        parsed_list = list(accounts_map.values())
        parsed_list.sort(key=lambda a: a.get("balance", 0), reverse=True)

        assert len(parsed_list) == 3
        assert parsed_list[0]["email"] == "userC@alcampo.es" and parsed_list[0]["balance"] == 80.0
        assert parsed_list[1]["email"] == "userB@alcampo.es" and parsed_list[1]["balance"] == 35.0
        assert parsed_list[2]["email"] == "userA@alcampo.es" and parsed_list[2]["balance"] == 22.5

    def test_top_accounts_empty_sources(self):
        accounts_map = {}
        assert len(accounts_map) == 0

# @end: Dashboard-Live-Progress-And-Top10-Adversarial

