# Implementation Plan — Fresh DUCAG / CCRP Reproduction

**Scope of this document:** Stage 1 planning only.  
**Authority:** `PROJECT_SPEC.md` + `docs/paper_algorithm_mapping.md`  
**Rule:** Do not implement Stages 2–8 until the user explicitly approves.  
**Rule:** Do not invent formulas, graph edges, transition probabilities, or expected results.

---

## 0. Project posture

| Principle | Plan |
|-----------|------|
| Fresh codebase | New Python modules under this workspace; **no** reuse of prior GitHub / old CCRP project code |
| Paper fidelity | Implement equations (1)–(7) and CCRP steps as mapped |
| Honesty | Compare against published values; report mismatches; never force-fit by hardcoding answers into inference |
| Beginner-friendly | NetworkX + NumPy + Matplotlib + Pytest + optional Streamlit; minimal extra deps |

Suggested root (per spec; may keep current folder `CCRP` as the project root):

```text
DUCAG_CCRP_Fresh/   # or current CCRP/
  PROJECT_SPEC.md
  README.md
  requirements.txt
  app.py
  src/
  experiments/
  tests/
  results/
  docs/
```

---

## 1. Stage gate overview

| Stage | Goal | Exit criterion |
|-------|------|----------------|
| **1** | Paper mapping + this plan | Docs exist; user approves |
| **2** | Graph construction | Nodes/edges/params load & validate; visualize |
| **3** | Simplification | Before/after graphs match paper cases where known |
| **4** | CCRP math | Reproduce Tables 3 and 8 chain-style calculations |
| **5** | All four experiments | Runnable scripts; logs of intermediates |
| **6** | Published vs computed | Comparison tables; discrepancy notes |
| **7** | Streamlit demo | Views driven by live Python results |
| **8** | Final tests + README | pytest green; reproducible commands |

**Current status:** Stage 1 complete pending approval.

---

## 2. Mapping of paper artifacts → code modules

| Paper concept | Planned module | Notes |
|---------------|----------------|-------|
| DUCAG = (N, E); X/S/V, B, G, r, A, F | `src/ducag_graph.py` | NetworkX DiGraph + typed node/edge attrs |
| Causality simplification + sub-DUCAG split | `src/graph_simplification.py` | Only paper-described + cited DUCG rules once verified |
| Causal-chain expand / UCC·ECC·HCC / eliminate UCC | `src/ccrp.py` | Core CCRP Steps 1–2 |
| Eq. (5) posterior; normalization | `src/probability_calculations.py` | Transparent substitution & logging |
| Eqs. (6)–(7); path ranking | `src/attack_path_analysis.py` | Scenario reconstruction Steps 1–4 |
| Experiment inputs | `experiments/paper_data.json` + `paper_experiment_*.py` | Data separate from algorithm |
| Demo | `app.py` | No hardcoded experiment answers |

---

## 3. Stage 2 plan — DUCAG construction

### 3.1 Implement

- Node types: `B`, `BX`, `S`, `V`, `G`, (generic `X` if needed)
- Directed edges with fields: `r`, transition / `A` parameter, optional gate semantics
- Constructors from explicit JSON/dict (no silent defaults for missing probabilities)
- Validation: dangling edges, missing params, illegal states, duplicate IDs
- Visualization: labels, directions, weights (Matplotlib)

### 3.2 Data to encode first (verified)

1. **Toy Fig. 1 / Table 2** — smallest closed example  
2. **Experiment 2 / Table 6** — primary numeric reproduction case  

### 3.3 Blocked until verification

- Full Fig. 3 (Exp. 1) edge list & matrices from [25], [31]  
- Full Fig. 7–8 (Exp. 3) parameters from [35]  

**Action when blocked:** encode only figure-recoverable structure; mark unknown params in data files as `"status": "needs_verification"` rather than guessing.

### 3.4 Tests

- Load Table 2 graph; assert edge probabilities match paper  
- Reject graphs missing required A/r fields  

---

## 4. Stage 3 plan — graph simplification

### 4.1 Implement from paper narrative first

Operational behaviors explicitly described:

1. Mark evidence nodes from alarm set at \(T_i\)  
2. Remove events irrelevant to evidence + concerned hypothesis  
3. Decompose by root hypothesis into sub-DUCAGs  
4. Drop a hypothesis sub-graph that cannot explain all abnormal evidence (Fig. 2 \(T_3\) / Exp. 3 only-\(B_2\) pattern)

### 4.2 Must not invent

Full 10–11 DUCG rule list. Before coding advanced rules:

- Digitize Exp. 2 Fig. 6 and Exp. 3 Fig. 8  
- Optionally consult DUCG refs [18–21] and document which rules are used  
- Add a `docs/simplification_rules_verification.md` note in Stage 3  

### 4.3 Verification targets

| Case | Expected qualitative outcome |
|------|------------------------------|
| Exp. 2 Path 1 | Matches Fig. 6 structure (after digitization) |
| Exp. 3 | Only \(B_2\) remains; path through \(V_1,S_1,V_4,S_4,V_8,S_7\) |
| Exp. 1 Path One | Only \(B_2\) explains evidence |

### 4.4 Display requirements (spec)

Show graph **before** and **after** simplification; explain removals; ensure inference uses the simplified graph.

---

## 5. Stage 4 plan — CCRP

### 5.1 Algorithm skeleton (paper order)

```text
for each concerned node X_v:
  1. Expand causal chains (upward & backward) until root / terminal / evidence
  2. Classify each chain as UCC | ECC | HCC          # Eq. (3)
  3. Discard UCC                                      # Eq. (4)
  4. Substitute priors / transition params into ECC+HCC
  5. Pr(X_v) = (sum retained chain values) / N        # Eq. (5)
```

Then scenario layer:

```text
simplify → CCRP all nodes
for each candidate AttackSeq:
  Pr = product of node posteriors along path           # Eq. (6)
  if path shared across hypotheses: sum / scale        # Eq. (7)
normalize; argmax                                      # Step 4
```

### 5.2 Transparency requirement

For each important calculation log:

- evidence & hypothesis  
- equation id  
- substituted numbers  
- intermediate chain values  
- N and normalization  
- final posterior / path probability  

### 5.3 Calibration order (do not skip)

1. Reproduce **Table 3** toy posteriors and normalized path probs **0.5019 / 0.4981**  
2. Reproduce **Table 8** Path-1 node posteriors under \(B_1\)  
3. Reproduce **Table 9** path products and normals (**0.3542, 0.2941, 0.1293**, …)  

If (1)–(3) fail, stop and diagnose; do not proceed to Exp. 1/3 topology work.

### 5.4 Open math questions (resolve with paper tables, not invention)

Document resolution in code comments / Stage 4 notes:

- Exact counting of \(N\)  
- How fractional coefficients \(1/2,1/3,1/4\) arise in Tables 3 & 8  
- Treatment of evidence nodes fixed at posterior 1  
- Formula (7) aggregation when labels are `B_1(BX_1)`  

---

## 6. Stage 5 plan — four experiments

### Experiment 1 — DARPA / LLDOS

| Item | Plan |
|------|------|
| Inputs | Table 5 sequences; Fig. 3/4 once digitized; params from [25],[31] if obtainable |
| Procedure | Simplify per path → reason → compare candidate sequences |
| Success | Match published candidate paths (qualitative) |
| If params unavailable | Record blocker; do not fabricate matrices |

### Experiment 2 — simulated network (priority)

| Item | Plan |
|------|------|
| Inputs | Table 6; Paths 1–3; evidence/missing/redundant per Table 7 |
| Path 1 (required) | Evidence `{V1,V3,S4,V6,V11,V13,S9}`; missing `{S2,S6,S8}`; target `S9` |
| Outputs | Tables 8–9 style intermediates; top-3 probs |
| Path 2/3 | Same pipeline; verify Table 7 published probs after confirming Path-3 `0.1882` digit |

### Experiment 3 — risk comparison

| Item | Plan |
|------|------|
| Inputs | Fig. 7–8 structure; evidence `V1,V4`; target `S7` |
| Outputs | CCRP row of Table 10; winning path |
| Comparison rows | Store Ref [32]/[35]/[36] as **published reference data**, not re-derived unless implementing those methods |

### Experiment 4 — runtime

| Item | Plan |
|------|------|
| Inputs | Random DAG generator per paper; evidence = hosts/2; 25 groups |
| Baseline | BNRP as described in [24]/[35] — implement a clear, documented BN inference baseline |
| Outputs | Timing curves vs host count; compare **trend** to Fig. 9 |
| Exact ms match | Not required unless Fig. 9 is digitized; hardware differs |

### Experiment runner commands (planned)

```bash
python -m experiments.paper_experiment_1
python -m experiments.paper_experiment_2
python -m experiments.paper_experiment_3
python -m experiments.paper_experiment_4
```

---

## 7. Stage 6 plan — results comparison

For every metric:

| Column | Content |
|--------|---------|
| Experiment | 1–4 / toy |
| Metric | e.g. `Pr(path1 normalized)` |
| Published | value from paper mapping |
| Computed | algorithm output |
| Abs diff | if numeric |
| Match status | exact / within ε / qualitative / blocked |
| Notes | equation / table / figure reference |

ε policy (proposed for approval): absolute tolerance **1e-3** for 4-decimal published probs unless paper shows more digits.

Never overwrite computed results with published ones in the algorithm path.

---

## 8. Stage 7 plan — Streamlit demo

Views (all backed by `src/`):

1. Project overview  
2. DUCAG visualization  
3. Evidence / hypothesis selection  
4. Simplification before/after  
5. Step-by-step CCRP  
6. Chain expansion & UCC elimination  
7. Intermediate probabilities  
8. Final posteriors  
9. Attack-path ranking  
10. Per-experiment pages  
11. Published vs computed table  

No animations, auth, or deployment scope.

---

## 9. Stage 8 plan — tests and docs

### Tests

- `tests/test_graph.py` — construction / validation  
- `tests/test_ccrp.py` — chain classify / eliminate / Eq. (5)  
- `tests/test_probabilities.py` — Table 3 / formula (6)–(7)  
- `tests/test_experiments.py` — Exp. 2 Path 1 top-3; Exp. 3 Table 10 CCRP row when data complete  

### Deliverables

- `README.md` — install, test, run experiments, launch app  
- `docs/implementation_report.md` — what was implemented  
- `docs/paper_comparison.md` — Stage 6 tables  
- `results/graphs|tables|logs/` — artifacts  

### `requirements.txt` (planned)

```text
networkx
numpy
matplotlib
pytest
streamlit
```

---

## 10. Verification work still required before / during later stages

Tracked from `paper_algorithm_mapping.md` §6:

| ID | Item | Needed for |
|----|------|------------|
| V1 | Digitize Fig. 5–6 edges if Table 6 incomplete for all nodes | Exp. 2 |
| V2 | Confirm Table 8 \(S_8=0.3512\) and Table 7 Path3 \(0.1882\) from PDF | Exp. 2 |
| V3 | Recover \(BX_1\) Path-1 node posteriors (omitted) | Full Table 9 derivation |
| V4 | Clarification of \(N\) using Tables 3 & 8 | CCRP |
| V5 | DUCG simplification rules from [21] applicable subset | Stage 3 |
| V6 | Exp. 1 matrices from [25],[31] | Exp. 1 |
| V7 | Exp. 3 full params from [35] / figures | Exp. 3 beyond Table 10 storage |
| V8 | Digitize Fig. 9 if exact timing comparison desired | Exp. 4 |
| V9 | Resolve toy-example path label vs product inconsistency | Stage 4 notes |

**Until verified, data files must flag fields as unverified — never fill with invented numbers.**

---

## 11. Immediate next step after approval

On user approval of Stage 1:

1. Create directory skeleton + `requirements.txt` + package `__init__` files  
2. Begin **Stage 2 only**: implement `ducag_graph.py` and encode **Table 2 toy graph** + **Table 6 Exp. 2 graph**  
3. Add visualization and validation tests  
4. Stop and report Stage 2 results before Stage 3  

---

## 12. Approval checkpoint

Please confirm:

1. The algorithm mapping in `docs/paper_algorithm_mapping.md` is acceptable.  
2. The four experiments and Path-1 incomplete-alarm configuration are correctly identified.  
3. Gaps marked **[NEEDS VERIFICATION]** / **[EXTERNAL]** should remain unresolved (no invented data).  
4. Proceed to **Stage 2 (graph construction only)** when you say so.

---

*End of Stage 1 implementation plan. No algorithm implementation performed yet.*
