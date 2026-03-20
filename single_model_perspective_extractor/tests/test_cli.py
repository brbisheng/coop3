import io
import json
import unittest
from contextlib import redirect_stdout

from perspective_extractor import cli


class NormalizeCliTests(unittest.TestCase):
    def test_normalize_defaults_to_json_output(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(["normalize", "How does remote work affect employee productivity?"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["cleaned_question"], "How does remote work affect employee productivity?")
        self.assertEqual(payload["actor_entity"], "remote work")
        self.assertEqual(payload["outcome_variable"], "employee productivity")
        self.assertIn("keywords", payload)

    def test_normalize_can_render_markdown(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "normalize",
                    "I want to know whether social media use increases teen anxiety",
                    "--format",
                    "markdown",
                ]
            )

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("# Normalized Question", output)
        self.assertIn("**cleaned_question:** To what extent does social media use increase teen anxiety?", output)
        self.assertIn("## Keywords", output)


if __name__ == "__main__":
    unittest.main()


class AxesCliTests(unittest.TestCase):
    def test_axes_defaults_to_markdown_with_question_support_cards_and_axes(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(["axes", "How does remote work affect employee productivity?"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("# Perspective Axes", output)
        self.assertIn("## QuestionCard", output)
        self.assertIn("## Knowledge Cards", output)
        self.assertIn("## Variable Cards", output)
        self.assertIn("## Controversy Cards", output)
        self.assertIn("## Axis Cards", output)
        self.assertIn("**type:**", output)
        self.assertIn("**focus:**", output)
        self.assertIn("**distinctness:**", output)

    def test_axes_json_can_skip_supporting_cards(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "axes",
                    "How does remote work affect employee productivity?",
                    "--format",
                    "json",
                    "--skip-knowledge",
                    "--skip-variables",
                    "--skip-controversies",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["knowledge_cards"], [])
        self.assertEqual(payload["variable_cards"], [])
        self.assertEqual(payload["controversy_cards"], [])
        self.assertGreaterEqual(len(payload["axis_cards"]), 8)
        self.assertIn("axis_type", payload["axis_cards"][0])
        self.assertIn("focus", payload["axis_cards"][0])
        self.assertIn("how_is_it_distinct", payload["axis_cards"][0])



class ReviewCliTests(unittest.TestCase):
    def test_review_defaults_to_json_with_raw_notes_decisions_and_summary(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(["review", "How does remote work affect employee productivity?"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("raw_notes", payload)
        self.assertIn("review_decisions", payload)
        self.assertIn("summary", payload)
        self.assertGreaterEqual(len(payload["raw_notes"]), 8)
        self.assertEqual(len(payload["review_decisions"]), len(payload["raw_notes"]))
        self.assertEqual(payload["summary"]["total"], len(payload["review_decisions"]))
        self.assertTrue({"kept", "merged", "rewritten", "dropped"} <= set(payload["summary"]))

    def test_review_markdown_includes_raw_notes_decisions_and_summary_sections(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(
                [
                    "review",
                    "How does remote work affect employee productivity?",
                    "--format",
                    "markdown",
                ]
            )

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("# Raw Notes", output)
        self.assertIn("# Review Decisions", output)
        self.assertIn("# Review Summary", output)
        self.assertIn("**kept:**", output)
        self.assertIn("**merged:**", output)
        self.assertIn("**rewritten:**", output)
        self.assertIn("**dropped:**", output)


class ExpandCliTests(unittest.TestCase):
    def test_expand_defaults_to_raw_json_perspective_note_list(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cli.main(["expand", "How does remote work affect employee productivity?"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIsInstance(payload, list)
        self.assertGreaterEqual(len(payload), 8)
        self.assertIn("note_id", payload[0])
        self.assertIn("axis_id", payload[0])
        self.assertEqual(payload[0]["note_id"], payload[0]["axis_id"].replace("axis_", "note_", 1))

