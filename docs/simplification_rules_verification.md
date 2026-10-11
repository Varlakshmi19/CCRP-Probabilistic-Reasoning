# Simplification rules — verified vs unresolved (Stage 3)

**Paper:** Dong et al. (2024), DOI 10.1186/s13677-023-00568-7  
**Module:** `src/graph_simplification.py`  
**Rule:** Do not invent missing DUCG rules from reference [21].

---

## Explicitly supported by the paper (implemented)

| Rule ID | Paper basis | Implementation |
|---------|-------------|----------------|
| `P-MARK-EVIDENCE` | Observed alarms marked as evidence (Fig. 2 blue nodes) | `is_evidence=True` on simplified graph nodes |
| `P-MARK-TARGET` | Target used after simplification in attack-scenario steps; allowed as input | Mark `is_target` when target remains in kept set; **no** invented target-deletion rules |
| `P-DECOMPOSE-HYP` | Decompose into multiple sub-DUCAGs per root hypothesis | `decompose_into_sub_ducags`; sub-DUCAG = hypothesis + descendants |
| `P-HYP-EXPLAIN` | Fig. 2: hypothesis that cannot explain all observed alarms is removed; Exp. 3: only \(B_2\) remains | Retain hypothesis iff a **directed path** exists to every evidence node; remove hypothesis + exclusive subgraph |
| `P-IRRELEVANT` | Remove events unconcerned / irrelevant to observed evidence and concerned hypothesis | Keep union of retained hypothesis sub-DUCAGs; remove all other nodes/edges |

### Operationalizations (stated limitations)

1. **“Explain all evidence”** → directed-path reachability from hypothesis to each evidence node. The paper states the criterion; it does not publish the full [21] logical test.
2. **“Irrelevant events”** → nodes/edges outside retained hypothesis sub-DUCAGs. The paper does not give a complete internal cleanup checklist beyond evidence/hypothesis relevance and hypothesis pruning.

These operationalizations are **not** claimed to be identical to every rule in [21].

---

## Not implemented (remain unresolved — require [21] or figure digitization)

| Item | Why unresolved |
|------|----------------|
| Full DUCG numbered simplification rule list (~10–11 rules) | Paper cites [21]; rules not enumerated in this paper |
| Delete causal link when \(A\)-matrix entry is 0 | DUCG literature; not stated with parameters in this paper’s Stage 3 scope |
| Delete normal-state variables with no active causal role | DUCG literature; state polarity details not fully operationalized here |
| Virtual D-type causes for isolated abnormal evidence | DUCG literature; not described in this paper’s attack-graph section |
| Evidence-blocked pathway deletion inside a kept sub-DUCAG | Not specified beyond the high-level narrative |
| Exact Exp. 1 / Exp. 2 / Exp. 3 simplified figure topologies | Figures not digitized; full experiment graphs not yet encoded |
| Treating approximation as “the original DUCG algorithm” | Explicitly disallowed |

---

## What Stage 3 tests cover

Synthetic graphs constructed only to exercise the **verified** behaviors above:

- Evidence marking  
- Irrelevant / unconcerned node removal outside retained sub-DUCAGs  
- Hypothesis pruning when evidence cannot be explained  
- Original graph immutability  

They do **not** claim to reproduce Experiment 1–3 published figures end-to-end.
