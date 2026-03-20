import unittest

from perspective_extractor.knowledge import (
    generate_controversy_cards,
    generate_knowledge_cards,
    generate_variable_cards,
)
from perspective_extractor.normalize import normalize_question


class KnowledgeGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = normalize_question("How does remote work affect employee productivity?")

    def test_generate_knowledge_cards_returns_background_and_mechanism_frames(self) -> None:
        cards = generate_knowledge_cards(self.card)

        self.assertGreaterEqual(len(cards), 4)
        self.assertEqual(cards[0].source_type, "single-model")
        self.assertTrue(any(card.title == "Mechanism map" for card in cards))
        self.assertTrue(any("remote work" in card.content for card in cards))
        self.assertTrue(all(card.verification_question for card in cards))

    def test_generate_variable_cards_covers_required_roles(self) -> None:
        cards = generate_variable_cards(self.card)

        roles = {card.variable_role for card in cards}
        self.assertEqual(roles, {"actor", "state", "decision", "constraint", "outcome"})
        self.assertEqual(cards[0].name, "remote work")
        self.assertEqual(cards[-1].name, "employee productivity")
        self.assertTrue(all(card.verification_question for card in cards))

    def test_generate_controversy_cards_focus_on_competing_explanations(self) -> None:
        cards = generate_controversy_cards(self.card)

        self.assertGreaterEqual(len(cards), 3)
        self.assertTrue(all(len(card.sides) >= 2 for card in cards))
        self.assertTrue(any("spurious" in card.question for card in cards))
        self.assertTrue(any(card.competing_perspectives for card in cards))


if __name__ == "__main__":
    unittest.main()
