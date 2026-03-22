import unittest

from perspective_extractor.models import (
    ActorCard,
    CompeteResult,
    CompetingMechanism,
    ConstraintCard,
    DecomposeResult,
    FalsificationEntry,
    FinalReport,
    NodeCard,
    ProblemFrame,
    StressResult,
    SurpriseEntry,
    TraceResult,
    TraceStep,
)


class Phase1ModelTests(unittest.TestCase):
    def test_phase1_primary_models_accept_proposal_aligned_payloads(self) -> None:
        decompose_result = DecomposeResult(
            problem_frame=ProblemFrame(
                core_question="How could a port disruption affect regional fuel prices?",
                decision_or_analysis_target="Assess the main causal channels and likely operational pressure points.",
                scope_notes=["Focus on the next 30 days", "Emphasize logistics and institutional bottlenecks"],
            ),
            actor_cards=[
                ActorCard(
                    name="Port authority",
                    type="institution",
                    role="Controls throughput decisions and recovery sequencing",
                    goal_guess="Restore operations without triggering safety failures",
                    why_relevant="Its choices determine whether congestion clears quickly or compounds.",
                )
            ],
            node_cards=[
                NodeCard(
                    name="Main import terminal",
                    type="facility",
                    function="Receives and transfers refined fuel shipments into inland distribution networks",
                    why_relevant="A disruption here can slow multiple downstream supply routes at once.",
                )
            ],
            constraint_cards=[
                ConstraintCard(
                    constraint="Hazardous cargo inspections limit restart speed",
                    applies_to=["Port authority", "Main import terminal"],
                    why_it_matters="Even politically urgent recovery plans still face mandatory safety checks.",
                )
            ],
        )

        trace_result = TraceResult(
            trace_target="Main import terminal shutdown",
            consequence_chain=[
                TraceStep(
                    order=1,
                    event="Inbound unloading is delayed",
                    mechanism="Cargo queues build because berth access collapses",
                    affected_entities=["Fuel importers", "Port authority"],
                ),
                TraceStep(
                    order=2,
                    event="Local wholesalers bid up replacement supply",
                    mechanism="Importers shift demand to alternate terminals with limited spare capacity",
                    affected_entities=["Wholesalers", "Alternate terminals"],
                ),
                TraceStep(
                    order=3,
                    event="Retail fuel prices rise unevenly across the region",
                    mechanism="Distribution costs and shortage expectations pass through to end markets",
                    affected_entities=["Retail stations", "Drivers"],
                ),
            ],
        )

        compete_result = CompeteResult(
            competing_mechanisms=[
                CompetingMechanism(
                    label="A",
                    core_mechanism="Physical throughput loss is the dominant driver",
                    what_it_explains="Immediate spot price spikes after the shutdown",
                    prediction="Prices fall rapidly once berth access resumes",
                    observable_signal="Terminal utilization normalizes before retail margins do",
                ),
                CompetingMechanism(
                    label="B",
                    core_mechanism="Expectation-driven hoarding is the dominant driver",
                    what_it_explains="Persistent regional price divergence after the initial outage",
                    prediction="Prices stay elevated even after berth access resumes",
                    observable_signal="Inventory drawdowns continue despite recovering terminal throughput",
                ),
            ],
            divergence_note="The mechanisms diverge on whether restored physical capacity is enough to normalize prices.",
        )

        stress_result = StressResult(
            falsification_ledger=[
                FalsificationEntry(
                    claim_under_stress="Restoring the terminal will quickly normalize retail prices",
                    hidden_assumption="Alternative terminals can absorb backlog without creating new inland bottlenecks",
                    how_it_could_fail="Backlogged truck and storage capacity remain constrained after berth access returns",
                    what_evidence_would_break_it="Persistently high depot wait times after terminal throughput recovers",
                )
            ],
            surprise_ledger=[
                SurpriseEntry(
                    surprise="A smaller inland pipeline node becomes the main bottleneck after the port reopens",
                    why_shallow_analysis_misses_it="Attention stays fixed on the headline port outage instead of substitute pathways",
                    what_actor_or_node_it_depends_on=["Inland pipeline operator", "Main import terminal"],
                )
            ],
        )

        final_report = FinalReport(
            key_actors_and_nodes=["Port authority vs. import terminal throughput are the key operational levers."],
            critical_mechanism_chains=["Shutdown -> unloading delay -> replacement bidding -> uneven retail pass-through."],
            competing_explanations_and_divergent_predictions=[
                "If throughput loss dominates, prices should normalize quickly after berth access resumes; if hoarding dominates, elevation should persist."
            ],
            likely_surprises=["An inland pipeline chokepoint may matter more than the reopened port."],
            main_uncertainties_and_hidden_assumptions=["The analysis assumes alternate terminals and trucking can absorb backlog."],
            executive_summary="Regional price effects depend on whether physical throughput or expectations remain the binding constraint after reopening.",
        )

        self.assertEqual(decompose_result.problem_frame.core_question, "How could a port disruption affect regional fuel prices?")
        self.assertEqual(len(trace_result.consequence_chain), 3)
        self.assertEqual(len(compete_result.competing_mechanisms), 2)
        self.assertEqual(len(stress_result.falsification_ledger), 1)
        self.assertEqual(len(final_report.likely_surprises), 1)

    def test_phase1_models_enforce_core_validation_rules(self) -> None:
        with self.assertRaisesRegex(ValueError, "type must be one of"):
            ActorCard(
                name="Trader",
                type="bank",
                role="Intermediates flows",
                goal_guess="Capture spreads",
                why_relevant="Moves supply between markets",
            )

        with self.assertRaisesRegex(ValueError, "orders must start at 1 and increase by 1"):
            TraceResult(
                trace_target="Target",
                consequence_chain=[
                    TraceStep(
                        order=1,
                        event="step one",
                        mechanism="first mechanism",
                        affected_entities=["Actor A"],
                    ),
                    TraceStep(
                        order=3,
                        event="step two",
                        mechanism="second mechanism",
                        affected_entities=["Actor B"],
                    ),
                ],
            )

        with self.assertRaisesRegex(ValueError, "exactly two entries"):
            CompeteResult(
                competing_mechanisms=[
                    CompetingMechanism(
                        label="A",
                        core_mechanism="Only one mechanism",
                        what_it_explains="Something",
                        prediction="One outcome",
                        observable_signal="One signal",
                    )
                ],
                divergence_note="Not enough competition",
            )

        with self.assertRaisesRegex(ValueError, "must not be identical"):
            CompeteResult(
                competing_mechanisms=[
                    CompetingMechanism(
                        label="A",
                        core_mechanism="Mechanism A",
                        what_it_explains="Something",
                        prediction="Same prediction",
                        observable_signal="Signal A",
                    ),
                    CompetingMechanism(
                        label="B",
                        core_mechanism="Mechanism B",
                        what_it_explains="Something else",
                        prediction="Same prediction",
                        observable_signal="Signal B",
                    ),
                ],
                divergence_note="Predictions collapse",
            )

        with self.assertRaisesRegex(ValueError, "likely_surprises must contain at least one item"):
            FinalReport(
                key_actors_and_nodes=["Actor"],
                critical_mechanism_chains=["Chain"],
                competing_explanations_and_divergent_predictions=["Competition"],
                likely_surprises=[],
                main_uncertainties_and_hidden_assumptions=["Assumption"],
            )


if __name__ == "__main__":
    unittest.main()
