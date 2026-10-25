"""
Forensic Integrity Audit Suite for Milestone M1
Empirical runtime tracing, static AST inspection, and adversarial stress-testing.
"""

import ast
import os
import re
import sys
import tempfile
import inspect
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scraper"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scraper.script_optimizado import capture_screenshot as capture_scraper
from scripts.local_test import capture_screenshot as capture_local
from scripts.local_test import test_single_account as run_local_test_account


class MockTraceWebDriver:
    """Mock WebDriver with call recording and file generation."""
    def __init__(self, page_source=""):
        self.page_source = page_source
        self.current_url = "https://www.compraonline.alcampo.es"
        self.screenshot_calls = []
        self.fail_screenshot = False
        self.raise_on_screenshot = None

    def save_screenshot(self, filepath):
        self.screenshot_calls.append(filepath)
        if self.raise_on_screenshot:
            raise self.raise_on_screenshot
        if self.fail_screenshot:
            return False
        # Create an actual 1x1 PNG stub on disk
        with open(filepath, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
        return True


# ==============================================================================
# SECTION 1: Static AST & Code Forensics
# ==============================================================================

class TestStaticASTForensics:
    """Verifies that the implementation is genuine and free of hardcoding or facades."""

    def test_scraper_capture_screenshot_ast_genuine(self):
        scraper_path = PROJECT_ROOT / "scraper" / "script_optimizado.py"
        with open(scraper_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)
        func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "capture_screenshot"]
        assert len(func_defs) == 1, "capture_screenshot must be defined in scraper/script_optimizado.py"
        fn = func_defs[0]

        # Verify arguments
        arg_names = [a.arg for a in fn.args.args]
        assert arg_names == ["driver", "email", "label", "screenshot_dir"]

        # Verify driver.save_screenshot call in AST
        calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "save_screenshot"
        ]
        assert len(calls) >= 1, "capture_screenshot MUST invoke driver.save_screenshot"

        # Verify no hardcoded email or fixed return string
        string_constants = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        for s in string_constants:
            assert "@" not in s, f"Hardcoded email detected in capture_screenshot AST: {s}"
            assert not (s.endswith(".png") and len(s) > 5), f"Hardcoded PNG filename detected in capture_screenshot AST: {s}"

    def test_local_test_capture_screenshot_ast_genuine(self):
        local_path = PROJECT_ROOT / "scripts" / "local_test.py"
        with open(local_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)
        func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "capture_screenshot"]
        assert len(func_defs) == 1, "capture_screenshot must be defined in scripts/local_test.py"
        fn = func_defs[0]

        calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "save_screenshot"
        ]
        assert len(calls) >= 1, "capture_screenshot in local_test.py MUST invoke driver.save_screenshot"

        # Verify no hardcoded email or fixed return string
        string_constants = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        for s in string_constants:
            assert "@" not in s, f"Hardcoded email detected in capture_screenshot AST: {s}"
            assert not (s.endswith(".png") and len(s) > 5), f"Hardcoded PNG filename detected in capture_screenshot AST: {s}"

    def test_instrumentation_call_sites_count(self):
        """Verify multiple call sites exist for all required error/anomaly conditions."""
        scraper_path = PROJECT_ROOT / "scraper" / "script_optimizado.py"
        with open(scraper_path, "r", encoding="utf-8") as f:
            code = f.read()

        matches = re.findall(r'capture_screenshot\s*\(', code)
        assert len(matches) >= 15, f"Expected at least 15 capture_screenshot calls in script_optimizado, found {len(matches)}"

        local_path = PROJECT_ROOT / "scripts" / "local_test.py"
        with open(local_path, "r", encoding="utf-8") as f:
            code_local = f.read()

        matches_local = re.findall(r'capture_screenshot\s*\(', code_local)
        assert len(matches_local) >= 7, f"Expected at least 7 capture_screenshot calls in local_test, found {len(matches_local)}"


# ==============================================================================
# SECTION 2: Empirical Runtime Tracing & Behavioral Verification
# ==============================================================================

class TestEmpiricalRuntimeTracing:
    """Executes capture_screenshot with real filesystem I/O and verifies file creation."""

    @pytest.mark.parametrize("fn", [capture_scraper, capture_local])
    def test_genuine_screenshot_creation_and_file_existence(self, fn, tmp_path):
        driver = MockTraceWebDriver()
        email = "test.auditor_99@alcampo.es"
        label = "err_waf"

        out_path = fn(driver, email, label, screenshot_dir=str(tmp_path))
        assert out_path is not None
        assert os.path.exists(out_path), f"Screenshot file must actually exist on disk: {out_path}"
        assert os.path.getsize(out_path) > 0, "Screenshot file must not be 0 bytes"
        assert len(driver.screenshot_calls) == 1
        assert driver.screenshot_calls[0] == out_path

        # Validate filename regex format: {safe_email}_{label}_{YYYYMMDD_HHMMSS}.png
        filename = os.path.basename(out_path)
        pattern = r"^test_auditor_99_alcampo_es_err_waf_\d{8}_\d{6}\.png$"
        assert re.match(pattern, filename), f"Filename does not match expected format: {filename}"

    @pytest.mark.parametrize("fn", [capture_scraper, capture_local])
    def test_all_ten_standard_labels(self, fn, tmp_path):
        labels = [
            "err_inputs",
            "err_waf",
            "err_call_center",
            "err_needs_attention",
            "err_oauth_timeout",
            "saldo_no_detectado",
            "saldo_positivo",
            "saldo_cero_verificado",
            "saldo_cero_compraonline",
            "err_unexpected",
        ]
        driver = MockTraceWebDriver()
        for lbl in labels:
            path = fn(driver, "user@test.org", lbl, screenshot_dir=str(tmp_path))
            assert path is not None
            assert f"_{lbl}_" in os.path.basename(path)
            assert os.path.exists(path)

    @pytest.mark.parametrize("fn", [capture_scraper, capture_local])
    def test_email_sanitization_pii_and_special_chars(self, fn, tmp_path):
        driver = MockTraceWebDriver()
        dirty_email = "User+Test!Name#123@Sub.Alcampo-Online.com"
        path = fn(driver, dirty_email, "err_inputs", screenshot_dir=str(tmp_path))
        assert path is not None
        filename = os.path.basename(path)
        # Should not contain +, !, #, @, or -
        assert not any(c in filename for c in ["+", "!", "#", "@", "-"]), f"Unsanitized characters in {filename}"
        assert filename.startswith("User_Test_Name_123_Sub_Alcampo_Online_com_err_inputs_")

    @pytest.mark.parametrize("fn", [capture_scraper, capture_local])
    def test_null_and_empty_email_fallback_to_anon(self, fn, tmp_path):
        driver = MockTraceWebDriver()
        path1 = fn(driver, None, "err_inputs", screenshot_dir=str(tmp_path))
        path2 = fn(driver, "", "err_inputs", screenshot_dir=str(tmp_path))
        assert os.path.basename(path1).startswith("anon_err_inputs_")
        assert os.path.basename(path2).startswith("anon_err_inputs_")

    @pytest.mark.parametrize("fn", [capture_scraper, capture_local])
    def test_driver_none_or_missing_method_fails_gracefully(self, fn, tmp_path):
        assert fn(None, "u@test.com", "label", screenshot_dir=str(tmp_path)) is None
        assert fn(object(), "u@test.com", "label", screenshot_dir=str(tmp_path)) is None

    @pytest.mark.parametrize("fn", [capture_scraper, capture_local])
    def test_exception_absorption_guarantees_zero_crash(self, fn, tmp_path):
        driver = MockTraceWebDriver()
        driver.raise_on_screenshot = PermissionError("Simulated WinError 5 Access Denied")
        # Must return None without propagating PermissionError
        result = fn(driver, "u@test.com", "label", screenshot_dir=str(tmp_path))
        assert result is None


# ==============================================================================
# SECTION 3: End-to-End Tracing via local_test runner
# ==============================================================================

class TestLocalTestRunnerTracing:
    """Tests runtime integration in local_test runner."""

    def test_login_timeout_captures_err_inputs(self, tmp_path):
        driver = MagicMock()
        driver.page_source = "<html><body>Generic login page</body></html>"
        driver.find_element.side_effect = Exception("Timeout waiting for inputs")

        saved_shots = []
        def fake_shot(path):
            saved_shots.append(path)
            with open(path, "w") as f:
                f.write("mock png")
            return True
        driver.save_screenshot.side_effect = fake_shot

        res = run_local_test_account(
            driver,
            "test_user@alcampo.es",
            "password123",
            timeout=1,
            screenshot_dir=str(tmp_path)
        )
        assert res["status"] == "failed"
        assert len(saved_shots) >= 1
        assert "err_inputs" in saved_shots[0]
        assert os.path.exists(saved_shots[0])

    def test_waf_challenge_captures_err_waf(self, tmp_path):
        driver = MagicMock()
        driver.page_source = "<html><body>Attention Required! Cloudflare Ray ID: 12345</body></html>"
        driver.find_element.side_effect = Exception("Timeout waiting for inputs")

        saved_shots = []
        def fake_shot(path):
            saved_shots.append(path)
            with open(path, "w") as f:
                f.write("mock png")
            return True
        driver.save_screenshot.side_effect = fake_shot

        res = run_local_test_account(
            driver,
            "waf_user@alcampo.es",
            "password123",
            timeout=1,
            screenshot_dir=str(tmp_path)
        )
        assert res["status"] == "failed"
        assert len(saved_shots) >= 1
        assert "err_waf" in saved_shots[0]
        assert os.path.exists(saved_shots[0])

    def test_call_center_lock_captures_err_call_center(self, tmp_path):
        driver = MagicMock()
        # Step 2 succeeds
        uname = MagicMock()
        pwd = MagicMock()
        driver.find_element.side_effect = lambda by, val: uname if val == "uname1" else pwd
        # Step 5 has call center text
        driver.page_source = "<html><body>Tu cuenta ha sido bloqueada. Contacte con Call Center.</body></html>"
        driver.current_url = "https://ar-customerdiamond-es.my.site.com/login"

        saved_shots = []
        def fake_shot(path):
            saved_shots.append(path)
            with open(path, "w") as f:
                f.write("mock png")
            return True
        driver.save_screenshot.side_effect = fake_shot

        res = run_local_test_account(
            driver,
            "locked_user@alcampo.es",
            "password123",
            timeout=1,
            screenshot_dir=str(tmp_path)
        )
        assert res["status"] == "failed"
        assert any("err_call_center" in s for s in saved_shots)
        assert all(os.path.exists(s) for s in saved_shots)
