
"""
Experiment 2: Simulated network attack scenario construction
Reference: Dong et al. (2024)

This version preserves the existing Experiment 2 calculations and adds
diagnostics for the S8 posterior mismatch.

Run from the project root:
    python -m experiments.paper_experiment_2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ccrp import run_ccrp
from src.ducag_graph import load_ducag_from_dict
from src.graph_simplification import simplify_ducag
from src.probability_calculations import (
    aggregate_hypothesis_path_probabilities,
    calculate_attack_path_probability,
    normalize_probabilities,
)

DATA_PATH = (
    Path(__file__).resolve().parent
    / "paper_data"
    / "experiment2_data.json"
)
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def print_s8_debug(ccrp_result: Any) -> None:
    """Print the available CCRP calculation details for S8."""

    print("\n" + "=" * 65)
    print("S8 DEBUG - CCRP POSTERIOR ANALYSIS")
    print("=" * 65)

    node_results = getattr(ccrp_result, "node_results", {})
    result = node_results.get("S8")

    if result is None:
        print("S8 is not present in node_results.")
        print("Available nodes:", list(node_results.keys()))
        return

    posterior = getattr(result, "posterior", None)
    n_value = getattr(result, "n_value", None)
    retained_sum = getattr(result, "retained_sum", None)

    print("Node:", "S8")
    print("Computed posterior:", posterior)
    print("Published posterior:", 0.3512)

    if posterior is not None:
        print("Absolute difference:", abs(posterior - 0.3512))

    print("N:", n_value)
    print("Retained chain sum:", retained_sum)

    print("\nDistinct hypotheses:")
    print(getattr(result, "distinct_hypotheses", "Not exposed"))

    print("\nDistinct evidence:")
    print(getattr(result, "distinct_evidence", "Not exposed"))

    retained_chains = getattr(result, "retained_chains", [])
    discarded_chains = getattr(result, "discarded_chains", [])

    print("\n--- Retained chains ---")

    if not retained_chains:
        print("No retained-chain details are available.")

    for index, chain in enumerate(retained_chains, start=1):
        print(f"\nChain {index}")
        print("  Direction:", getattr(chain, "direction", "Unknown"))
        print("  Path:", getattr(chain, "path", "Unknown"))
        print("  Type:", getattr(chain, "chain_type", "Unknown"))
        print("  Factors:", getattr(
            chain,
            "edge_factors",
            getattr(chain, "factors", "Not exposed"),
        ))
        print("  Value:", getattr(chain, "chain_value", "Unknown"))

    print("\n--- Discarded chains ---")

    if not discarded_chains:
        print("No discarded chains recorded.")

    for index, chain in enumerate(discarded_chains, start=1):
        print(f"\nChain {index}")
        print("  Direction:", getattr(chain, "direction", "Unknown"))
        print("  Path:", getattr(chain, "path", "Unknown"))
        print("  Type:", getattr(chain, "chain_type", "Unknown"))
        print("  Value:", getattr(chain, "chain_value", "Unknown"))

    print("\n" + "=" * 65)


def run_experiment_2() -> dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        config = json.load(file)

    ducag = load_ducag_from_dict(config["graph"])
    ducag.name = "Experiment_2_Simulated_Network"

    # ---------------------------------------------------------
    # Path 1: Primary incomplete-alarm scenario
    # ---------------------------------------------------------
    p1_cfg = config["path_1"]
    evidence = p1_cfg["observed_evidence"]
    target = p1_cfg["target"]

    print("\n" + "=" * 65)
    print("EXPERIMENT 2 - SIMULATED NETWORK")
    print("=" * 65)
    print("Observed evidence:", evidence)
    print("Missing alarms:", p1_cfg["missing_alarms"])
    print("Target:", target)

    # Step 1: Simplify the graph using the observed evidence.
    simplification_result = simplify_ducag(
        ducag,
        evidence=evidence,
        target=target,
    )
    simplified_graph = simplification_result.simplified

    # print("\nOriginal graph nodes:", ducag.number_of_nodes())
    # print("Simplified graph nodes:", simplified_graph.number_of_nodes())
    # print("Original graph edges:", ducag.number_of_edges())
    # print("Simplified graph edges:", simplified_graph.number_of_edges())

    # Step 2: Run CCRP for both hypotheses under nominal Path 1 evidence.
    ccrp_b1 = run_ccrp(
        simplified_graph,
        evidence=evidence,
        hypothesis="B1",
    )
    ccrp_bx1 = run_ccrp(
        simplified_graph,
        evidence=evidence,
        hypothesis="BX1",
    )

    # Table 8 published evaluation:
    # Table 8 Row 5 explicitly lists V4 with posterior 1.0 ("- | 1"), and all
    # Table 8 causal expressions terminate at V4. We evaluate CCRP under the
    # paper's Table 8 evidence set to reproduce Table 8 exactly.
    table_8_evidence = p1_cfg.get(
        "table_8_evidence",
        evidence + ["V4"] if "V4" not in evidence else evidence,
    )
    simplification_t8 = simplify_ducag(
        ducag,
        evidence=table_8_evidence,
        target=target,
    )
    ccrp_b1_t8 = run_ccrp(
        simplification_t8.simplified,
        evidence=table_8_evidence,
        hypothesis="B1",
    )

    # Debug the S8 calculation under Table 8 published conditions.
    print_s8_debug(ccrp_b1_t8)

    # ---------------------------------------------------------
    # Step 3: Calculate candidate attack-path probabilities.
    # ---------------------------------------------------------
    candidate_paths = p1_cfg["candidate_paths"]
    computed_candidates = []
    raw_path_probabilities = []

    for candidate in candidate_paths:
        nodes = candidate["nodes"]
        hypotheses = candidate["hypotheses"]
        hypothesis_probabilities = []

        if "B1" in hypotheses:
            sequence = [ccrp_b1.posteriors["B1"]]
            sequence.extend(ccrp_b1.posteriors[node] for node in nodes)

            hypothesis_probabilities.append(
                calculate_attack_path_probability(sequence)
            )

        if "BX1" in hypotheses:
            sequence = [ccrp_bx1.posteriors["BX1"]]
            sequence.extend(
                ccrp_bx1.posteriors[node] for node in nodes
            )

            hypothesis_probabilities.append(
                calculate_attack_path_probability(sequence)
            )

        if not hypothesis_probabilities:
            raise ValueError(
                f"No valid hypothesis probability for "
                f"candidate {candidate['id']}"
            )

        if len(hypothesis_probabilities) > 1:
            total_probability = aggregate_hypothesis_path_probabilities(
                hypothesis_probabilities
            )
        else:
            total_probability = hypothesis_probabilities[0]

        raw_path_probabilities.append(total_probability)

        computed_candidates.append(
            {
                "id": candidate["id"],
                "name": candidate["name"],
                "hypotheses": hypotheses,
                "is_true_path": candidate.get("is_true_path", False),
                "raw_probability": total_probability,
                "published_posterior": candidate["published_posterior"],
                "published_normalized": candidate["published_normalized"],
            }
        )

    # Step 4: Normalize the computed candidate probabilities.
    normalized_probabilities = normalize_probabilities(
        raw_path_probabilities
    )

    for index, candidate in enumerate(computed_candidates):
        candidate["computed_normalized"] = normalized_probabilities[index]

    ranked_candidates = sorted(
        computed_candidates,
        key=lambda item: item["computed_normalized"],
        reverse=True,
    )

    for rank, candidate in enumerate(ranked_candidates, start=1):
        candidate["computed_rank"] = rank

    # ---------------------------------------------------------
    # Step 5: Compare Table 8 node posteriors.
    # ---------------------------------------------------------
    table_8_comparison = {}
    published_posteriors = p1_cfg["published_table_8_posteriors_b1"]

    print("\n" + "=" * 65)
    print("TABLE 8 - NODE POSTERIOR COMPARISON")
    print("=" * 65)
    print(f"{'Node':<10}{'Computed':>14}{'Published':>14}{'Difference':>14}")

    for node, published_value in published_posteriors.items():
        computed_value = ccrp_b1_t8.posteriors.get(node)

        difference = (
            abs(computed_value - published_value)
            if computed_value is not None
            else None
        )

        table_8_comparison[node] = {
            "published": published_value,
            "computed": computed_value,
            "diff": difference,
        }

        computed_text = (
            f"{computed_value:.6f}"
            if computed_value is not None
            else "N/A"
        )
        difference_text = (
            f"{difference:.6f}"
            if difference is not None
            else "N/A"
        )

        print(
            f"{node:<10}"
            f"{computed_text:>14}"
            f"{published_value:>14.6f}"
            f"{difference_text:>14}"
        )

    # ---------------------------------------------------------
    # Step 6: Reproduce the published Table 9 normalization.
    # This is separate from the first-principles CCRP ranking.
    # ---------------------------------------------------------
    published_raw_probabilities = [
        candidate["published_posterior"]
        for candidate in candidate_paths
    ]

    table_9_normalized = normalize_probabilities(
        published_raw_probabilities
    )

    table_9_ranked_indices = sorted(
        range(len(table_9_normalized)),
        key=lambda index: table_9_normalized[index],
        reverse=True,
    )

    table_9_ranked_candidates = []

    for rank, index in enumerate(table_9_ranked_indices, start=1):
        candidate = candidate_paths[index]

        table_9_ranked_candidates.append(
            {
                "rank": rank,
                "path_id": candidate["id"],
                "name": candidate["name"],
                "is_true_path": candidate.get("is_true_path", False),
                "recomputed_normalized": table_9_normalized[index],
                "published_normalized": candidate["published_normalized"],
                "diff": abs(
                    table_9_normalized[index]
                    - candidate["published_normalized"]
                ),
            }
        )

    # ---------------------------------------------------------
    # Step 7: Save results.
    # ---------------------------------------------------------
    output_data = {
        "experiment": "Experiment 2 (Simulated Network)",
        "paper": config["metadata"]["paper"],
        "primary_scenario": {
            "name": "Path 1 (Incomplete alarms)",
            "observed_evidence": evidence,
            "missing_alarms": p1_cfg["missing_alarms"],
            "target": target,
            "table_9_published_reproduction": {
                "winner": table_9_ranked_candidates[0]["name"],
                "true_path_winner": table_9_ranked_candidates[0][
                    "is_true_path"
                ],
                "top_3": table_9_ranked_candidates[:3],
                "all_7_candidates": table_9_ranked_candidates,
            },
            "first_principles_ranking": {
                "winner": ranked_candidates[0]["name"],
                "winner_normalized": ranked_candidates[0][
                    "computed_normalized"
                ],
                "top_3": ranked_candidates[:3],
                "omitted_bx1_limitation": (
                    "The paper omitted BX1 node posteriors from Table 8. "
                    "Therefore, the BX1 first-principles ranking should "
                    "be interpreted with that limitation."
                ),
            },
            "table_8_node_posteriors_comparison": table_8_comparison,
            "table_8_evidence": table_8_evidence,
        },
        "path_2_summary": {
            "observed_evidence": config["path_2"]["observed_evidence"],
            "redundant_alarms": config["path_2"]["redundant_alarms"],
            "published_top_probability": config["path_2"][
                "top_candidate_published"
            ]["probability"],
        },
        "path_3_summary": {
            "observed_evidence": config["path_3"]["observed_evidence"],
            "redundant_alarms": config["path_3"]["redundant_alarms"],
            "missing_alarms": config["path_3"]["missing_alarms"],
            "published_top_probability": config["path_3"][
                "top_candidate_published"
            ]["probability"],
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = RESULTS_DIR / "experiment_2_results.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(output_data, file, indent=2)

    print("\nResults saved to:", output_file)

    return output_data


if __name__ == "__main__":
    results = run_experiment_2()
    primary = results["primary_scenario"]

    print("\n" + "=" * 65)
    print("TABLE 9 - PUBLISHED NORMALIZATION")
    print("=" * 65)

    table_9 = primary["table_9_published_reproduction"]
    print("Winner:", table_9["winner"])
    print("True path winner:", table_9["true_path_winner"])

    for item in table_9["top_3"]:
        print(
            f"Rank {item['rank']}: {item['name']} | "
            f"Computed={item['recomputed_normalized']:.4f} | "
            f"Published={item['published_normalized']:.4f}"
        )

    print("\n" + "=" * 65)
    print("FIRST-PRINCIPLES CCRP RANKING")
    print("=" * 65)

    first_principles = primary["first_principles_ranking"]
    print("Winner:", first_principles["winner"])

    for item in first_principles["top_3"]:
        print(
            f"Rank {item['computed_rank']}: {item['name']} | "
            f"Computed={item['computed_normalized']:.4f} | "
            f"Published={item['published_normalized']:.4f}"
        )
