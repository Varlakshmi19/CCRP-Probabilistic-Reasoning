"""
DUCAG graph construction (Stage 2 only).

Implements Definition 1 from Dong et al. (2024): DUCAG = (N, E), with node
types and weighted directed causal edges as described in Table 1 of the paper.

This module does NOT perform simplification, CCRP, or attack-path inference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Sequence, Union

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# Node types verified from paper Table 1 (+ BX used in Experiment 2 text).
ALLOWED_NODE_TYPES = frozenset({"B", "BX", "S", "V", "G", "X"})

# Logic-gate operators mentioned in the paper (Table 1).
ALLOWED_GATE_TYPES = frozenset({"AND", "OR", "XOR"})

PathLike = Union[str, Path]


class DUCAGValidationError(ValueError):
    """Raised when a DUCAG graph definition violates paper-related constraints."""


class DUCAGGraph:
    """
    Dynamic Uncertain Causal Attack Graph: DUCAG = (N, E).

    Nodes store ``node_type`` and optional metadata (description, states, prior).
    Directed edges store causal association ``r``, scalar ``transition_probability``
    and/or a ``transition_matrix`` (A-type parameters), matching Table 1 roles.
    """

    def __init__(
        self,
        *,
        name: str = "DUCAG",
        description: str = "",
        completeness: str = "unspecified",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.name = name
        self.description = description
        # completeness should be set by data files, e.g. "partial_demonstration"
        self.completeness = completeness
        self.metadata: dict[str, Any] = dict(metadata or {})
        self.graph = nx.DiGraph()
        self.graph.graph["name"] = name
        self.graph.graph["description"] = description
        self.graph.graph["completeness"] = completeness

    # ------------------------------------------------------------------ nodes
    def add_node(
        self,
        node_id: str,
        node_type: str,
        *,
        description: str = "",
        states: Optional[Sequence[Any]] = None,
        prior: Optional[Mapping[str, float]] = None,
        gate_type: Optional[str] = None,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Add a typed DUCAG node. Does not invent defaults for missing priors."""
        if not node_id or not isinstance(node_id, str):
            raise DUCAGValidationError(f"Invalid node_id: {node_id!r}")
        if node_id in self.graph:
            raise DUCAGValidationError(f"Duplicate node_id: {node_id!r}")

        node_type = node_type.upper()
        if node_type not in ALLOWED_NODE_TYPES:
            raise DUCAGValidationError(
                f"Unsupported node_type {node_type!r} for {node_id!r}. "
                f"Allowed: {sorted(ALLOWED_NODE_TYPES)}"
            )

        if gate_type is not None:
            gate_type = gate_type.upper()
            if node_type != "G":
                raise DUCAGValidationError(
                    f"gate_type is only valid for G-type nodes (got {node_id!r} as {node_type})"
                )
            if gate_type not in ALLOWED_GATE_TYPES:
                raise DUCAGValidationError(
                    f"Unsupported gate_type {gate_type!r}. Allowed: {sorted(ALLOWED_GATE_TYPES)}"
                )

        if prior is not None:
            self._validate_prior(node_id, prior)

        attrs: dict[str, Any] = {
            "node_type": node_type,
            "description": description,
            "states": list(states) if states is not None else None,
            "prior": dict(prior) if prior is not None else None,
            "gate_type": gate_type,
            "label": node_id,
        }
        if attributes:
            # Reserved keys must not be overwritten silently by free-form attrs.
            reserved = {"node_type", "label"}
            clash = reserved.intersection(attributes)
            if clash:
                raise DUCAGValidationError(
                    f"attributes for {node_id!r} collide with reserved keys: {sorted(clash)}"
                )
            attrs.update(attributes)

        self.graph.add_node(node_id, **attrs)

    # ------------------------------------------------------------------ edges
    def add_edge(
        self,
        source: str,
        target: str,
        *,
        r: float,
        transition_probability: Optional[float] = None,
        transition_matrix: Optional[Sequence[Sequence[float]]] = None,
        description: str = "",
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """
        Add a directed causal edge (weighted function variable F).

        Requires causal association degree ``r`` (paper: r_{n;i}).
        Requires at least one of ``transition_probability`` or ``transition_matrix``
        so that A-type parameters are explicit (no silent invention).
        """
        if source not in self.graph:
            raise DUCAGValidationError(
                f"Edge source {source!r} is not a node in the graph"
            )
        if target not in self.graph:
            raise DUCAGValidationError(
                f"Edge target {target!r} is not a node in the graph"
            )
        if source == target:
            raise DUCAGValidationError(
                f"Self-loop edges are not supported in this Stage 2 model: {source!r}"
            )
        if self.graph.has_edge(source, target):
            raise DUCAGValidationError(f"Duplicate directed edge: {source!r} -> {target!r}")

        self._validate_r(source, target, r)

        if transition_probability is None and transition_matrix is None:
            raise DUCAGValidationError(
                f"Edge {source!r} -> {target!r} needs transition_probability "
                "and/or transition_matrix (paper A-type parameters)."
            )

        if transition_probability is not None:
            self._validate_unit_interval(
                transition_probability,
                f"transition_probability on {source!r} -> {target!r}",
            )

        matrix_arr: Optional[np.ndarray] = None
        if transition_matrix is not None:
            matrix_arr = self._validate_transition_matrix(
                transition_matrix, f"transition_matrix on {source!r} -> {target!r}"
            )

        # Paper: F_{n;i} ≡ (r_{n;i} / r_n) A_{n;i}. r_n needs all parents; store
        # local r and optional F factor when r_n can be computed later.
        attrs: dict[str, Any] = {
            "r": float(r),
            "transition_probability": (
                float(transition_probability)
                if transition_probability is not None
                else None
            ),
            "transition_matrix": (
                matrix_arr.tolist() if matrix_arr is not None else None
            ),
            "description": description,
            "weight": (
                float(transition_probability)
                if transition_probability is not None
                else None
            ),
        }
        if attributes:
            reserved = {"r", "transition_probability", "transition_matrix", "weight"}
            clash = reserved.intersection(attributes)
            if clash:
                raise DUCAGValidationError(
                    f"attributes for edge {source!r}->{target!r} collide with "
                    f"reserved keys: {sorted(clash)}"
                )
            attrs.update(attributes)

        self.graph.add_edge(source, target, **attrs)

    # -------------------------------------------------------------- validation
    def validate(self) -> None:
        """
        Validate the whole graph: node types, edge endpoints, directions,
        and probability / weight ranges.
        """
        if self.graph.number_of_nodes() == 0:
            raise DUCAGValidationError("DUCAG has no nodes")

        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get("node_type")
            if node_type not in ALLOWED_NODE_TYPES:
                raise DUCAGValidationError(
                    f"Node {node_id!r} has invalid node_type {node_type!r}"
                )
            if node_type == "G":
                gate = data.get("gate_type")
                if gate is not None and gate not in ALLOWED_GATE_TYPES:
                    raise DUCAGValidationError(
                        f"Node {node_id!r} has invalid gate_type {gate!r}"
                    )
            prior = data.get("prior")
            if prior is not None:
                self._validate_prior(node_id, prior)

        # DiGraph guarantees directed edges; still check endpoints and params.
        for source, target, data in self.graph.edges(data=True):
            if source not in self.graph or target not in self.graph:
                raise DUCAGValidationError(
                    f"Edge {source!r} -> {target!r} references a missing node"
                )
            if "r" not in data:
                raise DUCAGValidationError(
                    f"Edge {source!r} -> {target!r} is missing causal weight r"
                )
            self._validate_r(source, target, data["r"])

            tp = data.get("transition_probability")
            tm = data.get("transition_matrix")
            if tp is None and tm is None:
                raise DUCAGValidationError(
                    f"Edge {source!r} -> {target!r} has neither "
                    "transition_probability nor transition_matrix"
                )
            if tp is not None:
                self._validate_unit_interval(
                    tp, f"transition_probability on {source!r} -> {target!r}"
                )
            if tm is not None:
                self._validate_transition_matrix(
                    tm, f"transition_matrix on {source!r} -> {target!r}"
                )

        # Isolated nodes are allowed (paper may mark unused nodes), but warn via
        # metadata only — not an error.

    def parent_association_sum(self, child: str) -> float:
        """Compute r_n = sum_p r_{n;p} for child n (paper formula context)."""
        if child not in self.graph:
            raise DUCAGValidationError(f"Unknown node: {child!r}")
        return float(sum(data["r"] for _, _, data in self.graph.in_edges(child, data=True)))

    def edge_normalized_r(self, source: str, target: str) -> float:
        """Return (r_{n;i} / r_n) for edge i -> n when r_n > 0."""
        if not self.graph.has_edge(source, target):
            raise DUCAGValidationError(f"No edge {source!r} -> {target!r}")
        r_local = float(self.graph.edges[source, target]["r"])
        r_n = self.parent_association_sum(target)
        if r_n <= 0:
            raise DUCAGValidationError(
                f"Cannot normalize r for {source!r} -> {target!r}: r_n={r_n}"
            )
        return r_local / r_n

    # ----------------------------------------------------------------- queries
    def nodes_of_type(self, node_type: str) -> list[str]:
        node_type = node_type.upper()
        return [
            n
            for n, d in self.graph.nodes(data=True)
            if d.get("node_type") == node_type
        ]

    def get_transition_probability(self, source: str, target: str) -> Optional[float]:
        if not self.graph.has_edge(source, target):
            raise DUCAGValidationError(f"No edge {source!r} -> {target!r}")
        return self.graph.edges[source, target].get("transition_probability")

    def to_networkx(self) -> nx.DiGraph:
        """Return the underlying NetworkX DiGraph (copy-safe for callers)."""
        return self.graph

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "completeness": self.completeness,
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "node_types": {
                t: self.nodes_of_type(t) for t in sorted(ALLOWED_NODE_TYPES)
                if self.nodes_of_type(t)
            },
            "metadata": dict(self.metadata),
        }

    def copy(self) -> "DUCAGGraph":
        """Return a deep copy of this DUCAG (original remains unchanged)."""
        return self.induced_subgraph(list(self.graph.nodes))

    def induced_subgraph(
        self,
        node_ids: Sequence[str],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        completeness: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        validate: bool = True,
    ) -> "DUCAGGraph":
        """
        Build a new DUCAG containing ``node_ids`` and all edges among them.

        Does not modify this graph. Used by Stage 3 simplification to produce
        a separate simplified graph.
        """
        node_set = list(dict.fromkeys(node_ids))  # stable unique
        unknown = [n for n in node_set if n not in self.graph]
        if unknown:
            raise DUCAGValidationError(
                f"induced_subgraph references unknown nodes: {unknown}"
            )

        meta = dict(self.metadata)
        if metadata:
            meta.update(metadata)

        new_g = DUCAGGraph(
            name=name if name is not None else self.name,
            description=description if description is not None else self.description,
            completeness=(
                completeness if completeness is not None else self.completeness
            ),
            metadata=meta,
        )

        for node_id in node_set:
            data = dict(self.graph.nodes[node_id])
            node_type = data.pop("node_type")
            data.pop("label", None)
            description_n = data.pop("description", "")
            states = data.pop("states", None)
            prior = data.pop("prior", None)
            gate_type = data.pop("gate_type", None)
            # Remaining keys are optional attributes (e.g. is_evidence).
            new_g.add_node(
                node_id,
                node_type,
                description=description_n,
                states=states,
                prior=prior,
                gate_type=gate_type,
                attributes=data or None,
            )

        for source, target, data in self.graph.edges(data=True):
            if source not in node_set or target not in node_set:
                continue
            edge_data = dict(data)
            r = edge_data.pop("r")
            tp = edge_data.pop("transition_probability", None)
            tm = edge_data.pop("transition_matrix", None)
            desc_e = edge_data.pop("description", "")
            edge_data.pop("weight", None)
            new_g.add_edge(
                source,
                target,
                r=r,
                transition_probability=tp,
                transition_matrix=tm,
                description=desc_e,
                attributes=edge_data or None,
            )

        if validate and new_g.graph.number_of_nodes() > 0:
            new_g.validate()
        return new_g

    # ----------------------------------------------------------- visualization
    def visualize(
        self,
        output_path: Optional[PathLike] = None,
        *,
        title: Optional[str] = None,
        figsize: tuple[float, float] = (12, 8),
        seed: int = 42,
        show: bool = False,
    ) -> Path:
        """
        Draw the constructed DUCAG with readable labels and edge weights.

        Edge labels use ``transition_probability`` when present.
        """
        self.validate()

        if title is None:
            title = f"{self.name} ({self.completeness})"

        type_colors = {
            "B": "#F4A261",
            "BX": "#E76F51",
            "S": "#2A9D8F",
            "V": "#264653",
            "G": "#E9C46A",
            "X": "#8AB17D",
        }

        pos = nx.spring_layout(self.graph, seed=seed, k=1.8)

        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title, fontsize=12, pad=12)

        for node_type, color in type_colors.items():
            nodelist = self.nodes_of_type(node_type)
            if not nodelist:
                continue
            nx.draw_networkx_nodes(
                self.graph,
                pos,
                nodelist=nodelist,
                node_color=color,
                node_size=1400,
                alpha=0.92,
                ax=ax,
                label=node_type,
            )

        # Dark fills (B/BX/V) use white labels; lighter fills use dark labels.
        dark_types = {"B", "BX", "V"}
        dark_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") in dark_types]
        light_nodes = [n for n in self.graph.nodes if n not in dark_nodes]
        if dark_nodes:
            nx.draw_networkx_labels(
                self.graph,
                pos,
                labels={n: n for n in dark_nodes},
                font_size=9,
                font_color="white",
                font_weight="bold",
                ax=ax,
            )
        if light_nodes:
            nx.draw_networkx_labels(
                self.graph,
                pos,
                labels={n: n for n in light_nodes},
                font_size=9,
                font_color="#1a1a1a",
                font_weight="bold",
                ax=ax,
            )

        nx.draw_networkx_edges(
            self.graph,
            pos,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=16,
            edge_color="#444444",
            width=1.4,
            connectionstyle="arc3,rad=0.06",
            ax=ax,
        )

        edge_labels = {}
        for u, v, data in self.graph.edges(data=True):
            tp = data.get("transition_probability")
            if tp is not None:
                edge_labels[(u, v)] = f"{tp:g}"
            else:
                edge_labels[(u, v)] = f"r={data.get('r'):g}"

        nx.draw_networkx_edge_labels(
            self.graph,
            pos,
            edge_labels=edge_labels,
            font_size=8,
            label_pos=0.55,
            ax=ax,
        )

        ax.legend(scatterpoints=1, loc="upper left", title="Node type")
        note = self.metadata.get("demonstration_note") or self.description
        if note:
            ax.text(
                0.5,
                -0.04,
                note,
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=8,
                wrap=True,
            )
        ax.axis("off")
        fig.tight_layout()

        if output_path is None:
            output_path = Path("results") / "graphs" / f"{self.name}.png"
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)
        return output_path

    # --------------------------------------------------------------- internals
    @staticmethod
    def _validate_unit_interval(value: float, label: str) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError) as exc:
            raise DUCAGValidationError(f"{label} must be numeric, got {value!r}") from exc
        if not 0.0 <= v <= 1.0:
            raise DUCAGValidationError(f"{label} must be in [0, 1], got {v}")

    @staticmethod
    def _validate_r(source: str, target: str, r: float) -> None:
        try:
            r_val = float(r)
        except (TypeError, ValueError) as exc:
            raise DUCAGValidationError(
                f"r on {source!r} -> {target!r} must be numeric, got {r!r}"
            ) from exc
        # Paper uses r as association degree; toy example sets r = 1.
        # Require strictly positive so r_n normalization is well-defined.
        if r_val <= 0:
            raise DUCAGValidationError(
                f"r on {source!r} -> {target!r} must be > 0, got {r_val}"
            )

    @staticmethod
    def _validate_prior(node_id: str, prior: Mapping[str, float]) -> None:
        if not prior:
            raise DUCAGValidationError(f"prior for {node_id!r} is empty")
        total = 0.0
        for state, p in prior.items():
            DUCAGGraph._validate_unit_interval(p, f"prior[{state!r}] for {node_id!r}")
            total += float(p)
        if abs(total - 1.0) > 1e-9:
            raise DUCAGValidationError(
                f"prior for {node_id!r} must sum to 1.0, got {total}"
            )

    @staticmethod
    def _validate_transition_matrix(
        matrix: Sequence[Sequence[float]], label: str
    ) -> np.ndarray:
        try:
            arr = np.asarray(matrix, dtype=float)
        except (TypeError, ValueError) as exc:
            raise DUCAGValidationError(f"{label} is not a numeric matrix") from exc
        if arr.ndim != 2:
            raise DUCAGValidationError(f"{label} must be 2-dimensional")
        if arr.size == 0:
            raise DUCAGValidationError(f"{label} is empty")
        if np.any(arr < 0.0) or np.any(arr > 1.0):
            raise DUCAGValidationError(f"{label} entries must all lie in [0, 1]")
        return arr


def load_ducag_from_dict(data: Mapping[str, Any]) -> DUCAGGraph:
    """
    Build a DUCAGGraph from an explicit dictionary (JSON-compatible).

    Expected keys:
      - name, description, completeness, metadata (optional)
      - nodes: list of {id, node_type, ...}
      - edges: list of {source, target, r, transition_probability?, transition_matrix?}
    """
    if "nodes" not in data or "edges" not in data:
        raise DUCAGValidationError("Graph data must contain 'nodes' and 'edges'")

    ducag = DUCAGGraph(
        name=str(data.get("name", "DUCAG")),
        description=str(data.get("description", "")),
        completeness=str(data.get("completeness", "unspecified")),
        metadata=data.get("metadata") or {},
    )

    for node in data["nodes"]:
        if "id" not in node or "node_type" not in node:
            raise DUCAGValidationError(f"Node entry missing id/node_type: {node!r}")
        ducag.add_node(
            node["id"],
            node["node_type"],
            description=node.get("description", ""),
            states=node.get("states"),
            prior=node.get("prior"),
            gate_type=node.get("gate_type"),
            attributes=node.get("attributes"),
        )

    for edge in data["edges"]:
        if "source" not in edge or "target" not in edge:
            raise DUCAGValidationError(f"Edge entry missing source/target: {edge!r}")
        if "r" not in edge:
            raise DUCAGValidationError(
                f"Edge {edge.get('source')}->{edge.get('target')} missing required 'r'"
            )
        ducag.add_edge(
            edge["source"],
            edge["target"],
            r=edge["r"],
            transition_probability=edge.get("transition_probability"),
            transition_matrix=edge.get("transition_matrix"),
            description=edge.get("description", ""),
            attributes=edge.get("attributes"),
        )

    ducag.validate()
    return ducag


def load_ducag_from_json(path: PathLike) -> DUCAGGraph:
    """Load graph data from a JSON file and return a validated DUCAGGraph."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return load_ducag_from_dict(data)


def dump_ducag_template() -> dict[str, Any]:
    """Return an empty schema template for authoring paper data files."""
    return {
        "name": "",
        "description": "",
        "completeness": "partial_demonstration",
        "metadata": {
            "paper": "Dong et al., Journal of Cloud Computing (2024) 13:24",
            "doi": "10.1186/s13677-023-00568-7",
            "source_in_paper": "",
            "demonstration_note": "",
        },
        "nodes": [],
        "edges": [],
    }


if __name__ == "__main__":
    # Minimal smoke usage; prefer examples/build_table2_demo.py for the Stage 2 demo.
    root = Path(__file__).resolve().parents[1]
    data_path = root / "experiments" / "paper_data" / "table2_fig1_partial.json"
    g = load_ducag_from_json(data_path)
    out = g.visualize(root / "results" / "graphs" / "table2_fig1_partial.png")
    print(g.summary())
    print(f"Wrote {out}")
