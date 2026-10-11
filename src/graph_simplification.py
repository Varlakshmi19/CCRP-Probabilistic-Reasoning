"""
DUCAG causality simplification (Stage 3).

Implements ONLY simplification behaviors that are explicitly stated in
Dong et al. (2024) and recorded as verified in docs/paper_algorithm_mapping.md.

This is NOT a re-implementation of the full DUCG rule catalog in reference [21].
See docs/simplification_rules_verification.md for the verified vs unresolved list.

Does not perform CCRP, probability inference, or attack-path reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

import networkx as nx

from .ducag_graph import DUCAGGraph, DUCAGValidationError

# ---------------------------------------------------------------------------
# Verified paper-supported rule identifiers (see simplification_rules_verification.md)
# ---------------------------------------------------------------------------

RULE_MARK_EVIDENCE = "P-MARK-EVIDENCE"
RULE_MARK_TARGET = "P-MARK-TARGET"
RULE_DECOMPOSE_HYPOTHESIS = "P-DECOMPOSE-HYP"
RULE_HYPOTHESIS_EXPLAIN = "P-HYP-EXPLAIN"
RULE_IRRELEVANT_TO_RETAINED = "P-IRRELEVANT"

HYPOTHESIS_NODE_TYPES = frozenset({"B", "BX"})

UNRESOLVED_DUCG_RULES_NOTE = (
    "The reference paper cites DUCG simplification in [21] but does not enumerate "
    "the full rule list (commonly ~10-11 rules: e.g. A-matrix zero link deletion, "
    "normal-state variable deletion, virtual D-type causes, detailed inconsistency "
    "logic). Those rules are NOT implemented here and must not be treated as present."
)


@dataclass(frozen=True)
class RemovalRecord:
    """One removed graph element with an explicit paper-supported reason."""

    kind: str  # "node" or "edge"
    element: Any  # node id or (source, target)
    reason: str
    rule_id: str


@dataclass
class SimplificationResult:
    """Outcome of simplification; original graph is never mutated."""

    original: DUCAGGraph
    simplified: DUCAGGraph
    evidence: list[str]
    target: Optional[str]
    candidate_hypotheses: list[str]
    retained_hypotheses: list[str]
    pruned_hypotheses: list[str]
    removed_nodes: list[RemovalRecord] = field(default_factory=list)
    removed_edges: list[RemovalRecord] = field(default_factory=list)
    applied_rules: list[str] = field(default_factory=list)
    unresolved_limitations: list[str] = field(default_factory=list)

    def removal_summary(self) -> dict[str, Any]:
        return {
            "retained_hypotheses": list(self.retained_hypotheses),
            "pruned_hypotheses": list(self.pruned_hypotheses),
            "removed_nodes": [
                {"node": r.element, "reason": r.reason, "rule_id": r.rule_id}
                for r in self.removed_nodes
            ],
            "removed_edges": [
                {
                    "edge": list(r.element),
                    "reason": r.reason,
                    "rule_id": r.rule_id,
                }
                for r in self.removed_edges
            ],
            "applied_rules": list(self.applied_rules),
            "unresolved_limitations": list(self.unresolved_limitations),
        }


class SimplificationError(ValueError):
    """Invalid simplification inputs or unsupported requests."""


def list_hypothesis_nodes(ducag: DUCAGGraph) -> list[str]:
    """Return B/BX root-hypothesis nodes (paper Definition / Exp. 2 BX)."""
    nodes = []
    for node_id, data in ducag.graph.nodes(data=True):
        if data.get("node_type") in HYPOTHESIS_NODE_TYPES:
            nodes.append(node_id)
    return sorted(nodes)


def hypothesis_explains_all_evidence(
    ducag: DUCAGGraph,
    hypothesis: str,
    evidence: Sequence[str],
) -> bool:
    """
    Paper criterion (Fig. 2 note; Exp. 3): a hypothesis is kept only if it can
    explain all observed alarm evidence.

    Operationalization used here (documented limitation): there is a directed
    path from the hypothesis to every evidence node. Finer DUCG conditions from
    [21] are unresolved and not applied.
    """
    if hypothesis not in ducag.graph:
        raise SimplificationError(f"Unknown hypothesis: {hypothesis!r}")
    g = ducag.graph
    for e in evidence:
        if e not in g:
            raise SimplificationError(f"Evidence node not in graph: {e!r}")
        if e == hypothesis:
            continue
        if not nx.has_path(g, hypothesis, e):
            return False
    return True


def hypothesis_descendant_nodes(ducag: DUCAGGraph, hypothesis: str) -> set[str]:
    """
    Nodes in the sub-DUCAG of ``hypothesis``: the hypothesis itself and all
    nodes reachable from it (paper: decompose by each root-event hypothesis).
    """
    if hypothesis not in ducag.graph:
        raise SimplificationError(f"Unknown hypothesis: {hypothesis!r}")
    return {hypothesis} | set(nx.descendants(ducag.graph, hypothesis))


def simplify_ducag(
    ducag: DUCAGGraph,
    evidence: Sequence[str],
    *,
    target: Optional[str] = None,
    concerned_hypotheses: Optional[Sequence[str]] = None,
) -> SimplificationResult:
    """
    Simplify a DUCAG under observed evidence without modifying ``ducag``.

    Verified paper-supported steps applied:
      1. Mark evidence (and optional target) on the simplified copy.
      2. Consider root hypotheses (B/BX), optionally restricted to
         ``concerned_hypotheses``.
      3. Prune any hypothesis that cannot explain all evidence.
      4. Keep the union of sub-DUCAGs of retained hypotheses (hypothesis +
         descendants); remove all other nodes/edges as irrelevant to the
         retained hypotheses under the observed evidence.

    Parameters
    ----------
    evidence:
        Observed alarm / evidence node ids (required; paper simplifies using
        observed attack events).
    target:
        Optional target node. Recorded and marked when present in the kept
        set. Target is NOT used to invent extra retention rules beyond the
        paper's evidence/hypothesis simplification narrative.
    concerned_hypotheses:
        Optional subset of hypotheses to consider (Fig. 1(b)-style "simplified
        DUCAG of the B1 hypothesis"). Defaults to all B/BX nodes.
    """
    ducag.validate()
    evidence_list = list(dict.fromkeys(evidence))
    if not evidence_list:
        raise SimplificationError(
            "Simplification requires a non-empty evidence set (paper: observed "
            "attack events / alarms)."
        )

    for e in evidence_list:
        if e not in ducag.graph:
            raise SimplificationError(f"Evidence node not in graph: {e!r}")

    if target is not None and target not in ducag.graph:
        raise SimplificationError(f"Target node not in graph: {target!r}")

    all_hyps = list_hypothesis_nodes(ducag)
    if concerned_hypotheses is None:
        candidates = list(all_hyps)
    else:
        candidates = list(dict.fromkeys(concerned_hypotheses))
        for h in candidates:
            if h not in ducag.graph:
                raise SimplificationError(f"Concerned hypothesis not in graph: {h!r}")
            if ducag.graph.nodes[h].get("node_type") not in HYPOTHESIS_NODE_TYPES:
                raise SimplificationError(
                    f"{h!r} is not a B/BX hypothesis node "
                    f"(type={ducag.graph.nodes[h].get('node_type')!r})"
                )

    if not candidates:
        raise SimplificationError(
            "No hypothesis nodes (B/BX) available for simplification."
        )

    applied = [
        RULE_MARK_EVIDENCE,
        RULE_DECOMPOSE_HYPOTHESIS,
        RULE_HYPOTHESIS_EXPLAIN,
        RULE_IRRELEVANT_TO_RETAINED,
    ]
    if target is not None:
        applied.append(RULE_MARK_TARGET)

    retained: list[str] = []
    pruned: list[str] = []
    removed_nodes: list[RemovalRecord] = []
    removed_edges: list[RemovalRecord] = []

    # Rule P-HYP-EXPLAIN: keep only hypotheses that explain all evidence.
    for h in candidates:
        if hypothesis_explains_all_evidence(ducag, h, evidence_list):
            retained.append(h)
        else:
            pruned.append(h)
            removed_nodes.append(
                RemovalRecord(
                    kind="node",
                    element=h,
                    reason=(
                        f"Hypothesis {h} cannot explain all observed evidence "
                        f"{evidence_list} (no directed path to at least one "
                        f"evidence node). Paper Fig. 2 / Exp. 3."
                    ),
                    rule_id=RULE_HYPOTHESIS_EXPLAIN,
                )
            )

    # Keep union of sub-DUCAGs of retained hypotheses.
    keep: set[str] = set()
    for h in retained:
        keep |= hypothesis_descendant_nodes(ducag, h)

    # Evidence and target markers: evidence must remain if explained; if a
    # retained hypothesis explains all evidence, every evidence node is
    # reachable from that hypothesis and therefore in its descendant set
    # (or is the hypothesis itself).
    for e in evidence_list:
        if retained and e not in keep:
            # Defensive: should not happen if explainability uses directed paths.
            raise SimplificationError(
                f"Internal error: evidence {e!r} missing from retained sub-DUCAGs"
            )

    pruned_set = set(pruned)
    original_nodes = set(ducag.graph.nodes)
    for n in sorted(original_nodes - keep):
        # Hypothesis nodes that failed explainability were already recorded.
        if n in pruned_set:
            continue
        owner = _exclusive_pruned_owner(ducag, n, pruned, retained)
        if owner is not None:
            reason = (
                f"Node {n} lies in the sub-DUCAG of pruned hypothesis {owner} "
                f"and is not retained under surviving hypotheses {retained}."
            )
            rule = RULE_HYPOTHESIS_EXPLAIN
        else:
            reason = (
                f"Node {n} is irrelevant to retained hypotheses {retained} "
                f"under evidence {evidence_list} (not in any retained "
                f"hypothesis sub-DUCAG). Paper: remove events unconcerned / "
                f"irrelevant to observed evidence and concerned hypothesis."
            )
            rule = RULE_IRRELEVANT_TO_RETAINED
        removed_nodes.append(
            RemovalRecord(kind="node", element=n, reason=reason, rule_id=rule)
        )

    # Edges removed: any edge with an endpoint not in keep, plus edges among
    # kept nodes are kept. Record edges that disappear.
    for u, v in ducag.graph.edges():
        if u in keep and v in keep:
            continue
        owner_u = (
            _exclusive_pruned_owner(ducag, u, pruned, retained)
            if u not in keep and u not in pruned_set
            else None
        )
        owner_v = (
            _exclusive_pruned_owner(ducag, v, pruned, retained)
            if v not in keep and v not in pruned_set
            else None
        )
        is_hyp_pruned = (
            u in pruned_set
            or v in pruned_set
            or owner_u is not None
            or owner_v is not None
        )
        rule = RULE_HYPOTHESIS_EXPLAIN if is_hyp_pruned else RULE_IRRELEVANT_TO_RETAINED

        if u not in keep and v not in keep:
            reason = (
                f"Edge {u}->{v} removed because both endpoints were removed."
            )
        elif u not in keep:
            reason = f"Edge {u}->{v} removed because source {u} was removed."
        else:
            reason = f"Edge {u}->{v} removed because target {v} was removed."
        removed_edges.append(
            RemovalRecord(
                kind="edge",
                element=(u, v),
                reason=reason,
                rule_id=rule,
            )
        )

    limitations = [
        UNRESOLVED_DUCG_RULES_NOTE,
        (
            "Hypothesis 'explains evidence' is operationalized as directed-path "
            "reachability from hypothesis to each evidence node. The paper states "
            "the explainability criterion but does not spell out [21]'s fuller logic."
        ),
        (
            "Within a retained hypothesis sub-DUCAG, finer deletion of individual "
            "irrelevant internal nodes (beyond dropping other hypotheses' "
            "subgraphs) is not fully specified in the paper text and is not "
            "approximated here."
        ),
    ]
    if target is not None and retained and target not in keep:
        limitations.append(
            f"Target {target!r} is not inside any retained hypothesis sub-DUCAG; "
            "it is recorded as input but absent from the simplified graph. "
            "No extra retention rule for targets is invented."
        )

    # Build separate simplified graph (may be empty if no hypothesis retained).
    meta = {
        "simplification": {
            "evidence": evidence_list,
            "target": target,
            "retained_hypotheses": retained,
            "pruned_hypotheses": pruned,
            "applied_rules": applied,
        }
    }
    simplified = ducag.induced_subgraph(
        sorted(keep),
        name=f"{ducag.name}_simplified",
        description=(
            f"Simplified DUCAG under evidence={evidence_list}, "
            f"retained_hypotheses={retained}"
        ),
        completeness="simplified_from_parent",
        metadata=meta,
        validate=bool(keep),
    )

    # Mark evidence / target on the simplified copy only.
    for e in evidence_list:
        if e in simplified.graph:
            simplified.graph.nodes[e]["is_evidence"] = True
    if target is not None and target in simplified.graph:
        simplified.graph.nodes[target]["is_target"] = True

    return SimplificationResult(
        original=ducag,
        simplified=simplified,
        evidence=evidence_list,
        target=target,
        candidate_hypotheses=candidates,
        retained_hypotheses=retained,
        pruned_hypotheses=pruned,
        removed_nodes=removed_nodes,
        removed_edges=removed_edges,
        applied_rules=applied,
        unresolved_limitations=limitations,
    )


def decompose_into_sub_ducags(
    ducag: DUCAGGraph,
    *,
    hypotheses: Optional[Sequence[str]] = None,
) -> dict[str, DUCAGGraph]:
    """
    Decompose into per-hypothesis sub-DUCAGs (paper: multiple sub-DUCAG based
    on each root event hypothesis). Does not prune by evidence.
    """
    ducag.validate()
    hyps = (
        list(dict.fromkeys(hypotheses))
        if hypotheses is not None
        else list_hypothesis_nodes(ducag)
    )
    result: dict[str, DUCAGGraph] = {}
    for h in hyps:
        nodes = sorted(hypothesis_descendant_nodes(ducag, h))
        result[h] = ducag.induced_subgraph(
            nodes,
            name=f"{ducag.name}_sub_{h}",
            description=f"Sub-DUCAG for hypothesis {h}",
            completeness="sub_ducag_decomposition",
            metadata={"hypothesis": h, "rule_id": RULE_DECOMPOSE_HYPOTHESIS},
        )
    return result


def _exclusive_pruned_owner(
    ducag: DUCAGGraph,
    node: str,
    pruned: Sequence[str],
    retained: Sequence[str],
) -> Optional[str]:
    """Return a pruned hypothesis that reaches ``node``, if any (for reasons)."""
    for h in pruned:
        if node == h or node in nx.descendants(ducag.graph, h):
            # Prefer exclusive ownership: not also under a retained hyp.
            under_retained = any(
                node == r or node in nx.descendants(ducag.graph, r) for r in retained
            )
            if not under_retained:
                return h
    return None


def verified_rule_catalog() -> list[dict[str, str]]:
    """Machine-readable list of rules this module claims to implement."""
    return [
        {
            "rule_id": RULE_MARK_EVIDENCE,
            "status": "verified_from_paper",
            "summary": "Mark observed alarm events as evidence on the simplified graph.",
        },
        {
            "rule_id": RULE_MARK_TARGET,
            "status": "input_supported_marking_only",
            "summary": (
                "Optional target node may be supplied and marked when retained; "
                "no invented target-specific deletion rules."
            ),
        },
        {
            "rule_id": RULE_DECOMPOSE_HYPOTHESIS,
            "status": "verified_from_paper",
            "summary": "Decompose into sub-DUCAGs per root hypothesis (B/BX).",
        },
        {
            "rule_id": RULE_HYPOTHESIS_EXPLAIN,
            "status": "verified_from_paper_with_operationalization",
            "summary": (
                "Remove hypotheses (and their exclusive subgraphs) that cannot "
                "explain all observed evidence."
            ),
        },
        {
            "rule_id": RULE_IRRELEVANT_TO_RETAINED,
            "status": "verified_from_paper_with_operationalization",
            "summary": (
                "Remove events outside retained hypothesis sub-DUCAGs as "
                "irrelevant / unconcerned under the observed evidence."
            ),
        },
    ]
