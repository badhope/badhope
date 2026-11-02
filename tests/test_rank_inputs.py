import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import refresh
from kit.rank import calculate_rank, derive_profile


class RankInputTests(unittest.TestCase):
    def test_derive_profile_uses_available_contribution_counts(self):
        block = {"commits": 250, "prs": 50, "issues": 25, "reviews": 2,
                 "stars": 50, "followers": 10}
        self.assertEqual(derive_profile(block)["rank"], calculate_rank(block))

    def test_missing_contribution_counts_remain_compatible(self):
        block = {"stars": 12, "followers": 2}
        self.assertEqual(derive_profile(block)["rank"], calculate_rank(block))

    def test_contribution_counts_reject_non_numeric_snapshot_values(self):
        import accounts
        from kit.schema import validate_stats
        data = {"as_of": "2026-01-01", "accounts": {key: {} for key in accounts.ACCOUNT_ORDER}}
        data["accounts"][accounts.ACCOUNT_ORDER[0]]["commits"] = "unknown"
        self.assertTrue(any("commits" in item for item in validate_stats(data)))

    def test_github_contributions_are_mapped_and_errors_preserve_snapshot(self):
        payload = {"data": {"user": {"contributionsCollection": {
            "totalCommitContributions": 12, "totalPullRequestContributions": 3,
            "totalIssueContributions": 4, "totalPullRequestReviewContributions": 5}}}}
        block = {"commits": 2}
        with patch.object(refresh, "github_graphql", return_value=payload):
            refresh.refresh_github_contributions("example", block, "test-token")
        self.assertEqual({key: block[key] for key in ("commits", "prs", "issues", "reviews")},
                         {"commits": 12, "prs": 3, "issues": 4, "reviews": 5})
        previous = block.copy()
        with patch.object(refresh, "github_graphql", return_value={"errors": [{"message": "denied"}]}):
            with self.assertRaises(ValueError):
                refresh.refresh_github_contributions("example", block, "test-token")
        self.assertEqual(block, previous)

    def test_graphql_partial_count_never_overwrites_snapshot(self):
        block = {"commits": 2}
        payload = {"data": {"user": {"contributionsCollection": {"totalCommitContributions": 8}}}}
        with patch.object(refresh, "github_graphql", return_value=payload):
            with self.assertRaises(ValueError):
                refresh.refresh_github_contributions("example", block, "test-token")
        self.assertEqual(block, {"commits": 2})
