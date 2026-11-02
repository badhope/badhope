import unittest

from kit.extras import (
    gist_svg,
    habits_svg,
    isocalendar_svg,
    people_svg,
    projects_svg,
)


SAMPLE = {
    "gists": [
        {"name": "demo.py", "description": "A tiny demo", "language": "Python", "url": "https://gist.github.com/x/1"}
    ],
    "contribution_days": [{"date": "2026-01-01", "count": 3}, {"date": "2026-01-02", "count": 0}],
    "habits": {"languages": [{"name": "Python", "minutes": 120}], "editors": [{"name": "Vim", "minutes": 30}]},
    "people": [{"login": "alice", "avatar_url": "https://example.test/a.png"}],
    "projects": [{"name": "demo", "description": "Demo project", "url": "https://example.test/demo"}],
}


class ExtraCardTests(unittest.TestCase):
    def test_gist_card_lists_real_items(self):
        svg = gist_svg(SAMPLE["gists"], "md")
        self.assertIn("demo.py", svg)
        self.assertIn("A tiny demo", svg)

    def test_isocalendar_card_renders_days(self):
        svg = isocalendar_svg(SAMPLE["contribution_days"], "md")
        self.assertIn("2026-01-01", svg)

    def test_habits_card_renders_both_sections(self):
        svg = habits_svg(SAMPLE["habits"], "md")
        self.assertIn("Python", svg)
        self.assertIn("Vim", svg)

    def test_people_card_renders_login(self):
        svg = people_svg(SAMPLE["people"], "md")
        self.assertIn("alice", svg)

    def test_projects_card_renders_project(self):
        svg = projects_svg(SAMPLE["projects"], "md")
        self.assertIn("Demo project", svg)

    def test_empty_data_returns_none(self):
        for fn, key in ((gist_svg, "gists"), (isocalendar_svg, "contribution_days"),
                        (habits_svg, "habits"), (people_svg, "people"), (projects_svg, "projects")):
            self.assertIsNone(fn({}, "md"))
