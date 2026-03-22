from demos.demo_final import render_markdown_report


REQUIRED_SECTION_HEADINGS = [
    "## Key Actors and Nodes",
    "## Critical Mechanism Chains",
    "## Competing Explanations and Divergent Predictions",
    "## Likely Surprises",
    "## Main Uncertainties / Hidden Assumptions",
]


def test_final_report_contains_all_required_section_headings_and_non_empty_content(phase1_scenario) -> None:
    report = phase1_scenario.final_report
    markdown = render_markdown_report(report)

    for heading in REQUIRED_SECTION_HEADINGS:
        assert heading in markdown

    assert report.key_actors_and_nodes
    assert report.critical_mechanism_chains
    assert report.competing_explanations_and_divergent_predictions
    assert report.likely_surprises
    assert report.main_uncertainties_and_hidden_assumptions
    assert len(markdown) < 12_000
