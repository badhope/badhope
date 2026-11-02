import unittest

import accounts as A
from kit.templates import resolve, section_order


class TemplateTests(unittest.TestCase):
    def test_default_template_preserves_original_section_order(self):
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        self.assertEqual(section_order(acct), [
            "about", "build", "skills", "works", "numbers", "achievements",
            "pinned", "writing", "elsewhere",
        ])

    def test_named_template_changes_order_without_dropping_sections(self):
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        acct["template"] = "compact"
        order = section_order(acct)
        self.assertEqual(set(order), set(section_order(dict(A.ACCOUNTS["gitcode_badhope"]))))

    def test_unknown_template_falls_back(self):
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        acct["template"] = "does-not-exist"
        self.assertEqual(resolve(acct)["name"], "classic")

    def test_compact_template_moves_works_before_skills(self):
        from kit.readme import render_readme
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        acct["template"] = "compact"
        text = render_readme(acct, "gitcode_badhope", "md",
                             {"as_of": "", "accounts": {}}, discovered={"accounts": {}})
        self.assertLess(text.index("## Selected work"), text.index("## Toolbox"))

    def test_minimal_template_hides_optional_sections(self):
        from kit.readme import render_readme
        acct = dict(A.ACCOUNTS["gitcode_badhope"])
        acct["template"] = "minimal"
        text = render_readme(acct, "gitcode_badhope", "md",
                             {"as_of": "", "accounts": {}}, discovered={"accounts": {}})
        self.assertNotIn("## Toolbox", text)
        self.assertNotIn("## Numbers", text)
        self.assertIn("## Elsewhere", text)

    def test_unrecognized_sections_keep_content_together(self):
        from kit.templates import apply
        lines = ["intro", "## Work", "work body", "## Extra", "extra body",
                 "## Skills", "skills body", "footer"]
        result = apply(lines, {"template": "compact"}, {"works": "Work", "skills": "Skills"})
        self.assertIn("## Extra", result)
        self.assertEqual(result[result.index("## Extra") + 1], "extra body")
        self.assertEqual(result.count("extra body"), 1)

    def test_classic_template_keeps_render_unchanged(self):
        from kit.readme import render_readme
        base = dict(A.ACCOUNTS["gitcode_badhope"])
        classic = dict(base, template="classic")
        args = ({"as_of": "", "accounts": {}},)
        kwargs = {"discovered": {"accounts": {}}}
        self.assertEqual(render_readme(base, "gitcode_badhope", "md", *args, **kwargs),
                         render_readme(classic, "gitcode_badhope", "md", *args, **kwargs))
