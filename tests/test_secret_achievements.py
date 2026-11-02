import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import accounts as A
from kit.achievements import achievements_svg


class SecretAchievementTests(unittest.TestCase):
    def test_secret_items_merge_into_achievement_panel(self):
        stats = {"accounts": {"gh_badhope": {"repos": 3, "stars": 1, "followers": 2}}}
        extras = {"secrets": [{"name": "Verified", "value": 1, "rank": "$", "progress": 1}]}
        svg = achievements_svg(A.ACCOUNTS["gh_badhope"], "gh_badhope", stats, "md",
                              discovered={"accounts": {"gh_badhope": {"repos": []}}},
                              theme=A.THEME, extras=extras)
        self.assertIn("Verified", svg)

    def test_secret_without_snapshot_is_not_rendered(self):
        stats = {"accounts": {"gh_badhope": {"repos": 3, "stars": 1, "followers": 2}}}
        svg = achievements_svg(A.ACCOUNTS["gh_badhope"], "gh_badhope", stats, "md",
                              discovered={"accounts": {"gh_badhope": {"repos": []}}},
                              theme=A.THEME)
        self.assertNotIn("Verified", svg)

    def test_secret_fetch_failure_returns_empty_and_keeps_other_sections(self):
        import refresh_extras
        with patch.object(refresh_extras, "_has_gpg", side_effect=OSError("offline")):
            self.assertEqual(refresh_extras.fetch_secrets("example"), [])

    def test_secret_fetch_maps_detected_flags(self):
        import refresh_extras
        with patch.object(refresh_extras, "_has_gpg", return_value=True), \
             patch.object(refresh_extras, "_has_starred_topics", return_value=False):
            items = refresh_extras.fetch_secrets("example")
        self.assertEqual([i["name"] for i in items], ["Verified"])
        self.assertEqual(items[0]["rank"], "$")
