"""
Stage 2 usage example: build and visualize the Table 2 partial DUCAG.

This graph uses ONLY transition probabilities printed in Table 2 of
Dong et al. (2024). It is a partial demonstration, not a full paper experiment.

Run from the project root:

    python examples/build_table2_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ducag_graph import load_ducag_from_json


def main() -> None:
    data_path = ROOT / "experiments" / "paper_data" / "table2_fig1_partial.json"
    out_path = ROOT / "results" / "graphs" / "table2_fig1_partial.png"

    ducag = load_ducag_from_json(data_path)
    summary = ducag.summary()

    print("=== DUCAG Stage 2 demo ===")
    print(f"Name:          {summary['name']}")
    print(f"Completeness:  {summary['completeness']}")
    print(f"Nodes:         {summary['num_nodes']}")
    print(f"Edges:         {summary['num_edges']}")
    print(f"Node types:    {summary['node_types']}")
    print()
    print("Verified Table 2 edges:")
    for u, v, data in ducag.to_networkx().edges(data=True):
        print(f"  {u} -> {v}: transition_probability={data['transition_probability']}, r={data['r']}")

    image = ducag.visualize(
        out_path,
        title="DUCAG partial demo — Table 2 only (NOT a full paper experiment)",
    )
    print()
    print(f"Wrote graph image: {image}")
    note = ducag.metadata.get("demonstration_note")
    if note:
        print()
        print(note)


if __name__ == "__main__":
    main()
