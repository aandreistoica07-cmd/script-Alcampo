"""
Unit tests for AccountCooldownManager: failure tracking across dates, 5-day pause threshold,
and success recovery. Runs in-memory / tmp_path with zero external dependencies.
"""

import pytest
from scraper.account_cooldown_manager import AccountCooldownManager


class TestAccountCooldownManager:
    """Test suite for AccountCooldownManager logic."""

    @pytest.fixture
    def manager(self, tmp_path):
        status_file = tmp_path / "account_status_test.json"
        return AccountCooldownManager(status_file_path=str(status_file))

    def test_single_failure_does_not_trigger_cooldown(self, manager):
        email = "test1@alcampo.es"
        res = manager.record_result(email=email, is_success=False, error_msg="Error: timeout", today_str="2026-10-24")

        assert res["action"] == "failure_recorded"
        assert res["consecutive_failures"] == 1
        assert res["status"] == "active"

        acc = manager.get_account_status(email)
        assert acc["consecutive_failures"] == 1
        assert acc["status"] == "active"
        assert acc["cooldown_until"] is None

    def test_five_consecutive_failures_triggers_cooldown(self, manager):
        email = "test2@alcampo.es"
        dates = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"]

        # 4 consecutive days of failure: still active
        for i in range(4):
            res = manager.record_result(email=email, is_success=False, today_str=dates[i])
            assert res["action"] == "failure_recorded"
            assert res["consecutive_failures"] == i + 1
            assert res["status"] == "active"

        # 5th consecutive day of failure: enters cooldown for 5 days
        res5 = manager.record_result(email=email, is_success=False, today_str=dates[4])
        assert res5["action"] == "entered_cooldown"
        assert res5["consecutive_failures"] == 5
        assert res5["status"] == "cooling_down"
        assert res5["cooldown_until"] == "2026-10-29"

        acc = manager.get_account_status(email)
        assert acc["status"] == "cooling_down"
        assert acc["cooldown_until"] == "2026-10-29"

    def test_success_resets_failure_counter(self, manager):
        email = "test3@alcampo.es"
        dates = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]

        # 4 consecutive days of failure
        for d in dates:
            manager.record_result(email=email, is_success=False, today_str=d)

        assert manager.get_account_status(email)["consecutive_failures"] == 4

        # 1 success: resets failures to 0 and becomes active
        res = manager.record_result(email=email, is_success=True, today_str="2026-10-24")
        assert res["action"] == "success"
        assert res["consecutive_failures"] == 0
        assert res["status"] == "active"

        acc = manager.get_account_status(email)
        assert acc["consecutive_failures"] == 0
        assert acc["status"] == "active"
        assert acc["cooldown_until"] is None

    def test_filter_accounts_for_run_during_and_after_cooldown(self, manager):
        email_cooldown = "cooling@alcampo.es"
        email_active = "active@alcampo.es"
        dates = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"]

        # Put cooling into cooldown until 2026-10-29
        for d in dates:
            manager.record_result(email_cooldown, is_success=False, today_str=d)

        account_list = [{"email": email_cooldown}, {"email": email_active}]

        # Day 2026-10-25: cooldown still in effect
        eligible, skipped, retesting = manager.filter_accounts_for_run(account_list, today_str="2026-10-25")
        assert len(eligible) == 1
        assert eligible[0]["email"] == email_active
        assert len(skipped) == 1
        assert skipped[0]["email"] == email_cooldown

        # Day 2026-10-30: cooldown has expired, account is eligible for retesting
        eligible_after, skipped_after, retesting_after = manager.filter_accounts_for_run(account_list, today_str="2026-10-30")
        assert len(eligible_after) == 2
        assert len(retesting_after) == 1
        assert retesting_after[0]["email"] == email_cooldown

    def test_unpause_all_cooldowns(self, manager):
        email1 = "acc1@alcampo.es"
        email2 = "acc2@alcampo.es"
        dates = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"]

        for d in dates:
            manager.record_result(email1, is_success=False, today_str=d)
            manager.record_result(email2, is_success=False, today_str=d)

        assert manager.get_account_status(email1)["status"] == "cooling_down"
        assert manager.get_account_status(email2)["status"] == "cooling_down"

        unpaused_count = manager.unpause_all_cooldowns()
        assert unpaused_count == 2
        assert manager.get_account_status(email1)["status"] == "active"
        assert manager.get_account_status(email1)["consecutive_failures"] == 0
        assert manager.get_account_status(email2)["status"] == "active"
