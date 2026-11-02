import unittest

import accounts as A
from kit.cards import langs_svg, skills_svg, works_svg


class CardTitleTests(unittest.TestCase):
    def test_langs_card_uses_configured_title(self):
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        acct["card_titles"] = {"langs": {"md": "Stack & Tools"}}
        svg = langs_svg("gitcode_badhope", "md", {"accounts": {"gitcode_badhope": {"repos": [
            {"language": "Python"}]}}}, theme=A.THEME,
            title=acct["card_titles"]["langs"]["md"])
        self.assertIn(">Stack &amp; Tools<", svg)

    def test_skills_card_keeps_default_note_when_unset(self):
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        svg = skills_svg(acct, "md", theme=A.THEME)
        self.assertIn(A.LABELS["md"]["skills_note"], svg)

    def test_works_card_accessibility_label_uses_configured_title(self):
        acct = A.ACCOUNTS["gitcode_badhope"]
        svg = works_svg(acct, "gitcode_badhope", "md", theme=A.THEME, title="Builds & Notes")
        self.assertIn('aria-label="Builds &amp; Notes', svg)

    def test_wakatime_title_override(self):
        from kit.wakatime import wakatime_svg
        svg = wakatime_svg({"data": {"range": "last_7_days",
                                     "categories": [{"text": "1 hr"}],
                                     "languages": [{"name": "Python", "text": "1 hr", "percent": 100}]}},
                           theme=A.THEME, title="Coding Time")
        self.assertIn("Coding Time", svg)
        self.assertNotIn("WakaTime", svg)

    def test_achievements_title_override(self):
        from kit.achievements import achievements_svg
        stats = {"accounts": {"gh_badhope": {"repos": 3, "stars": 1, "followers": 2}}}
        svg = achievements_svg(A.ACCOUNTS["gh_badhope"], "gh_badhope", stats, "md",
                               discovered={"accounts": {"gh_badhope": {"repos": []}}},
                               theme=A.THEME, title="Milestones")
        self.assertIn("Milestones", svg)
