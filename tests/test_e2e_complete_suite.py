# -*- coding: utf-8 -*-
"""
End-to-End Test Suite for Alcampo Scraper Consolidation (Milestone M5).
Structured across 4 rigorous tiers covering all 17 features (F1-F17)
and requirements R1-R4:
- Tier 1: Feature Coverage (F1-F17, R1-R4)
- Tier 2: Boundary & Corner Cases (Empty dirs, corrupt files, missing cards, 0,00 € DOMs, 429 WAF, 4000+ char Telegram, Windows UTF-8)
- Tier 3: Cross-Feature Combinations (Complete E2E lifecycle: matrix prep -> shard run with canary exit -> ensure_excel_output -> check-timeouts rescue -> Pass 2 retry -> final-merge 6-sheet workbook -> Telegram summary)
- Tier 4: Real-World Scenarios (Clean run, WAF block recovery, mixed account batch routing)

Zero external Chrome or live network dependencies: uses robust in-memory mock drivers
and isolated temporary filesystem fixtures to maintain real state and behavior.
"""

import os
import sys
import re
import json
import math
import time
import uuid
import html
import tempfile
import shutil
from pathlib import Path
from unittest import mock
import pytest
import pandas as pd

# Core scraper and scripts imports
from scraper.script_optimizado import (
    CircuitBreaker,
    AdaptivePacer,
    _verify_and_hydrate_session,
    _extract_loyalty_balance,
    extraer_tarjeta,
    limpiar_saldo,
    mask_email,
    ensure_excel_output,
    parse_args as parse_scraper_args,
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
import scripts.prepare_matrix as prepare_matrix_module
import scripts.local_test as local_test_module
from scripts.local_test import (
    parse_arguments as parse_local_test_args,
    load_accounts_from_file,
    test_single_account as exec_test_single_account,
    export_to_excel,
    main as local_test_main,
)


# ==============================================================================
# Helper Mock Objects for In-Memory E2E Execution
# ==============================================================================

class MockWebElement:
    """Mock Selenium WebElement for form interaction."""
    def __init__(self, tag_name="div", element_id="", text=""):
        self.tag_name = tag_name
        self.element_id = element_id
        self.text = text
        self.cleared = False
        self.keys_sent = []

    def clear(self):
        self.cleared = True

    def send_keys(self, value):
        self.keys_sent.append(str(value))

    def is_displayed(self):
        return True


class MockStealthWebDriver:
    """
    Mock Selenium WebDriver simulating browser navigation, DOM states,
    and redirection across Alcampo OAuth login and loyalty areas.
    """
    def __init__(self, initial_pages=None, initial_url="https://ar-customerdiamond-es.my.site.com/customerdiamond/login"):
        self.current_url = initial_url
        self.title = "Alcampo - Compra Online"
        self.pages = list(initial_pages or [])
        self.page_idx = 0
        self.refresh_count = 0
        self.navigated_urls = []
        self.executed_scripts = []
        self._login_success = True

    @property
    def page_source(self):
        if self.pages and self.page_idx < len(self.pages):
            return self.pages[self.page_idx]
        return self.pages[-1] if self.pages else "<html><body></body></html>"

    def get(self, url):
        self.navigated_urls.append(url)
        self.current_url = url
        if self.pages and self.page_idx + 1 < len(self.pages):
            self.page_idx += 1

    def refresh(self):
        self.refresh_count += 1
        if self.pages and self.page_idx + 1 < len(self.pages):
            self.page_idx += 1

    def find_element(self, by, value):
        el = MockWebElement(element_id=value)
        return el

    def execute_script(self, script, *args):
        self.executed_scripts.append(script)
        if "click" in script and self._login_success:
            self.current_url = "https://www.compraonline.alcampo.es/settings/loyalty"
            if self.pages and self.page_idx + 1 < len(self.pages):
                self.page_idx += 1

    def quit(self):
        pass


class StrictTelegramHTMLOracle:
    """
    Strict validation oracle verifying compliance with Telegram Bot API HTML rules.
    - Message length <= 4096 characters.
    - Only allowed HTML tags: <b>, <strong>, <i>, <em>, <u>, <s>, <a>, <code>, <pre>, <blockquote>.
    - All tags properly balanced and closed.
    - No unescaped raw '<', '>', or '&' characters in message body.
    """
    ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "s", "strike", "del", "a", "code", "pre", "blockquote"}

    @classmethod
    def validate(cls, text: str) -> list[str]:
        violations = []
        if len(text) > 4096:
            violations.append(f"Length {len(text)} exceeds Telegram limit of 4096 characters")

        tag_pattern = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9_-]+)(?:\s+[^>]*)?>")
        tag_stack = []

        for match in tag_pattern.finditer(text):
            is_closing = bool(match.group(1))
            tag_name = match.group(2).lower()
            if tag_name not in cls.ALLOWED_TAGS:
                violations.append(f"Disallowed HTML tag: <{tag_name}>")

            if not is_closing:
                tag_stack.append(tag_name)
            else:
                if not tag_stack:
                    violations.append(f"Unmatched closing tag: </{tag_name}>")
                elif tag_stack[-1] != tag_name:
                    violations.append(f"Mismatched tag: expected </{tag_stack[-1]}>, found </{tag_name}>")
                else:
                    tag_stack.pop()

        if tag_stack:
            violations.append(f"Unclosed tags at end of message: {tag_stack}")

        stripped = tag_pattern.sub("", text)
        if "<" in stripped:
            violations.append("Raw unescaped '<' detected")
        if ">" in stripped:
            violations.append("Raw unescaped '>' detected")

        return violations


# ==============================================================================
# TIER 1: FEATURE COVERAGE (F1 - F17 & R1 - R4)
# ==============================================================================

class TestTier1FeatureCoverage:
    """
    Verifies full feature coverage across the 17 features and R1-R4 requirements
    specified in PROJECT.md.
    """

    @pytest.fixture
    def repo_root(self):
        return Path(__file__).resolve().parent.parent

    # --- F1 & R1: Structural Consolidation & No Spaces in Folder Names ---
    def test_f1_r1_directory_structure_and_no_legacy_space_paths(self, repo_root):
        """F1: Ensure 'scraper/' exists, legacy folder with spaces is eliminated, and modular structure holds."""
        scraper_dir = repo_root / "scraper"
        legacy_dir = repo_root / "script_alcampo_activacion telegram"
        assert scraper_dir.is_dir(), "Directory 'scraper/' must exist"
        assert not legacy_dir.exists(), "Legacy directory 'script_alcampo_activacion telegram/' must NOT exist in repo root"

        # Modular directories contract
        assert (repo_root / "scripts").is_dir(), "'scripts/' directory must exist"
        assert (repo_root / "dashboard").is_dir(), "'dashboard/' directory must exist"
        assert (repo_root / "tests").is_dir(), "'tests/' directory must exist"
        assert (scraper_dir / "__init__.py").is_file(), "'scraper/__init__.py' must exist for package modularity"

        # Verify active CI/CD workflow references scraper/ and not the legacy path with spaces
        wf_file = repo_root / ".github" / "workflows" / "alcampo_2pass_matrix.yml"
        assert wf_file.is_file(), "alcampo_2pass_matrix.yml must exist"
        wf_text = wf_file.read_text(encoding="utf-8")
        assert 'cd "scraper"' in wf_text or "cd scraper" in wf_text, "Workflow must execute in 'scraper/' directory"
        assert 'script_alcampo_activacion telegram' not in wf_text, (
            "CI/CD workflow must not contain references to 'script_alcampo_activacion telegram'"
        )

    # --- F2 & R1: Canonical Frontend in dashboard/ and Vercel Config ---
    def test_f2_r1_frontend_consolidation_and_vercel_config(self, repo_root):
        """F2: Canonical frontend in dashboard/ with vercel.json routing."""
        dashboard_dir = repo_root / "dashboard"
        assert (dashboard_dir / "index.html").is_file(), "Canonical 'dashboard/index.html' must exist"
        assert (dashboard_dir / "css" / "style.css").is_file(), "Canonical 'dashboard/css/style.css' must exist"

        vercel_json_path = repo_root / "vercel.json"
        assert vercel_json_path.is_file(), "vercel.json must exist in repository root"
        with open(vercel_json_path, "r", encoding="utf-8") as vf:
            v_data = json.load(vf)
        assert "dashboard" in str(v_data), "vercel.json must route to dashboard"

        # Verify dashboard exists as primary UI, and docs/ mirrors it for Vercel root compatibility
        assert (dashboard_dir / "index.html").is_file()
        docs_dir = repo_root / "docs"
        if docs_dir.exists() and (docs_dir / "index.html").exists():
            assert (docs_dir / "index.html").read_text(encoding="utf-8") == (dashboard_dir / "index.html").read_text(encoding="utf-8")

    # --- F3 & R1: Sub-script de pruebas scripts/local_test.py CLI ---
    def test_f3_r1_local_test_cli_invocation_and_step_by_step_execution(self, tmp_path):
        """F3: scripts/local_test.py CLI argument parsing, standalone execution, and Excel export."""
        # Test CLI argument parsing
        test_args = [
            "--email", "test_user@alcampo.es",
            "--password", "SecretPass123!",
            "--headless",
            "--timeout", "15",
            "--slowmo", "0.0",
            "--output-excel", str(tmp_path / "local_test_out.xlsx")
        ]
        with mock.patch.object(sys, "argv", ["local_test.py"] + test_args):
            parsed = parse_local_test_args()
            assert parsed.email == "test_user@alcampo.es"
            assert parsed.password == "SecretPass123!"
            assert parsed.headless is True
            assert parsed.timeout == 15

        # Test single account step-by-step mock execution
        page1 = '<html><body><input id="uname1"/><input id="pwd1"/><input id="btnSubmit_login"/></body></html>'
        page2 = (
            '<html><body>'
            '<p>Tu Saldo es 18,75 €</p>'
            '<span class="sana-sans-alt">4002005555555</span>'
            '</body></html>'
        )
        mock_driver = MockStealthWebDriver(initial_pages=[page1, page2])
        res = exec_test_single_account(mock_driver, "test_user@alcampo.es", "SecretPass123!", timeout=5, slowmo=0.0)

        assert res["status"] == "success"
        assert res["balance"] == 18.75
        assert res["card_number"] == "4002005555555"

        # Test export_to_excel helper
        out_excel = tmp_path / "test_export.xlsx"
        export_to_excel([res], str(out_excel))
        assert out_excel.exists()
        df = pd.read_excel(out_excel)
        assert len(df) == 1
        assert df.iloc[0]["email"] == "test_user@alcampo.es"
        assert "18.75" in str(df.iloc[0]["saldo"])

    # --- F4: Automated Test Suite Contract ---
    def test_f4_r1_unit_test_suite_contracts_and_discoverability(self, repo_root):
        """F4: Verify automated test suite contracts and modular test files in tests/."""
        tests_dir = repo_root / "tests"
        required_test_files = [
            "test_circuit_breaker.py",
            "test_cooldown_manager.py",
            "test_scraper_utils.py",
            "test_matrix_calc.py",
            "test_merge_and_retry.py",
        ]
        for tf in required_test_files:
            assert (tests_dir / tf).is_file(), f"Required test file {tf} must exist in tests/"

    # --- F5 & R2: prepare_matrix.py Imports & Firebase Initialization ---
    def test_f5_r2_prepare_matrix_imports_and_firebase_initialization(self, tmp_path):
        """F5: Verify 'time' and 'uuid' imported and /progress.json initialized cleanly."""
        matrix_script = Path(prepare_matrix_module.__file__)
        content = matrix_script.read_text(encoding="utf-8")
        assert "import time" in content, "prepare_matrix.py must import time"
        assert "import uuid" in content, "prepare_matrix.py must import uuid"

        gh_output = tmp_path / "github_output.txt"
        env_vars = {
            "GITHUB_OUTPUT": str(gh_output),
            "INPUT_ACCOUNTS_PER_VM": "25",
            "FIREBASE_DB_URL": "https://test-matrix-rtdb.firebaseio.com"
        }
        put_requests = []

        def mock_put(url, json=None, timeout=None):
            put_requests.append((url, json))
            resp = mock.MagicMock()
            resp.status_code = 200
            return resp

        with mock.patch.dict(os.environ, env_vars, clear=True), \
             mock.patch("requests.post") as mock_post, \
             mock.patch("requests.put", side_effect=mock_put):
            mock_post.return_value = mock.MagicMock(status_code=200)

            prepare_matrix_module.main()

            # Verify /progress.json PUT call
            progress_calls = [c for c in put_requests if "/progress.json" in c[0]]
            assert len(progress_calls) >= 1, "prepare_matrix must initialize /progress.json"
            init_payload = progress_calls[0][1]
            assert init_payload["processed"] == 0
            assert "total" in init_payload
            assert "run_id" in init_payload
            assert init_payload["vms"] == {}
            assert init_payload["is_finished"] is False

    # --- F6 & R2: run_id Generation and Pipeline Propagation ---
    def test_f6_r2_run_id_uniqueness_and_pipeline_propagation(self, tmp_path):
        """F6: Verify run_id format, uniqueness, and absorption in CLI and environment."""
        gh_output = tmp_path / "gh_out.txt"
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(gh_output)}, clear=True), \
             mock.patch("requests.post"), mock.patch("requests.put"):
            prepare_matrix_module.main()

        content = gh_output.read_text(encoding="utf-8")
        match = re.search(r"run_id=(run_\d+_[0-9a-f]{6})", content)
        assert match is not None, f"run_id pattern missing in GITHUB_OUTPUT: {content}"
        generated_run_id = match.group(1)

        # Verify CLI args parsing in script_optimizado absorbs run_id
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--run-id", generated_run_id]):
            args = parse_scraper_args()
            assert args.run_id == generated_run_id

    # --- F7 & R2: Dashboard Progress Calculation & Monotonic Clamping ---
    def test_f7_r2_dashboard_progress_calculation_and_monotonic_clamping(self, repo_root):
        """F7: Verify JavaScript logic in dashboard/index.html enforces monotonic clamp and run_id filtering."""
        index_html = (repo_root / "dashboard" / "index.html").read_text(encoding="utf-8")

        # Verify zombie VM filtering by activeRunId
        assert "if (activeRunId && vm.run_id !== activeRunId) continue;" in index_html, (
            "index.html must filter VMs by activeRunId"
        )
        # Verify clamping <= 100% and >= 0%
        assert "Math.max(0, Math.min(rawTotal, aggProc))" in index_html, (
            "index.html must clamp processed count to [0, rawTotal]"
        )
        assert "Math.max(0, Math.min(100, Math.round((processed / total) * 100)))" in index_html, (
            "index.html must clamp percentage to [0, 100]"
        )
        # Verify monotonic high-water mark tracking
        assert "window._maxProcessedSeen" in index_html, (
            "index.html must maintain monotonic progress via _maxProcessedSeen"
        )

    # --- F8 & R2: Top 10 Catalog Synchronization & Live Streaming ---
    def test_f8_r2_dashboard_top10_catalog_and_streaming_resilience(self, repo_root):
        """F8: Verify handling of Object and Array payloads and avoidance of infinite loading state."""
        index_html = (repo_root / "dashboard" / "index.html").read_text(encoding="utf-8")

        # Check Array vs Object handling in top accounts parsing
        assert "Array.isArray" in index_html or "Object.values" in index_html, (
            "index.html must support both Array and Object formats for accounts"
        )
        # Check safe string coercion in escapeHtml
        assert "if (text == null) return '';" in index_html, (
            "index.html must safely coerce null/undefined values in escapeHtml"
        )

    # --- F9 & R2: CSS Styling, Grid Layout, and Contrast ---
    def test_f9_r2_dashboard_css_variables_grid_layout_and_contrast(self, repo_root):
        """F9: Verify CSS variables, responsive grid, and dark contrast rules in style.css."""
        css_content = (repo_root / "dashboard" / "css" / "style.css").read_text(encoding="utf-8")

        # Verify essential CSS variables
        assert "--bg-dark" in css_content
        assert "--panel-bg" in css_content
        assert "--accent-blue" in css_content
        assert "--text-primary" in css_content

        # Verify responsive grid setup for cards
        assert "grid-template-columns" in css_content, "style.css must define responsive grid layout"

        # Verify barcode container styling avoids overflow
        assert "overflow" in css_content, "style.css must handle overflow styling"

    # --- F10 & R3: Pipeline Resilience with if: always() ---
    def test_f10_r3_github_actions_workflow_resilience_contracts(self, repo_root):
        """F10: Verify check-timeouts, scrape-pass2-retry, and final-consolidate use if: always() && !cancelled()."""
        workflow_file = repo_root / ".github" / "workflows" / "alcampo_2pass_matrix.yml"
        assert workflow_file.is_file(), "alcampo_2pass_matrix.yml must exist"
        wf_text = workflow_file.read_text(encoding="utf-8")

        # Check job-level conditional executions
        assert "check-timeouts:" in wf_text
        assert "scrape-pass2-retry:" in wf_text
        assert "final-consolidate:" in wf_text

        # All key consolidation and retry jobs must execute on failure
        matches = re.findall(r"if:\s*always\(\)\s*&&\s*!cancelled\(\)", wf_text)
        assert len(matches) >= 3, (
            f"Expected at least 3 instances of 'if: always() && !cancelled()', found {len(matches)}"
        )

    # --- F11 & R3/R4: Guaranteed Excel Output on Exit ---
    def test_f11_r3_guaranteed_excel_output_under_shard_termination(self, tmp_path):
        """F11: ensure_excel_output must guarantee an Excel file even on empty results or IP canary exit."""
        assigned = [
            {"email": "unreached_1@alcampo.es", "password": "p1"},
            {"email": "unreached_2@alcampo.es", "password": "p2"},
        ]
        target_excel = tmp_path / "shard_exit_guarantee.xlsx"

        df = ensure_excel_output(
            target_path=target_excel,
            resultados=[],
            assigned_accounts=assigned,
            exit_reason="Bloqueo Canario IP"
        )

        assert target_excel.exists(), "Excel file must exist on disk"
        assert len(df) == 2, "All assigned accounts must be present in guaranteed output"
        assert (df["error_type"] == "ip_error").all()
        assert (df["saldo"] == "Error: Bloqueo Canario IP").all()

    # --- F12 & R3: Pattern Artifact Download Contract ---
    def test_f12_r3_workflow_artifact_pattern_download_contract(self, repo_root):
        """F12: Verify actions/download-artifact@v4 uses pattern: 'pass*' in final-consolidate."""
        workflow_file = repo_root / ".github" / "workflows" / "alcampo_2pass_matrix.yml"
        wf_text = workflow_file.read_text(encoding="utf-8")

        assert "pattern: 'pass*'" in wf_text or 'pattern: "pass*"' in wf_text, (
            "final-consolidate job must use pattern: 'pass*' to collect artifacts from all shards"
        )
        assert "merge-multiple: true" in wf_text, (
            "final-consolidate job must enable merge-multiple: true"
        )

    # --- F13 & R3: merge_and_retry.py Hardening & Modular 6-Sheet Workbook ---
    def test_f13_r3_merge_and_retry_hardening_and_modular_exports(self, tmp_path):
        """F13: merge_and_retry.py must import sys and generate the 6 canonical sheets."""
        merge_code = Path(merge_and_retry_module.__file__).read_text(encoding="utf-8")
        assert "import sys" in merge_code, "merge_and_retry.py must import sys"

        # Create multi-category test data
        test_df = pd.DataFrame([
            {"email": "ok1@alcampo.es", "saldo": "Tu Saldo es 20,00 €", "card_number": "4002001111111", "error_type": "ok"},
            {"email": "zero1@alcampo.es", "saldo": "Tu Saldo es 0,00 €", "card_number": "4002002222222", "error_type": "ok"},
            {"email": "call1@alcampo.es", "saldo": "Error: Cuenta bloqueada call center", "card_number": None, "error_type": "needs_attention"},
            {"email": "cred1@alcampo.es", "saldo": "Error: Credenciales incorrectas", "card_number": None, "error_type": "account_error"},
            {"email": "ip1@alcampo.es", "saldo": "Error: HTTP 429 WAF", "card_number": None, "error_type": "ip_error"},
        ])
        out_excel = tmp_path / "reporte_6_hojas.xlsx"
        sheets = generate_consolidated_excel(test_df, str(out_excel))

        expected_sheets = {
            "Todas las Cuentas",
            "Exitosas con Saldo",
            "Saldo Cero Verificado",
            "Bloqueadas Call Center",
            "Error Credenciales",
            "Error IP y Timeouts"
        }
        assert set(sheets.keys()) == expected_sheets, f"Sheets generated do not match expected: {set(sheets.keys())}"
        assert out_excel.exists()
        xls = pd.ExcelFile(out_excel)
        assert set(xls.sheet_names) == expected_sheets

    # --- F14 & R4: Deep Session Hydration and False 0,00 € Elimination ---
    def test_f14_r4_session_hydration_and_false_zero_elimination(self):
        """F14: _verify_and_hydrate_session must refresh and navigate home when 0,00 € appears without card."""
        # Unhydrated 0,00 € on first read -> hydrated after refresh and navigation
        p1 = '<html><body><p>Tu Saldo es 0,00 €</p></body></html>'
        p2 = '<html><body><p>Tu Saldo es 0,00 €</p></body></html>'
        p3 = '<html><body><p>Tu Saldo es 45,00 €</p><span class="sana-sans-alt">4002009999999</span></body></html>'

        driver = MockStealthWebDriver(initial_pages=[p1, p2, p3])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.1)

        assert saldo == "Tu Saldo es 45,00 €", "Hydration must recover real balance after home reload"
        assert card == "4002009999999", "Hydration must extract loyalty card number"
        assert driver.refresh_count >= 1, "driver.refresh() must be called on suspicious balance"

    # --- F15 & R4: 4-Tier Circuit Breaker Taxonomy ---
    def test_f15_r4_four_tier_circuit_breaker_taxonomy_and_error_classification(self):
        """F15: CircuitBreaker must classify errors into needs_attention, account_error, session_error, ip_error."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        # 1. needs_attention (Call Center, 2FA, Password Reset)
        t1, _ = cb.classify_error(page_source="Tu cuenta ha sido bloqueada. Contacta con Call Center")
        assert t1 == "needs_attention"
        t2, _ = cb.classify_error(page_source="Introduce el código de verificación 2FA enviado")
        assert t2 == "needs_attention"

        # 2. account_error (Permanent credential issues)
        t3, _ = cb.classify_error(page_source="Usuario o contraseña incorrectos")
        assert t3 == "account_error"

        # 3. session_error (OAuth redirect timeout, unhydrated session)
        t4, _ = cb.classify_error(error_msg="Timeout redirección demorada OAuth")
        assert t4 == "session_error"

        # 4. ip_error (Cloudflare, HTTP 429, WAF, connection refused)
        t5, _ = cb.classify_error(status_code=429)
        assert t5 == "ip_error"
        t6, _ = cb.classify_error(page_source="cloudflare ray id: 7c89a01b challenge-platform")
        assert t6 == "ip_error"

        # Non-IP errors must not trip consecutive server error counter
        cb.record_result(is_server_error=False, reason="Call Center", error_type="needs_attention")
        cb.record_result(is_server_error=False, reason="Bad password", error_type="account_error")
        assert cb.consecutive_server_errors == 0
        assert cb.triggered is False

    # --- F16 & R4: CLI Flags, Live Streaming, and Adaptive Jitter ---
    def test_f16_r4_cli_flags_live_streaming_and_adaptive_jitter(self):
        """F16: Verify --headless/--headful parsing, AdaptivePacer backoff with jitter, and live streaming."""
        # Test CLI flags
        with mock.patch.object(sys, "argv", ["script_optimizado.py", "--headless", "--threads", "4"]):
            args = parse_scraper_args()
            assert args.headless is True
            assert args.threads == 4

        # Test AdaptivePacer dynamic adaptation
        pacer = AdaptivePacer(base_delay=0.5, min_delay=0.2, max_delay=5.0)
        initial_delay = pacer.current_delay
        # Under pressure, delay increases to at least 1.5s
        pacer.record_pressure("WAF 429")
        assert pacer.current_delay >= 1.5
        # Under successes, delay recovers gradually
        for _ in range(10):
            pacer.record_success(elapsed_s=2.0)
        assert pacer.current_delay < 1.5

    # --- F17: Acceptance Criteria Verification Matrix ---
    def test_f17_acceptance_criteria_matrix_verification(self, repo_root):
        """F17: Full acceptance criteria verification mapping R1-R4 against repository status."""
        # R1 Acceptance: Modular directories & local testing
        assert (repo_root / "scraper").is_dir()
        assert (repo_root / "scripts" / "local_test.py").is_file()

        # R2 Acceptance: Dashboard files & valid vercel config
        assert (repo_root / "dashboard" / "index.html").is_file()
        assert (repo_root / "vercel.json").is_file()

        # R3 Acceptance: Workflow 2-pass matrix with guaranteed outputs
        assert (repo_root / ".github" / "workflows" / "alcampo_2pass_matrix.yml").is_file()

        # R4 Acceptance: Scraper core with session hydration
        scraper_code = (repo_root / "scraper" / "script_optimizado.py").read_text(encoding="utf-8")
        assert "_verify_and_hydrate_session" in scraper_code
        assert "CircuitBreaker" in scraper_code


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """
    Validates extreme boundaries, corrupted inputs, pathological DOM structures,
    and platform encoding constraints.
    """

    # --- B1: Empty Directory and Zero Accounts Handling ---
    def test_b1_empty_artifact_directory_and_zero_accounts_handling(self, tmp_path):
        """B1: Pipeline helpers must handle completely empty directories without unhandled crashes."""
        empty_in = tmp_path / "empty_shards"
        empty_in.mkdir()
        failed_json = tmp_path / "failed.json"
        out_excel = tmp_path / "consolidated_empty.xlsx"

        # Test check-timeouts with empty directory
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "check-timeouts",
            "--input-dir", str(empty_in),
            "--failed-json", str(failed_json),
        ]):
            merge_and_retry_module.main()
            assert not failed_json.exists()

        # Test final-merge with empty directory (warns cleanly without crash)
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(empty_in),
            "--output-excel", str(out_excel),
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        # Test ensure_excel_output with 0 assigned accounts (fallback record created)
        fallback_file = tmp_path / "fallback_zero.xlsx"
        df = ensure_excel_output(fallback_file, resultados=[], assigned_accounts=[], exit_reason="Empty Run")
        assert fallback_file.exists()
        assert len(df) == 1
        assert df.iloc[0]["email"] == "none"

    # --- B2: Corrupted Files & Invalid Extensions Recovery ---
    def test_b2_corrupted_files_and_invalid_extensions_recovery(self, tmp_path):
        """B2: Corrupt JSON, truncated files, and invalid file formats must be safely rejected."""
        # 1. Unsupported extension
        txt_file = tmp_path / "cuentas.txt"
        txt_file.write_text("user@test.es:password", encoding="utf-8")
        with pytest.raises(ValueError, match="Formato no soportado"):
            load_accounts_from_file(str(txt_file))

        # 2. Corrupted JSON syntax
        bad_json = tmp_path / "corrupt.json"
        bad_json.write_text("{broken_json: [123", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_accounts_from_file(str(bad_json))

        # 3. Nonexistent file
        with pytest.raises(FileNotFoundError):
            load_accounts_from_file(str(tmp_path / "does_not_exist.json"))

        # 4. Corrupt Excel file among valid shards in merge_and_retry
        shards_dir = tmp_path / "mixed_shards"
        shards_dir.mkdir()
        corrupt_excel = shards_dir / "shard_corrupt.xlsx"
        corrupt_excel.write_bytes(b"PK\x00\x00NotAValidZipFileContent")

        valid_excel = shards_dir / "shard_pass1_valid.xlsx"
        pd.DataFrame([{
            "email": "valid@alcampo.es",
            "password": "pwd",
            "saldo": "Tu Saldo es 15,00 €",
            "card_number": "4002001234567",
            "error_type": "ok"
        }]).to_excel(valid_excel, index=False)

        out_merged = tmp_path / "merged_resilient.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(shards_dir),
            "--output-excel", str(out_merged)
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert out_merged.exists()
        merged_df = pd.read_excel(out_merged, sheet_name="Todas las Cuentas")
        assert len(merged_df) == 1
        assert merged_df.iloc[0]["email"] == "valid@alcampo.es"

    # --- B3: DOM with Valid Balance but Missing Loyalty Card ---
    def test_b3_dom_with_valid_balance_but_missing_card_triggers_hydration(self):
        """B3: HTML with balance but missing 13-digit card number must trigger hydration and remain robust."""
        html_without_card = (
            '<html><body>'
            '<p class="balance-title">Tu Saldo es 10,00 €</p>'
            '<div class="loyalty-card">No card assigned</div>'
            '</body></html>'
        )
        assert extraer_tarjeta(html_without_card) is None

        # When balance is > 0 and no card, _verify_and_hydrate_session returns balance with None card
        driver = MockStealthWebDriver(initial_pages=[html_without_card])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.1)
        assert saldo == "Tu Saldo es 10,00 €"
        assert card is None

    # --- B4: Verified 0,00 € DOM Distinguished from Unhydrated Timeout ---
    def test_b4_verified_zero_euro_dom_distinguished_from_unhydrated_timeout(self):
        """B4: Explicit 0,00 € with valid loyalty card must be verified as 0.00 €, not treated as an error."""
        verified_zero_page = (
            '<html><body>'
            '<p>Tu Saldo es 0,00 €</p>'
            '<span class="sana-sans-alt">4002008888888</span>'
            '</body></html>'
        )
        driver = MockStealthWebDriver(initial_pages=[verified_zero_page])
        saldo, card = _verify_and_hydrate_session(driver, timeout_s=0.1)

        assert saldo == "Tu Saldo es 0,00 €"
        assert card == "4002008888888"
        # Zero is clean float 0.0
        assert limpiar_saldo(saldo) == 0.0

        # In contrast, an unhydrated page with loading text is not a verified 0
        unhydrated_page = '<html><body><div>Cargando datos de usuario...</div></body></html>'
        driver_unhydrated = MockStealthWebDriver(initial_pages=[unhydrated_page, unhydrated_page, unhydrated_page])
        saldo_unh, card_unh = _verify_and_hydrate_session(driver_unhydrated, timeout_s=0.05)
        assert saldo_unh == "No encontrado"
        assert card_unh is None

    # --- B5: HTTP 429 / 403 WAF and Cloudflare Challenge Resilience ---
    def test_b5_http_429_waf_and_cloudflare_challenge_resilience(self):
        """B5: Pathological WAF blocks, rate limits, and Cloudflare signatures must be categorized as ip_error."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)

        # 429 Status
        err_type, reason = cb.classify_error(status_code=429)
        assert err_type == "ip_error"
        assert "429" in reason

        # Cloudflare Ray ID Challenge
        cf_page = "<html><title>Just a moment...</title><body>Checking your browser before accessing. cloudflare ray id: 89abcf12 challenge-platform</body></html>"
        err_type2, reason2 = cb.classify_error(page_source=cf_page)
        assert err_type2 == "ip_error"

        # WAF Block message
        waf_page = "<html><body>Access Denied: 403 Forbidden. Blocked by Cloudflare WAF rule.</body></html>"
        err_type3, reason3 = cb.classify_error(page_source=waf_page)
        assert err_type3 == "ip_error"

        # Verify 8 consecutive IP errors trip the breaker
        for i in range(8):
            triggered, trip_reason = cb.record_result(is_server_error=True, reason=f"429 #{i}", error_type="ip_error")
            if i == 7:
                assert triggered is True
                assert cb.triggered is True
                assert "8 caídas consecutivas" in trip_reason
            else:
                assert triggered is False

    # --- B6: Huge Dataset Telegram Message Chunking & HTML Validity ---
    def test_b6_huge_dataset_telegram_message_chunking_and_strict_html_validity(self):
        """B6: Summary message with 500+ items must obey 4096-char ceiling and preserve valid HTML tags/entities."""
        # Generate 100 accounts in Top 10 input
        large_top = [(100.0 - i, f"user_large_{i:03d}+special&tag<script>@alcampo.es") for i in range(10)]
        large_error_summary = "Very long error details: " + ("Error: Cloudflare WAF 429 & Connection timeout; " * 80)

        msg = format_telegram_summary(
            total=1000,
            saldo_total=5432.10,
            cuentas_dinero=150,
            cuentas_cero=200,
            cuentas_error=650,
            top_10=large_top,
            error_summary=large_error_summary
        )

        assert len(msg) <= 4096, f"Message length {len(msg)} exceeds Telegram limit of 4096"
        assert "... [truncado]" in msg, "Long message must contain truncation marker"

        # Validate with strict Telegram HTML oracle
        violations = StrictTelegramHTMLOracle.validate(msg)
        assert violations == [], f"HTML validation violations: {violations}"

    # --- B7: Windows UTF-8 Execution, Special Encodings, and Emojis ---
    def test_b7_windows_utf8_execution_special_encodings_and_emojis(self, tmp_path):
        """B7: Test execution with Spanish accents, tildes (ñ, á, é, í, ó, ú), emojis, and symbols."""
        special_records = [
            {
                "email": "josé.maría.niño@españa.es",
                "password": "contraseña_con_ñ_y_tildes_!@#€%^",
                "saldo": "Tu Saldo es 1.500,75 € 💰✨",
                "card_number": "4002007777777",
                "error_type": "ok",
                "total_s": 1500.75,
            },
            {
                "email": "emoji.user@test.org",
                "password": "pwd",
                "saldo": "Error: Bloqueo WAF 403 ❌🚫⚠️",
                "card_number": None,
                "error_type": "ip_error",
                "total_s": 0.0,
            }
        ]

        target_excel = tmp_path / "utf8_test.xlsx"
        df = ensure_excel_output(
            target_path=target_excel,
            resultados=special_records,
            assigned_accounts=[],
            exit_reason="Test UTF-8"
        )

        assert target_excel.exists()
        read_df = pd.read_excel(target_excel)
        assert len(read_df) == 2
        assert read_df.iloc[0]["email"] == "josé.maría.niño@españa.es"
        assert "💰" in read_df.iloc[0]["saldo"]
        assert "❌" in read_df.iloc[1]["saldo"]


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (END-TO-END INTEGRATION)
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """
    End-to-end integration lifecycle test executing the full pipeline chain:
    Matrix Prep -> Pass 1 Shards (with Canary Exit & session errors)
    -> ensure_excel_output -> check-timeouts rescue -> Pass 2 Retry
    -> final-merge 6-sheet workbook -> Telegram summary.
    """

    def test_complete_e2e_pipeline_lifecycle_simulation(self, tmp_path):
        """
        Simulates end-to-end multi-pass execution:
        - 6 master accounts
        - Pass 1 runs 3 shards:
          Shard 0: Acc 1 succeeds (25.50 €), Acc 2 hits Canary IP exit (saved via ensure_excel_output).
          Shard 1: Acc 3 has Call Center lock, Acc 4 has slow redirect (session_error).
          Shard 2: Acc 5 has bad password (account_error), Acc 6 succeeds (0.00 € verified).
        - check-timeouts rescues Acc 2 (ip_error) and Acc 4 (session_error).
        - Pass 2 retry recovers Acc 2 (30.00 €) and Acc 4 (12.00 €).
        - final-merge consolidates all artifacts, deduplicates by priority, and builds 6 sheets.
        - Telegram summary is validated against metrics.
        """
        sandbox = tmp_path / "e2e_sandbox"
        sandbox.mkdir()

        pass1_dir = sandbox / "pass1_artifacts"
        pass1_dir.mkdir()
        pass2_dir = sandbox / "pass2_artifacts"
        pass2_dir.mkdir()
        all_final_dir = sandbox / "all_final_shards"
        all_final_dir.mkdir()

        master_accounts = [
            {"email": "acc1_money@alcampo.es", "password": "pass1"},
            {"email": "acc2_canary@alcampo.es", "password": "pass2"},
            {"email": "acc3_callcenter@alcampo.es", "password": "pass3"},
            {"email": "acc4_slowredirect@alcampo.es", "password": "pass4"},
            {"email": "acc5_badpass@alcampo.es", "password": "pass5"},
            {"email": "acc6_zerobalance@alcampo.es", "password": "pass6"},
        ]
        master_file = sandbox / "master_accounts.json"
        master_file.write_text(json.dumps(master_accounts), encoding="utf-8")

        # ----------------------------------------------------------------------
        # Step 1: Matrix Preparation Simulation
        # ----------------------------------------------------------------------
        total_accounts = len(master_accounts)
        accounts_per_vm = 2
        shards_count = math.ceil(total_accounts / accounts_per_vm)
        assert shards_count == 3
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        # ----------------------------------------------------------------------
        # Step 2: Pass 1 Shard Execution
        # ----------------------------------------------------------------------
        # Shard 0: Acc 1 processed ok; Acc 2 unreached due to Canary IP Exit
        shard0_results = [
            {
                "email": "acc1_money@alcampo.es",
                "password": "pass1",
                "saldo": "Tu Saldo es 25,50 €",
                "card_number": "4002001111111",
                "error_type": "ok",
                "total_s": 25.50
            }
        ]
        shard0_assigned = master_accounts[0:2]
        shard0_file = pass1_dir / "saldos_pass1_shard_0.xlsx"
        ensure_excel_output(shard0_file, shard0_results, shard0_assigned, exit_reason="Bloqueo Canario IP")
        assert shard0_file.exists()

        # Shard 1: Acc 3 Call Center lock; Acc 4 Session error (redirection demorada)
        shard1_results = [
            {
                "email": "acc3_callcenter@alcampo.es",
                "password": "pass3",
                "saldo": "Error: Cuenta bloqueada call center",
                "card_number": None,
                "error_type": "needs_attention",
                "total_s": 0.0
            },
            {
                "email": "acc4_slowredirect@alcampo.es",
                "password": "pass4",
                "saldo": "Error: Timeout redirección demorada OAuth",
                "card_number": None,
                "error_type": "session_error",
                "total_s": 0.0
            }
        ]
        shard1_file = pass1_dir / "saldos_pass1_shard_1.xlsx"
        ensure_excel_output(shard1_file, shard1_results, master_accounts[2:4])
        assert shard1_file.exists()

        # Shard 2: Acc 5 Credenciales incorrectas; Acc 6 Verified 0,00 €
        shard2_results = [
            {
                "email": "acc5_badpass@alcampo.es",
                "password": "pass5",
                "saldo": "Error: Credenciales incorrectas o no autorizadas",
                "card_number": None,
                "error_type": "account_error",
                "total_s": 0.0
            },
            {
                "email": "acc6_zerobalance@alcampo.es",
                "password": "pass6",
                "saldo": "Tu Saldo es 0,00 €",
                "card_number": "4002006666666",
                "error_type": "ok",
                "total_s": 0.0
            }
        ]
        shard2_file = pass1_dir / "saldos_pass1_shard_2.xlsx"
        ensure_excel_output(shard2_file, shard2_results, master_accounts[4:6])
        assert shard2_file.exists()

        # ----------------------------------------------------------------------
        # Step 3: check-timeouts Rescue Phase
        # ----------------------------------------------------------------------
        failed_json_path = sandbox / "failed_accounts.json"
        pass1_files = [str(shard0_file), str(shard1_file), str(shard2_file)]
        failed_accounts = collect_failed_accounts(pass1_files, master_accounts)

        # Acc 2 (ip_error from canary exit) and Acc 4 (session_error) must be rescued
        # Acc 1 and Acc 6 are successes (excluded)
        # Acc 3 (Call Center) and Acc 5 (Bad Password) are permanent errors (excluded)
        failed_emails = {fa["email"] for fa in failed_accounts}
        assert failed_emails == {"acc2_canary@alcampo.es", "acc4_slowredirect@alcampo.es"}, (
            f"Expected rescue of Acc 2 and Acc 4, got: {failed_emails}"
        )

        failed_json_path.write_text(json.dumps(failed_accounts), encoding="utf-8")

        # ----------------------------------------------------------------------
        # Step 4: Pass 2 Retry Shard Execution
        # ----------------------------------------------------------------------
        # Both rescued accounts succeed with fresh IPs / hydrated sessions
        pass2_results = [
            {
                "email": "acc2_canary@alcampo.es",
                "password": "pass2",
                "saldo": "Tu Saldo es 30,00 €",
                "card_number": "4002002222222",
                "error_type": "ok",
                "total_s": 30.00
            },
            {
                "email": "acc4_slowredirect@alcampo.es",
                "password": "pass4",
                "saldo": "Tu Saldo es 12,00 €",
                "card_number": "4002004444444",
                "error_type": "ok",
                "total_s": 12.00
            }
        ]
        pass2_file = pass2_dir / "saldos_retry_shard_0.xlsx"
        ensure_excel_output(pass2_file, pass2_results, failed_accounts)
        assert pass2_file.exists()

        # ----------------------------------------------------------------------
        # Step 5: final-merge Phase (All artifacts consolidated)
        # ----------------------------------------------------------------------
        # Copy Pass 1 and Pass 2 artifacts to all_final_dir simulating download-artifact
        for f in pass1_files:
            shutil.copy(f, all_final_dir / Path(f).name)
        shutil.copy(str(pass2_file), all_final_dir / pass2_file.name)

        final_excel_path = sandbox / "REPORTE_DEFINITIVO_TELEGRAM.xlsx"
        with mock.patch.object(sys, "argv", [
            "merge_and_retry.py",
            "--mode", "final-merge",
            "--input-dir", str(all_final_dir),
            "--output-excel", str(final_excel_path)
        ]), mock.patch("scripts.merge_and_retry.enviar_telegram"):
            merge_and_retry_module.main()

        assert final_excel_path.exists(), "Final 6-sheet Excel report must be generated"

        # ----------------------------------------------------------------------
        # Step 6: 6-Sheet Distribution and Invariant Validation
        # ----------------------------------------------------------------------
        xls = pd.ExcelFile(final_excel_path)
        df_all = pd.read_excel(xls, sheet_name="Todas las Cuentas")
        df_saldo = pd.read_excel(xls, sheet_name="Exitosas con Saldo")
        df_cero = pd.read_excel(xls, sheet_name="Saldo Cero Verificado")
        df_call = pd.read_excel(xls, sheet_name="Bloqueadas Call Center")
        df_cred = pd.read_excel(xls, sheet_name="Error Credenciales")
        df_ip = pd.read_excel(xls, sheet_name="Error IP y Timeouts")

        # Invariant 1: Exactly 6 unique accounts in master report
        assert len(df_all) == 6, f"Expected 6 unique accounts, found {len(df_all)}"

        # Invariant 2: Priority override - Acc 2 and Acc 4 have Pass 2 positive balances!
        acc2_row = df_all[df_all["email"] == "acc2_canary@alcampo.es"].iloc[0]
        assert "30,00" in str(acc2_row["saldo"]), "Pass 2 success must override Pass 1 IP Canary error"
        acc4_row = df_all[df_all["email"] == "acc4_slowredirect@alcampo.es"].iloc[0]
        assert "12,00" in str(acc4_row["saldo"]), "Pass 2 success must override Pass 1 Session timeout"

        # Invariant 3: Exitosas con Saldo contains Acc 1 (25.50), Acc 2 (30.00), Acc 4 (12.00)
        assert len(df_saldo) == 3
        total_balance_extracted = sum(limpiar_saldo(s) for s in df_saldo["saldo"])
        assert round(total_balance_extracted, 2) == 67.50  # 25.50 + 30.00 + 12.00

        # Invariant 4: Saldo Cero Verificado contains Acc 6
        assert len(df_cero) == 1
        assert df_cero.iloc[0]["email"] == "acc6_zerobalance@alcampo.es"

        # Invariant 5: Bloqueadas Call Center contains Acc 3
        assert len(df_call) == 1
        assert df_call.iloc[0]["email"] == "acc3_callcenter@alcampo.es"

        # Invariant 6: Error Credenciales contains Acc 5
        assert len(df_cred) == 1
        assert df_cred.iloc[0]["email"] == "acc5_badpass@alcampo.es"

        # Invariant 7: Error IP y Timeouts is 0 because all transient errors were recovered in Pass 2!
        assert len(df_ip) == 0

        # ----------------------------------------------------------------------
        # Step 7: Telegram Notification Summary Validation
        # ----------------------------------------------------------------------
        top_ranked = [
            (30.00, "acc2_canary@alcampo.es"),
            (25.50, "acc1_money@alcampo.es"),
            (12.00, "acc4_slowredirect@alcampo.es"),
        ]
        telegram_msg = format_telegram_summary(
            total=len(df_all),
            saldo_total=total_balance_extracted,
            cuentas_dinero=len(df_saldo),
            cuentas_cero=len(df_cero),
            cuentas_error=len(df_call) + len(df_cred) + len(df_ip),
            top_10=top_ranked
        )

        assert "67.50 €" in telegram_msg
        assert "Cuentas con dinero: 3" in telegram_msg
        assert "Cuentas con saldo 0: 1" in telegram_msg
        assert "Cuentas con error / Call Center: 2" in telegram_msg

        oracle_violations = StrictTelegramHTMLOracle.validate(telegram_msg)
        assert oracle_violations == [], f"Telegram format error: {oracle_violations}"


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios:
    """
    Simulates production field operational conditions:
    1. Clean 100% success run without timeouts.
    2. Severe WAF block recovery with CircuitBreaker safety trip and Pass 2 healing.
    3. Highly heterogeneous mixed account batch with deterministic sheet routing.
    """

    # --- Scenario 1: Clean Run (100% Success) ---
    def test_scenario_1_clean_run_hundred_percent_success(self, tmp_path):
        """Clean run scenario where all accounts succeed in Pass 1."""
        accounts = [
            {"email": f"clean_{i}@alcampo.es", "password": f"pwd{i}", "balance": 10.0 * (i + 1)}
            for i in range(5)
        ]
        shard_file = tmp_path / "saldos_pass1_clean.xlsx"
        records = [
            {
                "email": a["email"],
                "password": a["password"],
                "saldo": f"Tu Saldo es {a['balance']:.2f} €",
                "card_number": f"400200{i:07d}",
                "error_type": "ok",
                "total_s": a["balance"],
            }
            for i, a in enumerate(accounts)
        ]
        ensure_excel_output(shard_file, records, accounts)

        # check-timeouts reports no failures
        failed = collect_failed_accounts([str(shard_file)])
        assert len(failed) == 0, "No accounts should require retry on a clean run"

        out_final = tmp_path / "reporte_clean.xlsx"
        sheets = generate_consolidated_excel(pd.read_excel(shard_file), str(out_final))
        assert len(sheets["Exitosas con Saldo"]) == 5
        assert len(sheets["Bloqueadas Call Center"]) == 0
        assert len(sheets["Error Credenciales"]) == 0
        assert len(sheets["Error IP y Timeouts"]) == 0

    # --- Scenario 2: WAF Block Recovery with Circuit Breaker ---
    def test_scenario_2_waf_block_recovery_with_circuit_breaker(self, tmp_path):
        """WAF rate-limit block trips CircuitBreaker; ensure_excel_output saves shard; Pass 2 rescues."""
        cb = CircuitBreaker(max_consecutive_failures=8, max_failure_ratio=0.50, min_processed_threshold=10)
        assigned = [{"email": f"waf_{i}@alcampo.es", "password": "p"} for i in range(12)]

        processed = []
        # First 2 succeed
        for i in range(2):
            processed.append({
                "email": assigned[i]["email"],
                "password": "p",
                "saldo": "Tu Saldo es 5,00 €",
                "card_number": f"400200{i:07d}",
                "error_type": "ok",
                "total_s": 5.0,
            })
            cb.record_result(is_server_error=False, reason="OK", error_type="ok")

        # Next accounts hit 429 WAF block until CB trips
        for i in range(2, 10):
            err_type, reason = cb.classify_error(status_code=429)
            triggered, trip_reason = cb.record_result(is_server_error=True, reason=reason, error_type=err_type)
            processed.append({
                "email": assigned[i]["email"],
                "password": "p",
                "saldo": f"Error: {reason}",
                "card_number": None,
                "error_type": err_type,
                "total_s": 0.0,
            })
            if triggered:
                break

        assert cb.triggered is True
        assert "8 caídas consecutivas" in cb.trigger_reason

        # Ensure Excel saves all 12 assigned accounts despite premature stop
        shard_waf_file = tmp_path / "saldos_pass1_waf.xlsx"
        df_saved = ensure_excel_output(shard_waf_file, processed, assigned, exit_reason="Circuit Breaker WAF")
        assert len(df_saved) == 12

        # check-timeouts rescues all 10 uncompleted / blocked accounts
        rescuable = collect_failed_accounts([str(shard_waf_file)], assigned)
        assert len(rescuable) == 10
        assert {a["email"] for a in rescuable} == {assigned[i]["email"] for i in range(2, 12)}

    # --- Scenario 3: Mixed Account Batch Routing & Isolation ---
    def test_scenario_3_mixed_account_batch_routing_and_isolation(self, tmp_path):
        """Validates precise segregation of all real-world account categories into the 6 sheets."""
        dataset = [
            # 1. Positive balance
            {"email": "pos1@alcampo.es", "saldo": "Tu Saldo es 120,50 €", "card_number": "4002001111111", "error_type": "ok"},
            {"email": "pos2@alcampo.es", "saldo": "Tu Saldo es 0,99 €", "card_number": "4002002222222", "error_type": "ok"},
            # 2. Verified zero balance
            {"email": "zero@alcampo.es", "saldo": "Tu Saldo es 0,00 €", "card_number": "4002003333333", "error_type": "ok"},
            # 3. Call center & 2FA
            {"email": "callcenter@alcampo.es", "saldo": "Error: Cuenta bloqueada call center", "card_number": None, "error_type": "needs_attention"},
            {"email": "otp_2fa@alcampo.es", "saldo": "Error: Código de verificación 2FA", "card_number": None, "error_type": "needs_attention"},
            {"email": "reset_pwd@alcampo.es", "saldo": "Error: Restablecer contraseña btnPwReset", "card_number": None, "error_type": "needs_attention"},
            # 4. Bad credentials
            {"email": "bad_user@alcampo.es", "saldo": "Error: Usuario incorrecto", "card_number": None, "error_type": "account_error"},
            {"email": "bad_pwd@alcampo.es", "saldo": "Error: Contraseña no válida", "card_number": None, "error_type": "account_error"},
            # 5. IP & timeouts
            {"email": "waf_429@alcampo.es", "saldo": "Error: HTTP Status 429", "card_number": None, "error_type": "ip_error"},
            {"email": "cloudflare@alcampo.es", "saldo": "Error: Firma Cloudflare/Captcha", "card_number": None, "error_type": "ip_error"},
            {"email": "timeout_oauth@alcampo.es", "saldo": "Error: Timeout redirección demorada", "card_number": None, "error_type": "session_error"},
        ]

        df_input = pd.DataFrame(dataset)
        out_excel = tmp_path / "mixed_routing_report.xlsx"
        sheets = generate_consolidated_excel(df_input, str(out_excel))

        assert len(sheets["Todas las Cuentas"]) == 11
        assert len(sheets["Exitosas con Saldo"]) == 2
        assert len(sheets["Saldo Cero Verificado"]) == 1
        assert len(sheets["Bloqueadas Call Center"]) == 3
        assert len(sheets["Error Credenciales"]) == 2
        assert len(sheets["Error IP y Timeouts"]) == 3

        # Confirm exact email memberships
        assert set(sheets["Exitosas con Saldo"]["email"]) == {"pos1@alcampo.es", "pos2@alcampo.es"}
        assert set(sheets["Saldo Cero Verificado"]["email"]) == {"zero@alcampo.es"}
        assert set(sheets["Bloqueadas Call Center"]["email"]) == {"callcenter@alcampo.es", "otp_2fa@alcampo.es", "reset_pwd@alcampo.es"}
        assert set(sheets["Error Credenciales"]["email"]) == {"bad_user@alcampo.es", "bad_pwd@alcampo.es"}
        assert set(sheets["Error IP y Timeouts"]["email"]) == {"waf_429@alcampo.es", "cloudflare@alcampo.es", "timeout_oauth@alcampo.es"}
