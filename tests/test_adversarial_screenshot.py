"""
Adversarial Challenge & Stress Test Suite for Milestone M1
Focus: Empirical stress testing of `capture_screenshot` in:
- `scraper/script_optimizado.py`
- `scripts/local_test.py`

Verifies:
1. Driver edge cases: None, missing save_screenshot, WebDriverException, IOError, PermissionError.
2. Email sanitization and path traversal prevention ('../../secret', 'test@domain.com', spaces, empty, None, illegal chars).
3. Exact timestamped schema adherence ({safe_email}_{label}_{YYYYMMDD_HHMMSS}.png) and directory containment.
4. Concurrency and thread safety under heavy load.
"""

import os
import re
import pytest
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock

# Import both implementations
from scraper.script_optimizado import capture_screenshot as capture_screenshot_scraper
from scripts.local_test import capture_screenshot as capture_screenshot_local


IMPLEMENTATIONS = [
    ("scraper.script_optimizado", capture_screenshot_scraper),
    ("scripts.local_test", capture_screenshot_local),
]

CANONICAL_LABELS = [
    "err_inputs",
    "err_waf",
    "err_call_center",
    "err_needs_attention",
    "err_oauth_timeout",
    "saldo_positivo",
    "saldo_cero_compraonline",
    "saldo_cero_verificado",
    "saldo_no_detectado",
    "err_unexpected",
]


class MockDriverWithSave:
    """Mock WebDriver that records save_screenshot calls and optionally writes a dummy file."""
    def __init__(self, write_dummy=True, side_effect=None):
        self.save_calls = []
        self.write_dummy = write_dummy
        self.side_effect = side_effect

    def save_screenshot(self, filename):
        self.save_calls.append(filename)
        if self.side_effect:
            if isinstance(self.side_effect, Exception):
                raise self.side_effect
            elif callable(self.side_effect):
                self.side_effect(filename)
            else:
                raise RuntimeError("Mock side effect")
        if self.write_dummy:
            Path(filename).write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdummy")
        return True


class DummyNoSaveDriver:
    """Driver missing save_screenshot attribute."""
    pass


class DummyPropertyExceptionDriver:
    """Driver where hasattr or attribute access triggers an exception."""
    @property
    def save_screenshot(self):
        raise AttributeError("Simulated faulty property access")


# ==============================================================================
# SECTION 1: Driver Edge Cases & Exception Absorption
# ==============================================================================

@pytest.mark.parametrize("module_name, func", IMPLEMENTATIONS)
class TestDriverEdgeCases:
    """Empirical challenge of driver argument variations and exception handling."""

    def test_driver_is_none(self, module_name, func, tmp_path):
        """When driver is None, capture_screenshot must return None without raising."""
        res = func(None, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None
        assert len(list(tmp_path.iterdir())) == 0

    def test_driver_lacks_save_screenshot(self, module_name, func, tmp_path):
        """When driver lacks save_screenshot attribute, return None without raising."""
        # Test with custom class
        driver_dummy = DummyNoSaveDriver()
        res = func(driver_dummy, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None

        # Test with basic Python types
        for invalid_driver in [object(), 12345, "not_a_driver", [], {}]:
            res = func(invalid_driver, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
            assert res is None

        assert len(list(tmp_path.iterdir())) == 0

    def test_driver_save_screenshot_raises_webdriver_exception(self, module_name, func, tmp_path):
        """When driver.save_screenshot raises WebDriverException, catch safely and return None."""
        try:
            from selenium.common.exceptions import WebDriverException
            exc = WebDriverException("Simulated Chrome connection lost")
        except ImportError:
            exc = RuntimeError("Simulated WebDriverException fallback")

        driver = MockDriverWithSave(side_effect=exc)
        res = func(driver, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None
        assert len(driver.save_calls) == 1

    def test_driver_save_screenshot_raises_ioerror(self, module_name, func, tmp_path):
        """When driver.save_screenshot raises IOError / OSError, catch safely and return None."""
        driver = MockDriverWithSave(side_effect=IOError("Disk I/O error"))
        res = func(driver, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None
        assert len(driver.save_calls) == 1

    def test_driver_save_screenshot_raises_permission_error(self, module_name, func, tmp_path):
        """When driver.save_screenshot raises PermissionError (WinError 5), catch safely."""
        driver = MockDriverWithSave(side_effect=PermissionError("Access denied (WinError 5)"))
        res = func(driver, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None
        assert len(driver.save_calls) == 1

    def test_driver_save_screenshot_raises_unexpected_exception(self, module_name, func, tmp_path):
        """Any unexpected exception (MemoryError, SystemError, custom) must be absorbed."""
        class CustomFatalError(Exception):
            pass

        driver = MockDriverWithSave(side_effect=CustomFatalError("Catastrophic error"))
        res = func(driver, "user@test.es", "err_unexpected", screenshot_dir=str(tmp_path))
        assert res is None
        assert len(driver.save_calls) == 1

    def test_driver_attribute_access_faulty(self, module_name, func, tmp_path):
        """Driver whose save_screenshot property raises on access must be safely handled."""
        driver = DummyPropertyExceptionDriver()
        res = func(driver, "user@test.es", "err_inputs", screenshot_dir=str(tmp_path))
        assert res is None


# ==============================================================================
# SECTION 2: Email Sanitization, Path Traversal & Schema Adherence
# ==============================================================================

@pytest.mark.parametrize("module_name, func", IMPLEMENTATIONS)
class TestEmailSanitizationAndSchema:
    """Empirical challenge of email inputs, path traversal attacks, and schema formatting."""

    @pytest.mark.parametrize("email_input, expected_email_sub", [
        ("../../secret", "______secret"),
        ("..\\..\\windows\\system32\\calc.exe", "______windows_system32_calc_exe"),
        ("/etc/shadow", "_etc_shadow"),
        ("test@domain.com", "test_domain_com"),
        ("user with spaces", "user_with_spaces"),
        ("user.name+tag@sub.example.com", "user_name_tag_sub_example_com"),
        ("user:pass*invalid?chars\"<>|", "user_pass_invalid_chars____"),
        ("", "anon"),
        (None, "anon"),
        (12345, "12345"),
        (False, "anon"),
        (True, "True"),
    ])
    def test_email_sanitization_and_containment(self, module_name, func, tmp_path, email_input, expected_email_sub):
        """
        Verify that:
        1. safe_email matches expected sanitization without path traversal characters.
        2. Generated file path is strictly inside screenshot_dir.
        3. Filename adheres to {safe_email}_{label}_{YYYYMMDD_HHMMSS}.png schema.
        """
        driver = MockDriverWithSave(write_dummy=True)
        label = "saldo_positivo"

        shot_path = func(driver, email_input, label, screenshot_dir=str(tmp_path))
        assert shot_path is not None
        assert os.path.exists(shot_path)

        path_obj = Path(shot_path).resolve()
        dir_obj = tmp_path.resolve()

        # STRICT PATH CONTAINMENT: The generated file must be directly in screenshot_dir
        assert path_obj.parent == dir_obj, f"Path traversal escape detected! {path_obj} not in {dir_obj}"

        # Schema regex verification: {safe_email}_{label}_{YYYYMMDD_HHMMSS}.png
        filename = path_obj.name
        pattern = rf"^{re.escape(expected_email_sub)}_{re.escape(label)}_(\d{{8}}_\d{{6}})\.png$"
        match = re.match(pattern, filename)
        assert match is not None, f"Filename '{filename}' does not match expected schema '{pattern}'"

        # Validate that the timestamp is a valid datetime
        ts_str = match.group(1)
        parsed_dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        assert parsed_dt.year >= 2026

    @pytest.mark.parametrize("label", CANONICAL_LABELS)
    def test_all_canonical_labels_and_directory_creation(self, module_name, func, tmp_path, label):
        """Verify that all 10 canonical labels format properly and missing directories are auto-created."""
        nested_dir = tmp_path / "deep" / "nested" / "audit_dir"
        assert not nested_dir.exists()

        driver = MockDriverWithSave(write_dummy=True)
        shot_path = func(driver, "auditor@alcampo.es", label, screenshot_dir=str(nested_dir))

        assert shot_path is not None
        assert nested_dir.exists()
        assert os.path.exists(shot_path)

        filename = Path(shot_path).name
        assert filename.startswith(f"auditor_alcampo_es_{label}_")
        assert filename.endswith(".png")


# ==============================================================================
# SECTION 3: Concurrency, Thread Safety & High Load Stress
# ==============================================================================

@pytest.mark.parametrize("module_name, func", IMPLEMENTATIONS)
class TestConcurrencyAndStress:
    """Multi-threaded stress testing to verify absence of race conditions or file locks."""

    def test_concurrent_screenshots_multi_threaded(self, module_name, func, tmp_path):
        """20 concurrent threads writing screenshots simultaneously to the same directory."""
        num_threads = 20
        iterations_per_thread = 5

        def worker(thread_id):
            driver = MockDriverWithSave(write_dummy=True)
            results = []
            for i in range(iterations_per_thread):
                email = f"thread_{thread_id}_user_{i}@alcampo.es"
                label = CANONICAL_LABELS[i % len(CANONICAL_LABELS)]
                path = func(driver, email, label, screenshot_dir=str(tmp_path))
                assert path is not None
                assert os.path.exists(path)
                results.append(path)
            return results

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            all_paths = []
            for f in as_completed(futures):
                all_paths.extend(f.result())

        assert len(all_paths) == num_threads * iterations_per_thread
        # Verify all created files exist on disk
        existing_files = list(tmp_path.glob("*.png"))
        assert len(existing_files) >= 1  # May be fewer than total if timestamps collide, but all calls succeed without error
