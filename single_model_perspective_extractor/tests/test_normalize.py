import unittest

from perspective_extractor.normalize import normalize_question


class NormalizeQuestionTests(unittest.TestCase):
    def test_normalizes_causal_question(self) -> None:
        card = normalize_question("How does remote work affect employee productivity?")

        self.assertEqual(card.cleaned_question, "How does remote work affect employee productivity?")
        self.assertEqual(card.actor_entity, "remote work")
        self.assertEqual(card.outcome_variable, "employee productivity")
        self.assertEqual(card.domain_hint, "business")
        self.assertIn("remote work", card.keywords)
        self.assertIn("employee productivity", card.keywords)
        self.assertTrue(any("Time frame" in item for item in card.missing_pieces))

    def test_rewrites_statement_like_question(self) -> None:
        card = normalize_question("I want to know whether social media use increases teen anxiety")

        self.assertEqual(
            card.cleaned_question,
            "To what extent does social media use increase teen anxiety?",
        )
        self.assertEqual(card.actor_entity, "social media use")
        self.assertEqual(card.outcome_variable, "teen anxiety")
        self.assertEqual(card.domain_hint, "public health")
        self.assertTrue(any("may influence" in item for item in card.assumptions))
        self.assertFalse(any("Target population" in item for item in card.missing_pieces))


if __name__ == "__main__":
    unittest.main()
