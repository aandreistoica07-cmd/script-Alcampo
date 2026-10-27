"""Offline tests for final UI credentials; no scraper or production writes."""
import base64
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts.merge_and_retry import complete_top_account_passwords, load_master_accounts


@pytest.mark.parametrize("compressed", [False, True])
def test_final_top_recovers_passwords_from_secret(monkeypatch, compressed):
    accounts = [{"email": "user@example.test", "password": "  p:á<&001  "}]
    raw = json.dumps(accounts).encode("utf-8")
    if compressed:
        raw = gzip.compress(raw)
    monkeypatch.setenv("ACCOUNTS_BASE64", base64.b64encode(raw).decode("ascii"))
    # Ensure this test never reads repository account files.
    monkeypatch.setattr("scripts.merge_and_retry.os.path.exists", lambda _: False)
    top = [{"email": " USER@example.test ", "password": "", "balance": 12.5, "card_number": "123"}]
    result = complete_top_account_passwords(top, load_master_accounts())
    assert result == [{"email": " USER@example.test ", "password": "  p:á<&001  ",
                       "balance": 12.5, "card_number": "123"}]


@pytest.mark.parametrize("missing", [None, "", float("nan")])
def test_missing_passwords_and_existing_credentials(missing):
    top = [{"email": "a@example.test", "password": missing, "balance": 10},
           {"email": "b@example.test", "password": "existing", "balance": 9},
           {"email": "unknown@example.test", "password": None, "balance": 8}]
    master = [{"email": "a@example.test", "password": "001234"},
              {"email": "b@example.test", "password": "other"},
              {"email": "extra@example.test", "password": "excluded"}]
    result = complete_top_account_passwords(top, master)
    assert [a["password"] for a in result] == ["001234", "existing", ""]
    assert [a["balance"] for a in result] == [10, 9, 8]
    assert len(result) == 3


@pytest.mark.parametrize("password", ["nan", "None", "  keep spaces  ", "001234"])
def test_literal_passwords_are_preserved(password):
    top = [{"email": "a@example.test", "password": password}]
    assert complete_top_account_passwords(top, [{"email": "a@example.test", "password": "replacement"}])[0]["password"] == password


def test_final_export_uses_secret_in_isolated_cli(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    # Copy the CLI and its local dependency so even default paths stay isolated.
    for relative in ("scripts/merge_and_retry.py", "scraper/account_cooldown_manager.py"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / relative, target)
    shards = tmp_path / "shards"
    shards.mkdir()
    pd.DataFrame([{"email": "final@example.test", "saldo": "Tu Saldo es 12,50 €",
                   "card_number": "4002001111111"}]).to_excel(shards / "saldos_pass1_shard_0.xlsx", index=False)
    env = os.environ.copy()
    env.update(FIREBASE_DB_URL="false", TELEGRAM_TOKEN="none", TELEGRAM_CHAT_ID="none",
               ACCOUNTS_BASE64=base64.b64encode(json.dumps([
                   {"email": "final@example.test", "password": "001:secret"}
               ]).encode()).decode(), PYTHONIOENCODING="utf-8")
    result = subprocess.run([
        sys.executable, str(tmp_path / "scripts/merge_and_retry.py"),
        "--mode", "final-merge", "--input-dir", str(shards),
        "--output-excel", str(tmp_path / "report.xlsx"),
        "--dashboard-dir", str(tmp_path / "dashboard"),
        "--docs-dir", str(tmp_path / "docs")
    ], cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stderr
    assert "001:secret" not in result.stdout + result.stderr
    for folder in (tmp_path, tmp_path / "dashboard", tmp_path / "docs"):
        top = json.loads((folder / "top_accounts.json").read_text(encoding="utf-8"))
        assert top[0]["password"] == "001:secret"
        assert top[0]["balance"] == 12.5
