"""
Experiment 2: Simulated network attack scenario construction (Dong et al., 2024).

PRIMARY incomplete-alarm scenario required by PROJECT_SPEC:
  - Path 1: Simulated true path: B1 -> V1 -> S2 -> V3 -> S4 -> V6 -> S6 -> V11 -> S8 -> V13 -> S9
  - Observed alarms: {V1, V3, S4, V6, V11, V13, S9}
  - Missing alarms: S2, S6, S8
  - Target: S9
  - Hypotheses: B1, BX1, B2

Also covers Path 2 (redundant alarms) and Path 3 (redundant & missing alarms).
Outputs intermediate values, Table 8 node posteriors, and Table 9 scenario rankings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ccrp import run_ccrp
from src.ducag_graph import load_ducag_from_dict
from src.graph_simplification import simplify_ducag
from src.probability_calculations import (
    aggregate_hypothesis_path_probabilities,
    calculate_attack_path_probability,
    normalize_probabilities,
)

DATA_PATH = Path(__file__).resolve().parent / "paper_data" / "experiment2_data.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def run_experiment_2() -> dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    ducag = load_ducag_from_dict(config["graph"])
    ducag.name = "Experiment_2_Simulated_Network"

    # =========================================================================
    # Path 1 (Primary incomplete-alarm case)
    # =========================================================================
    p1_cfg = config["path_1"]
    evidence = p1_cfg["observed_evidence"]
    target = p1_cfg["target"]

    # Step 1: Simplification under evidence
    simp_res = simplify_ducag(ducag, evidence=evidence, target=target)
    simplified_g = simp_res.simplified

    # Step 2: CCRP node posterior calculation
    # Run under B1 (primary tabulated case in Table 8) and BX1
    ccrp_b1 = run_ccrp(simplified_g, evidence=evidence, hypothesis="B1")
    ccrp_bx1 = run_ccrp(simplified_g, evidence=evidence, hypothesis="BX1")

    # Step 3: Candidate path probability calculation (Eq. 6 & Eq. 7)
    candidate_paths = p1_cfg["candidate_paths"]
    computed_candidates = []
    raw_path_probs = []

    for c in candidate_paths:
        nodes = c["nodes"]
        hyps = c["hypotheses"]

        # If path is evaluated under both B1 and BX1, aggregate per Eq. (7)
        hyp_probs = []
        if "B1" in hyps:
            # Full sequence from B1 through nodes
            p_b1_seq = [ccrp_b1.posteriors["B1"]] + [ccrp_b1.posteriors[n] for n in nodes]
            hyp_probs.append(calculate_attack_path_probability(p_b1_seq))
        if "BX1" in hyps:
            p_bx1_seq = [ccrp_bx1.posteriors["BX1"]] + [ccrp_bx1.posteriors[n] for n in nodes]
            hyp_probs.append(calculate_attack_path_probability(p_bx1_seq))

        # Equation 7 aggregation
        if len(hyp_probs) > 1:
            total_prob = aggregate_hypothesis_path_probabilities(hyp_probs)
        else:
            total_prob = hyp_probs[0]

        raw_path_probs.append(total_prob)
        computed_candidates.append({
            "id": c["id"],
            "name": c["name"],
            "hypotheses": hyps,
            "is_true_path": c.get("is_true_path", False),
            "raw_probability": total_prob,
            "published_posterior": c["published_posterior"],
            "published_normalized": c["published_normalized"],
        })

    # Step 4: Normalization (Step 4 of attack scenario reconstruction)
    normalized_probs = normalize_probabilities(raw_path_probs)
    for idx, c in enumerate(computed_candidates):
        c["computed_normalized"] = normalized_probs[idx]

    # Rank candidate paths from first-principles inference
    ranked = sorted(computed_candidates, key=lambda x: x["computed_normalized"], reverse=True)
    for rank_idx, item in enumerate(ranked, 1):
        item["computed_rank"] = rank_idx

    # Compare node posteriors under B1 with Table 8 published values
    table_8_comparison = {}
    pub_t8 = p1_cfg["published_table_8_posteriors_b1"]
    for node, pub_val in pub_t8.items():
        comp_val = ccrp_b1.posteriors.get(node)
        table_8_comparison[node] = {
            "published": pub_val,
            "computed": comp_val,
            "diff": abs(comp_val - pub_val) if comp_val is not None else None,
        }

    # Verify Table 9 published posteriors normalization
    t9_published_raw = [c["published_posterior"] for c in candidate_paths]
    t9_normalized = normalize_probabilities(t9_published_raw)
    t9_ranked_indices = sorted(range(len(t9_normalized)), key=lambda i: t9_normalized[i], reverse=True)
    t9_ranked_candidates = [
        {
            "rank": rank + 1,
            "path_id": candidate_paths[i]["id"],
            "name": candidate_paths[i]["name"],
            "is_true_path": candidate_paths[i].get("is_true_path", False),
            "recomputed_normalized": t9_normalized[i],
            "published_normalized": candidate_paths[i]["published_normalized"],
            "diff": abs(t9_normalized[i] - candidate_paths[i]["published_normalized"]),
        }
        for rank, i in enumerate(t9_ranked_indices)
    ]

    out_data = {
        "experiment": "Experiment 2 (Simulated Network)",
        "paper": config["metadata"]["paper"],
        "primary_scenario": {
            "name": "Path 1 (Incomplete alarms)",
            "observed_evidence": evidence,
            "missing_alarms": p1_cfg["missing_alarms"],
            "target": target,
            "table_9_published_reproduction": {
                "winner": t9_ranked_candidates[0]["name"],
                "true_path_winner": t9_ranked_candidates[0]["is_true_path"],
                "top_3": t9_ranked_candidates[:3],
                "all_7_candidates": t9_ranked_candidates,
            },
            "first_principles_ranking": {
                "winner": ranked[0]["name"],
                "winner_normalized": ranked[0]["computed_normalized"],
                "top_3": ranked[:3],
                "omitted_bx1_limitation": (
                    "The paper explicitly omitted BX1 node posteriors 'due to space limitations' "
                    "(Section 4.2). Table 8 only reports posteriors under B1."
                ),
            },
            "table_8_node_posteriors_comparison": table_8_comparison,
        },
        "path_2_summary": {
            "observed_evidence": config["path_2"]["observed_evidence"],
            "redundant_alarms": config["path_2"]["redundant_alarms"],
            "published_top_probability": config["path_2"]["top_candidate_published"]["probability"],
        },
        "path_3_summary": {
            "observed_evidence": config["path_3"]["observed_evidence"],
            "redundant_alarms": config["path_3"]["redundant_alarms"],
            "missing_alarms": config["path_3"]["missing_alarms"],
            "published_top_probability": config["path_3"]["top_candidate_published"]["probability"],
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "experiment_2_results.json"
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(out_data, fh, indent=2)

    return out_data


if __name__ == "__main__":
    res = run_experiment_2()
    print("=== Experiment 2 Results ===")
    p1 = res["primary_scenario"]
    print("--- Table 9 Published Reproduction (Exact Normalization) ---")
    t9_rank = p1["table_9_published_reproduction"]
    print(f"Winner: {t9_rank['winner']}")
    print(f"True path winner: {t9_rank['true_path_winner']}")
    for item in t9_rank["top_3"]:
        print(f"  Rank {item['rank']}: {item['name']} -> Recomputed: {item['recomputed_normalized']:.4f} (Published: {item['published_normalized']:.4f})")
    print("\n--- First-Principles Graph Inference Ranking ---")
    fp_rank = p1["first_principles_ranking"]
    print(f"Winner: {fp_rank['winner']}")
    for item in fp_rank["top_3"]:
        print(f"  Rank {item['computed_rank']}: {item['name']} -> Computed: {item['computed_normalized']:.4f} (Published: {item['published_normalized']:.4f})")
