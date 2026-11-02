import unittest

from kit.rank import ACHIEVEMENT_TABLE, achievements


class AchievementCoverageTests(unittest.TestCase):
    def test_extended_fields_are_declared(self):
        fields = {field for _, field, _, _ in ACHIEVEMENT_TABLE}
        self.assertTrue({"repos", "followers", "stars", "languages", "years",
                         "gists", "organizations", "starred", "following"} <= fields)

    def test_missing_fields_do_not_produce_entries(self):
        items = achievements({"repos": 3})
        self.assertEqual([item["name"] for item in items], ["Developer"])

    def test_extended_fields_produce_entries(self):
        items = achievements({"gists": 5, "organizations": 2, "starred": 30, "following": 12})
        names = {item["name"] for item in items}
        self.assertTrue({"Gister", "Organizer", "Curator", "Follower"} <= names)

    def test_zero_is_a_valid_real_value(self):
        items = achievements({"gists": 0})
        self.assertEqual(items[0]["value"], 0)
        self.assertEqual(items[0]["rank"], "C")
