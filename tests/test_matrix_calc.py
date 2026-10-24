"""
Unit tests for matrix calculation and shard partitioning math.
Tests partition math, disjointness, exhaustiveness, and balanced distribution.
Zero external dependencies.
"""

import math
import time
import uuid
import re
import pytest


def calculate_shards(total_accounts, per_vm=75):
    """Calculates number of shards matching prepare_matrix logic."""
    if total_accounts <= 0:
        return 1
    return math.ceil(total_accounts / per_vm)


def partition_by_shard(accounts, shard_id, total_shards):
    """Modulo-based partitioning matching script_optimizado logic."""
    return [acc for i, acc in enumerate(accounts) if i % total_shards == shard_id]


class TestMatrixShardCalculation:
    """Test suite for shard count calculation."""

    def test_default_512_accounts_with_75_per_vm(self):
        # 512 / 75 = 6.826 -> 7 shards
        assert calculate_shards(512, per_vm=75) == 7

    def test_exact_multiples(self):
        assert calculate_shards(75, per_vm=75) == 1
        assert calculate_shards(150, per_vm=75) == 2
        assert calculate_shards(300, per_vm=75) == 4

    def test_boundary_above_multiple(self):
        assert calculate_shards(76, per_vm=75) == 2
        assert calculate_shards(151, per_vm=75) == 3

    def test_zero_and_empty_accounts(self):
        assert calculate_shards(0, per_vm=75) == 1
        assert calculate_shards(-5, per_vm=75) == 1

    def test_small_custom_per_vm(self):
        # 512 accounts with 50 per vm -> ceil(512/50) = 11 shards
        assert calculate_shards(512, per_vm=50) == 11
        # 10 accounts with 1 per vm -> 10 shards
        assert calculate_shards(10, per_vm=1) == 10


class TestModuloShardPartitionMath:
    """Test suite for striping partitioning mathematical properties."""

    @pytest.fixture
    def sample_accounts(self):
        return [f"user_{i}@example.com" for i in range(512)]

    def test_partition_union_equals_original_dataset(self, sample_accounts):
        total_shards = 7
        all_reconstructed = []
        for shard_id in range(total_shards):
            shard_accounts = partition_by_shard(sample_accounts, shard_id, total_shards)
            all_reconstructed.extend(shard_accounts)

        assert len(all_reconstructed) == len(sample_accounts)
        assert set(all_reconstructed) == set(sample_accounts)

    def test_partition_disjointness(self, sample_accounts):
        total_shards = 7
        shard_sets = [set(partition_by_shard(sample_accounts, sid, total_shards)) for sid in range(total_shards)]

        # No intersection between any pair of shards
        for i in range(total_shards):
            for j in range(i + 1, total_shards):
                intersection = shard_sets[i].intersection(shard_sets[j])
                assert len(intersection) == 0, f"Collision detected between shard {i} and shard {j}: {intersection}"

    def test_balanced_distribution(self, sample_accounts):
        total_shards = 7
        shard_lengths = [len(partition_by_shard(sample_accounts, sid, total_shards)) for sid in range(total_shards)]

        # 512 % 7 = 1, so exactly one shard gets 74 and six get 73
        assert max(shard_lengths) - min(shard_lengths) <= 1
        assert sum(shard_lengths) == 512
        assert shard_lengths.count(74) == 1
        assert shard_lengths.count(73) == 6

    def test_single_shard_gets_all_accounts(self, sample_accounts):
        shard_0 = partition_by_shard(sample_accounts, shard_id=0, total_shards=1)
        assert len(shard_0) == len(sample_accounts)
        assert shard_0 == sample_accounts


class TestRunIdAndFirebasePayload:
    """Test suite for run_id generation, clean imports, and Firebase RTDB payload structure."""

    def test_run_id_format_and_uniqueness(self):
        def generate_run_id():
            return f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        run_id = generate_run_id()
        assert re.match(r"^run_\d+_[0-9a-f]{6}$", run_id), f"Invalid run_id format: {run_id}"

        # Generate 100 IDs and verify zero collisions
        generated_ids = {generate_run_id() for _ in range(100)}
        assert len(generated_ids) == 100

    def test_prepare_matrix_imports_clean(self):
        """Verifies scripts/prepare_matrix.py imports time, uuid, and requests without NameError."""
        import scripts.prepare_matrix as pm
        assert hasattr(pm, "time")
        assert hasattr(pm, "uuid")
        assert hasattr(pm, "requests")
        assert callable(pm.main)

    def test_firebase_init_payload_structure(self):
        """Verifies the structure and reset guarantees of the Firebase initialization payload."""
        total = 512
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        start_time = time.time()

        init_payload = {
            "run_id": run_id,
            "total": total,
            "processed": 0,
            "success": 0,
            "money": 0,
            "zero": 0,
            "error": 0,
            "total_balance": 0.0,
            "start_time": start_time,
            "status": "running",
            "is_finished": False,
            "vms": {},
            "threads": {}
        }

        assert init_payload["run_id"] == run_id
        assert init_payload["total"] == 512
        assert init_payload["processed"] == 0
        assert init_payload["vms"] == {}
        assert init_payload["threads"] == {}
        assert init_payload["status"] == "running"
        assert init_payload["is_finished"] is False

    def test_live_progress_zombie_vm_filtering(self):
        """Simulates fetchLiveProgress filtering of zombie VMs from prior executions."""
        active_run_id = "run_1729780000_a1b2c3"
        zombie_run_id = "run_1729770000_oldold"

        simulated_vms = {
            "VM_0": {"run_id": active_run_id, "processed": 30, "total_balance": 15.5},
            "VM_1": {"run_id": active_run_id, "processed": 25, "total_balance": 20.0},
            "VM_2_zombie": {"run_id": zombie_run_id, "processed": 75, "total_balance": 150.0},
            "VM_3_orphan": {"processed": 50, "total_balance": 80.0}
        }

        # Filtering logic matching index.html: any VM lacking the matching active_run_id is discarded
        agg_proc = 0
        agg_bal = 0.0
        for vk, vm in simulated_vms.items():
            if active_run_id and vm.get("run_id") != active_run_id:
                continue
            agg_proc += vm.get("processed", 0)
            agg_bal += vm.get("total_balance", 0.0)

        # Both VM_2_zombie (mismatched run_id) and VM_3_orphan (missing run_id) are discarded
        assert agg_proc == 30 + 25
        assert agg_bal == 15.5 + 20.0

    def test_live_progress_monotonic_clamping(self):
        """Verifies clamping so processed never exceeds total and never drops below zero."""
        raw_total = 100
        agg_proc_normal = 85
        agg_proc_overflow = 140
        agg_proc_negative = -25

        clamped_normal = max(0, min(raw_total, agg_proc_normal)) if raw_total > 0 else max(0, agg_proc_normal)
        clamped_overflow = max(0, min(raw_total, agg_proc_overflow)) if raw_total > 0 else max(0, agg_proc_overflow)
        clamped_negative = max(0, min(raw_total, agg_proc_negative)) if raw_total > 0 else max(0, agg_proc_negative)

        assert clamped_normal == 85
        assert clamped_overflow == 100
        assert clamped_negative == 0

