# Fresh Project Specification: DUCAG and CCRP Paper Reproduction

## Objective

Build a new Python project from scratch that faithfully implements the DUCAG model and CCRP probabilistic reasoning algorithm from the reference research paper.

Reference paper:
"A New Method of Dynamic Network Security Analysis Based on Dynamic Uncertain Causality Graph"

https://link.springer.com/article/10.1186/s13677-023-00568-7

The purpose is to understand and demonstrate the published algorithm, graph construction, intermediate reasoning, probability calculations, experiments, and comparison with the original paper.

This is a reproduction project. No new algorithm, research contribution, or machine learning model is required.

## 1. Fresh implementation requirement

Start with a new project directory.

Do not copy, import, or reuse implementation code from my previous GitHub repository or old project folders.

Do not assume that previously generated results are correct.

Read the reference paper and independently implement its methods in newly written code.

Use the original paper's graph structures, parameters, equations, evidence, experimental cases, and published results wherever they are specified.

Do not invent missing data or expected results.

## 2. Technology

Use:

- Python for the algorithm and experiments.
- NetworkX for graph representation where suitable.
- Matplotlib for graph visualization.
- NumPy for numerical calculations where useful.
- Pytest for testing.
- Streamlit for a simple local demonstration interface, if appropriate.

Keep the implementation beginner-friendly and avoid unnecessary dependencies.

## 3. Core implementation

Implement the following from the paper:

### A. DUCAG construction

- Represent the node types and directed causal relationships defined in the paper.
- Store causal weights and other necessary parameters.
- Construct the graph from explicit input data.
- Validate nodes, edges, and probability parameters.
- Display the actual computational graph.
- Show node labels, edge directions, and causal weights.
- Explain the purpose of the important nodes.

### B. Graph simplification

- Implement the paper's graph simplification procedure.
- Use the specified evidence and target nodes.
- Display the graph before and after simplification.
- Explain which nodes or relationships were removed and why.
- Ensure that the displayed simplified graph matches the graph used in inference.

### C. CCRP algorithm

Implement the paper's exact reasoning procedure:

1. Expand causal chains.
2. Classify chains using the categories defined in the paper, including UCC, ECC, and HCC where applicable.
3. Eliminate invalid causal chains according to the paper's rules.
4. Calculate the required probabilities.
5. Normalize probabilities where required.
6. Calculate posterior probabilities for the relevant hypotheses.
7. Reconstruct and rank candidate attack paths.
8. Select the most probable attack scenario according to the published method.

Read the mathematical definitions carefully before coding. Do not substitute ordinary shortest-path algorithms, generic Bayesian inference, or simple multiplication of edge weights for the paper's reasoning procedure.

### D. Transparent calculations

For every important calculation, show:

- Input values and evidence.
- Applicable equation from the paper.
- Substituted numerical values.
- Intermediate results.
- Normalization, when applicable.
- Final probability.
- Interpretation of the result.

Keep causal weights, prior probabilities, posterior probabilities, and attack-path probabilities distinct.

Do not hardcode expected final answers into the algorithm.

## 4. Paper experiments

Identify every experiment in the reference paper's experimental section and implement all of them.

For each experiment, reproduce the specified graph, parameter values, evidence, target, hypotheses, procedure, and reported metrics.

At least one required case is the paper's incomplete-alarm attack reconstruction scenario.

Use the reported path and evidence:

Path:
B1 → V1 → S2 → V3 → S4 → V6 → S6 → V11 → S8 → V13 → S9

Observed evidence:
{V1, V3, S4, V6, V11, V13, S9}

Missing alarm events:
S2, S6, S8

Target:
S9

Reconstruct the relevant candidate paths and posterior probabilities from the paper. Check the complete paper for the exact model parameters and expected outputs before implementing this case.

Also reproduce the other published experiments, including the risk-probability comparisons and runtime comparisons where applicable.

Do not replace a paper experiment with a new experiment just because it is easier to implement.

## 5. Results comparison

For every experiment, generate a comparison table containing:

- Experiment name.
- Metric or probability being compared.
- Published result.
- Our computed result.
- Numerical difference, when meaningful.
- Match status.
- Explanation of any discrepancy.

Reference the appropriate equation, table, or figure in the paper.

Do not fabricate missing published values.

If the implementation differs from the paper, investigate the cause and report the discrepancy honestly. Do not change calculations simply to force the expected result.

## 6. Demonstration interface

Create a simple local interface that makes the algorithm easy to demonstrate.

Include:

1. Project overview.
2. DUCAG graph visualization.
3. Evidence and hypothesis selection.
4. Graph simplification.
5. Step-by-step CCRP reasoning.
6. Causal-chain expansion and elimination.
7. Intermediate probability calculations.
8. Final posterior probabilities.
9. Candidate attack-path ranking.
10. Separate views for each paper experiment.
11. Published-versus-computed results comparison.

Use a straightforward layout with readable labels and tables. No elaborate UI, animations, authentication, deployment, or unrelated features are needed.

All results must come from the Python implementation rather than being separately hardcoded in the interface.

## 7. Fresh directory structure

Use a clear structure similar to:

DUCAG_CCRP_Fresh/
    PROJECT_SPEC.md
    README.md
    requirements.txt
    app.py
    src/
        __init__.py
        ducag_graph.py
        graph_simplification.py
        ccrp.py
        probability_calculations.py
        attack_path_analysis.py
    experiments/
        __init__.py
        paper_experiment_1.py
        paper_experiment_2.py
        paper_experiment_3.py
        paper_experiment_4.py
        paper_data.json
    tests/
        test_graph.py
        test_ccrp.py
        test_probabilities.py
        test_experiments.py
    results/
        graphs/
        tables/
        logs/
    docs/
        paper_algorithm_mapping.md
        implementation_report.md
        paper_comparison.md

Adapt the structure if necessary, but maintain separation between the algorithm, experiment inputs, tests, visualizations, and interface.

## 8. Testing and verification

Test graph construction, simplification, causal-chain expansion, invalid-chain elimination, probability calculations, normalization, attack-path ranking, and all experimental cases.

Run each experiment using a reproducible command.

Verify that the results are generated by the algorithm rather than by hardcoded expected values.

Provide commands to install dependencies, run tests, run individual experiments, and launch the interface.

## 9. Implementation stages

Stage 1: Read the paper and create a detailed algorithm and experiment mapping.

Stage 2: Implement and test graph construction.

Stage 3: Implement graph simplification and verify it against the paper.

Stage 4: Implement CCRP and verify each mathematical operation.

Stage 5: Reproduce every paper experiment.

Stage 6: Compare the computed results with the paper.

Stage 7: Build the simple demonstration interface.

Stage 8: Run final tests and document the results.

Complete and verify each stage before moving to the next.

## 10. Completion requirements

The final implementation must:

- Be written from scratch in the new project directory.
- Follow the paper's actual algorithm.
- Display the graph used in computation.
- Show the important intermediate reasoning and probability calculations.
- Reproduce all four paper experiments.
- Compare the computed results against published values.
- Explain any mismatches and limitations.
- Include tests, a README, and reproducible execution commands.
- Be simple enough for an undergraduate student to explain during a project review.

Start by studying the paper and producing an implementation plan. Do not generate the entire codebase immediately. First show the exact algorithm, equations, experimental cases, and data that need to be implemented. Wait for approval before proceeding to the first implementation stage.