import sys
import types
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace


django = types.ModuleType("django")
django_db = types.ModuleType("django.db")
django_db.transaction = SimpleNamespace()
sys.modules.setdefault("django", django)
sys.modules.setdefault("django.db", django_db)

from plugin import Plugin


class SeriesRepairTests(unittest.TestCase):
    def setUp(self):
        self.plugin = Plugin.__new__(Plugin)
        self.titles = self.plugin._parse_series_repair_titles("The Young and the Restless")

    def program(self, title="The Young and the Restless", custom_properties=None):
        return SimpleNamespace(
            title=title,
            custom_properties=custom_properties or {},
            start_time=datetime(2026, 8, 10, tzinfo=timezone.utc),
        )

    def qualifies(self, program, titles=None, missing_only=True):
        return self.plugin._program_qualifies_for_series_repair(
            program,
            self.titles if titles is None else titles,
            missing_only,
        )

    def test_matching_title_with_no_episode_metadata_qualifies(self):
        self.assertTrue(self.qualifies(self.program()))

    def test_matching_title_with_onscreen_only_metadata_qualifies(self):
        program = self.program(custom_properties={"onscreen_episode": "13436"})

        self.assertTrue(self.qualifies(program))
        self.assertFalse(self.plugin._has_structured_episode_metadata(program.custom_properties))

    def test_matching_title_with_s_style_onscreen_imported_as_structured_metadata_is_skipped(self):
        program = self.program(custom_properties={"onscreen_episode": "S03E12", "season": 3, "episode": 12})

        self.assertFalse(self.qualifies(program))
        self.assertTrue(self.plugin._has_structured_episode_metadata(program.custom_properties))

    def test_matching_title_with_existing_structured_metadata_is_skipped(self):
        program = self.program(custom_properties={"season": 4, "episode": 12})

        self.assertFalse(self.qualifies(program))
        self.assertTrue(self.plugin._has_structured_episode_metadata(program.custom_properties))

    def test_existing_structured_metadata_qualifies_when_missing_only_is_off(self):
        program = self.program(custom_properties={"season": 4, "episode": 12})

        self.assertTrue(self.qualifies(program, missing_only=False))

    def test_nonmatching_title_is_skipped(self):
        program = self.program(title="The Jennifer Hudson Show")

        self.assertFalse(self.qualifies(program))

    def test_title_matching_is_exact_not_partial(self):
        program = self.program(title="The Young and the Restless - Extra")

        self.assertFalse(self.qualifies(program))

    def test_title_matching_is_case_insensitive_and_trimmed(self):
        titles = self.plugin._parse_series_repair_titles("  the young and the restless  ")
        program = self.program(title="THE YOUNG AND THE RESTLESS")

        self.assertTrue(self.qualifies(program, titles=titles))

    def test_status_title_display_preserves_configured_title_casing(self):
        display = self.plugin._series_repair_title_display(
            " The Young and the Restless \nthe young and the restless\nAnother Show"
        )

        self.assertEqual(display, ["The Young and the Restless", "Another Show"])

    def test_blank_title_filter_preserves_legacy_global_behavior(self):
        program = self.program(
            title="Any Program",
            custom_properties={"season": 2, "episode": 3},
        )

        self.assertTrue(self.qualifies(program, titles=set(), missing_only=True))

    def test_custom_properties_are_preserved_except_intended_repair_additions(self):
        program = self.program(custom_properties={
            "onscreen_episode": "13436",
            "rating": "TV-14",
            "categories": ["Drama"],
        })

        repaired = self.plugin._build_series_repair_custom_properties(
            program,
            ["Series"],
            True,
            True,
        )

        self.assertEqual(repaired["onscreen_episode"], "13436")
        self.assertEqual(repaired["rating"], "TV-14")
        self.assertEqual(repaired["categories"], ["Drama", "Series"])
        self.assertEqual(repaired["season"], 2026)
        self.assertEqual(repaired["episode"], 222)

    def test_nonqualifying_program_custom_properties_are_unchanged(self):
        original = {"onscreen_episode": "13436", "rating": "TV-14"}
        program = self.program(custom_properties=original)

        repaired = self.plugin._build_series_repair_custom_properties(
            program,
            ["Series"],
            True,
            False,
        )

        self.assertEqual(repaired, original)
        self.assertIsNot(repaired, original)


if __name__ == "__main__":
    unittest.main()
