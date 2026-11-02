import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import refresh_extras


class GraphQLExtraTests(unittest.TestCase):
    def test_calendar_uses_contribution_counts_not_event_counts(self):
        payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
            "weeks": [{"contributionDays": [{"date": "2026-01-01", "contributionCount": 4}]}]}}}}}
        with patch.object(refresh_extras, "_extra_graphql", return_value=payload):
            self.assertEqual(refresh_extras.fetch_calendar("alice"), [{"date": "2026-01-01", "count": 4}])

    def test_projects_are_project_v2_not_repositories(self):
        payload = {"data": {"user": {"projectsV2": {"nodes": [
            {"title": "Board", "url": "https://github.com/users/alice/projects/1", "shortDescription": "Work", "public": True}],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}
        with patch.object(refresh_extras, "_extra_graphql", return_value=payload):
            result = refresh_extras.fetch_projects("alice")
        self.assertEqual(result[0]["name"], "Board")
        self.assertIn("/projects/1", result[0]["url"])

    def test_projects_without_explicit_public_flag_are_not_exported(self):
        payload = {"data": {"user": {"projectsV2": {"nodes": [
            {"title": "Private", "url": "https://github.com/users/alice/projects/2"}],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}
        with patch.object(refresh_extras, "_extra_graphql", return_value=payload):
            self.assertEqual(refresh_extras.fetch_projects("alice"), [])

    def test_incomplete_project_pagination_is_rejected(self):
        payload = {"data": {"user": {"projectsV2": {"nodes": [], "pageInfo": {}}}}}
        with patch.object(refresh_extras, "_extra_graphql", return_value=payload):
            with self.assertRaises(ValueError):
                refresh_extras.fetch_projects("alice")

    def test_graphql_errors_are_not_empty_success(self):
        with patch.object(refresh_extras, "_extra_graphql", return_value={"errors": [{"message": "denied"}]}):
            with self.assertRaises(ValueError):
                refresh_extras.fetch_calendar("alice")
