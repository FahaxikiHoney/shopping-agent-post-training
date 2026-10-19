import tempfile
import unittest
from pathlib import Path

from scripts.run_mock_query_batch import (
    completed_sample_ids,
    derived_quality_path,
    infer_scenario_type,
    latest_rows_by_sample,
    load_jsonl,
    pending_samples,
    requested_samples,
    select_samples,
    write_jsonl,
)


class MockQueryBatchRunnerTest(unittest.TestCase):
    def _records(self):
        records = []
        for site_code in ["UK-Site", "DE-Site", "FR-Site", "NL-Site"]:
            for index in range(3):
                records.append({
                    "sample_id": f"{site_code}-{index}",
                    "site_code": site_code,
                    "query": f"query {site_code} {index}",
                })
        return records

    def test_balanced_sampling_is_deterministic(self):
        first = select_samples(self._records(), 8, seed=17, balance_sites=True)
        second = select_samples(self._records(), 8, seed=17, balance_sites=True)
        self.assertEqual(first, second)
        counts = {}
        for row in first:
            counts[row["site_code"]] = counts.get(row["site_code"], 0) + 1
        self.assertEqual(counts, {
            "UK-Site": 2,
            "DE-Site": 2,
            "FR-Site": 2,
            "NL-Site": 2,
        })

    def test_sampling_deduplicates_sample_ids(self):
        records = self._records()
        records.append(dict(records[0]))
        selected = select_samples(records, 0, seed=17)
        self.assertEqual(len(selected), 12)

    def test_resume_only_skips_successful_rows(self):
        rows = [
            {
                "sample": {"sample_id": "ok"},
                "trajectory": {"status": "done"},
                "error": None,
            },
            {
                "sample": {"sample_id": "failed"},
                "trajectory": None,
                "error": {"message": "503"},
            },
        ]
        self.assertEqual(completed_sample_ids(rows), {"ok"})

    def test_rerun_can_force_completed_selected_samples(self):
        selected = self._records()[:2]
        completed = {selected[0]["sample_id"]}
        self.assertEqual(pending_samples(selected, completed), [selected[1]])
        self.assertEqual(pending_samples(selected, completed, rerun=True), selected)

    def test_auto_scenario_uses_bundle_labels(self):
        sample = {
            "query_difficulty_reasons": ["recommendation", "bundle"],
            "difficulty_reasons": ["multi_category_bundle"],
        }
        self.assertEqual(
            infer_scenario_type(sample, "auto"),
            "bundle_purchase",
        )
        self.assertEqual(
            infer_scenario_type({}, "auto"),
            "search_recommend",
        )

    def test_explicit_scenario_overrides_sample_labels(self):
        sample = {"query_difficulty_reasons": ["bundle"]}
        self.assertEqual(
            infer_scenario_type(sample, "search_recommend"),
            "search_recommend",
        )

    def test_requested_samples_preserve_order_and_reject_unknown_ids(self):
        records = self._records()
        selected = requested_samples(records, ["NL-Site-2", "UK-Site-0"])
        self.assertEqual(
            [row["sample_id"] for row in selected],
            ["NL-Site-2", "UK-Site-0"],
        )
        with self.assertRaisesRegex(ValueError, "unknown sample ids"):
            requested_samples(records, ["missing"])

    def test_latest_resume_row_replaces_previous_failure(self):
        rows = [
            {"sample": {"sample_id": "same"}, "trajectory": None, "error": "503"},
            {
                "sample": {"sample_id": "other"},
                "trajectory": {"status": "done"},
                "error": None,
            },
            {
                "sample": {"sample_id": "same"},
                "trajectory": {"status": "done"},
                "error": None,
            },
        ]
        latest = latest_rows_by_sample(rows)
        self.assertEqual([row["sample"]["sample_id"] for row in latest], ["same", "other"])
        self.assertEqual(latest[0]["trajectory"]["status"], "done")

    def test_jsonl_round_trip_and_quality_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.jsonl"
            write_jsonl(path, self._records()[:2])
            self.assertEqual(load_jsonl(path), self._records()[:2])
            self.assertEqual(
                derived_quality_path(path),
                Path(directory) / "batch_quality.json",
            )


if __name__ == "__main__":
    unittest.main()
