# Project: Alcampo Scraper & CI/CD Pipeline Optimization

## Architecture
- **Scraper Engine (`scraper/script_optimizado.py`)**: Selenium WebDriver automation with Chrome (headful/headless). Implements Circuit Breaker, Account Cooldown, Salesforce OAuth flow, Dual-Layer loyalty verification (`compraonline.alcampo.es` -> `miportal.alcampo.es`), and automatic screenshot capture.
- **Local Test Runner (`scripts/local_test.py`)**: Standalone debugging and validation tool with CLI arguments (`--email`, `--password`, `--headless`, `--slowmo`, `--screenshot-dir`).
- **Consolidator & Retry Pipeline (`scripts/merge_and_retry.py`)**: Consolidates Pass 1 matrix shards (`pass1_part_*.xlsx`), filters retries for Pass 2 dynamic queue, generates 6-sheet unified Excel workbook, computes Top 10 balances, sends sanitized HTML Telegram alert, and updates Firebase RTDB / Vercel dashboard.
- **Unit & Adversarial Test Suite (`tests/`)**: 47+ pytest tests covering CircuitBreaker, CooldownManager, matrix partitioning, merge logic, and scraper utilities without requiring Chrome or network.
- **E2E Testing Track**: Independent requirement-driven validation suite verifying all features, boundary cases, pairwise combinations, and real-world application scenarios.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Visual Screenshot Instrumentation | Automatic `save_screenshot` on errors (login timeout, btnPwReset, call center, WAF/Cloudflare) and anomalies (unhydrated balance, suspicious zero) in `local_test.py` and `script_optimizado.py` saving to `screenshots/` | M1 | Survey (R1) |
| 2 | Expanded Card Regex | Extend loyalty card extraction regex to include `400300\d{7}` and 13-digit EAN (`400\d{10}` and `280\d{10}`) | M2 | Survey (R4, Follow-up) |
| 3 | Dual-Layer Balance Fallback | If `compraonline` displays 0,00 € or error banner (`settings.loyalty.manage.alternative`) while `loyalty-manage-button` exists, navigate to `miportal.alcampo.es/es/cuenta/fidelidad` to extract genuine balance and card | M2 | Survey (R4, Follow-up) |
| 4 | Synchronize `btnPwReset` Handling | Ensure `scripts/local_test.py` mirrors `script_optimizado.py` by attempting re-login on Salesforce `btnPwReset` challenge | M2 | Survey (R2, R4) |
| 5 | Visual Audit on Critical Samples | Browser inspection across witness account (`noelia_gll@hotmail.com` with 3.00 €), candidate 0.00 €, pwreset challenge, and call center block | M3 | Survey (R2) |
| 6 | Cross-Agent Evidence Debate | Multi-agent analysis of DOM hydration times, headless Linux vs Windows CSS classes, root cause of false zeros, and Top 10 consolidation | M3 | Survey (R3) |
| 7 | Consolidation & Retry Refactor | Refactor `scripts/merge_and_retry.py` `is_definitive_success` so degraded 0 balances without card verification are retried in Pass 2; route positive balances to `Exitosas con Saldo` and Top 10 | M4 | Survey (R4) |
| 8 | Empirical Verification & Baseline Comparison | Run complete 47+ pytest suite (including fixing `test_scraper_utils.py`), verify local execution, and generate deployment comparison guide vs Run #382 | M5 | Survey (R5) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Systematic Screenshot Instrumentation | Add `capture_screenshot` across error/anomaly handlers in `scraper/script_optimizado.py` and `scripts/local_test.py` | none | DONE |
| M2 | Dual-Layer Loyalty Engine & Card Regex | Implement Capa 2 fallback to `miportal.alcampo.es`, `400300` regex, and `btnPwReset` re-login sync | M1 | DONE |
| M3 | Visual Audit & Multi-Agent Debate | Empirical verification of critical accounts and cross-agent consensus on DOM and false-zero elimination | M2 | DONE |
| M4 | Pipeline Consolidation & Top 10 Patch | Patch `scripts/merge_and_retry.py` for Pass 2 retry classification, Excel 6-sheet output, and Top 10 integrity | M2 | DONE |
| M5 | Empirical Verification & GHA Run Guide | Comprehensive test verification (47+ tests green), local run cert, and guide for GitHub Actions run vs #382 | M3, M4 | IN_PROGRESS |
| M6 | Final E2E Test Pass & Hardening | Pass 100% E2E test suite (Tiers 1-4) and Tier 5 adversarial coverage hardening | M5 | PLANNED |

## Interface Contracts
### `scraper/script_optimizado.py` ↔ `screenshots/`
- Function: `capture_screenshot(driver, email, label, screenshot_dir="screenshots")`
- Format: `screenshots/{safe_email}_{label}_{YYYYMMDD_HHMMSS}.png`
- Labels: `err_inputs`, `err_waf`, `err_call_center`, `err_needs_attention`, `err_timeout`, `saldo_positivo`, `saldo_cero_compraonline`, `saldo_cero_verificado`, `miportal_fallback`, `err_unexpected`

### `_verify_and_hydrate_session` (Capa 1 & Capa 2)
- Input: `driver`, `email`
- Output tuple: `(saldo_str, tarjeta_str)`
- Behavior:
  - Step 1: Check `compraonline.alcampo.es/settings/loyalty`.
  - Step 2: If `saldo` is `"Tu Saldo es 0,00 €"` or `None`, and element `data-test="loyalty-manage-button"` or text `"Parece que hay algo que no va bien"` exists, execute Capa 2:
    - Navigate to `https://www.miportal.alcampo.es/es/cuenta/fidelidad`.
    - Wait for `Saldo disponible` (up to 8s).
    - Extract `saldo` and `tarjeta` (matching `400\d{10}` or `280\d{10}`).
  - Step 3: Return verified tuple.

### `scripts/merge_and_retry.py` ↔ Consolidator
- Function: `is_definitive_success(saldo_str, tarjeta_str)`
- Behavior:
  - If `saldo_val > 0`: definitive success (`True`).
  - If `saldo_val == 0.0`: definitive success ONLY IF tarjeta is verified or fallback checked. If degraded without card, return `False` (retryable in Pass 2).

## Code Layout
- `scraper/script_optimizado.py`: Core Selenium scraper engine (GHA Matrix Shard worker).
- `scripts/local_test.py`: CLI test runner for single account inspection.
- `scripts/merge_and_retry.py`: Shard consolidator, retry queue builder, Excel/Telegram reporter.
- `tests/`: Pytest test suite (`test_circuit_breaker.py`, `test_cooldown_manager.py`, `test_matrix_calc.py`, `test_merge_and_retry.py`, `test_scraper_utils.py`).
- `screenshots/`: Storage directory for timestamped PNG audit captures.
- `dashboard/`: Frontend dashboard assets (`index.html`, `history.json`, `top_accounts.json`).
