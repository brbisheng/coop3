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
