# AbsorbBench-36

A fixed-task benchmark for evaluating autonomous agents on **microwave-absorber inverse design**. It contains 36 design tasks: 18 coated honeycomb sandwich tasks and 18 triply periodic minimal surface (TPMS) tasks.

This release provides task definitions and evaluation tools, **without AbsorbEvo's test results, optimized designs, trajectories, or baseline scores**. It is independent of a particular language model or agent architecture.

[Task index](tasks.csv) · [Evaluation protocol](docs/protocol.md) · [Geometry and simulation](docs/modeling.md) · [Integration guide](docs/integration.md)

## Dataset

| Split | Honeycomb | TPMS | Total | Intended use |
|---|---:|---:|---:|---|
| Development | 4 | 4 | 8 | Build and debug an agent |
| Validation | 2 | 2 | 4 | Choose settings before testing |
| Test | 12 | 12 | 24 | Evaluate a frozen agent |
| **All** | **18** | **18** | **36** | |

Every [task JSON](tasks/) includes the target frequency band, incidence angles, objective polarizations, reflection-loss threshold, required coverage, allowed design variables, fixed geometry, and a common initial design. All IDs begin with **AB36**. The historical core-task prefixes have been normalized; task settings and numeric suffixes have not been redesigned.

The standard budget is **five new design proposals per task**. Each proposal is evaluated at all required angles with both registered reflection modes; only the task's designated polarizations enter the objective. The common Initial is evaluated separately and is not a new proposal. The standard test split therefore contains 120 proposal opportunities for one agent.

## Quick start

Requires Python 3.10 or newer. The supplied tools use only the standard library.

```bash
git clone https://github.com/ZhichengFeng/AbsorbEvo.git
cd AbsorbEvo/benchmarks/AbsorbBench-36
python tools/absorbbench.py validate
python tools/absorbbench.py show AB36-HC-D01
python tools/absorbbench.py template AB36-HC-D01 --out evaluation.json
python tools/geometry.py AB36-HC-D01 --out geometry.json
python -m unittest discover -s tests -v
```

`evaluation.json` is an **unverified Initial template**, not a sample result. Run your own full-wave solver, export the required complex reflection spectra, and fill the evidence fields only after checking the solver logs. Then score the evaluation:

```bash
python tools/absorbbench.py score evaluation.json --out initial_score.json
```

Use a new evaluation file with `round_index` 1–5 and your agent's active parameters for each new proposal. See the [integration guide](docs/integration.md) for the complete input format and trajectory summary command.

## What is included

- `tasks/`, `tasks.csv`, `splits.json`: 36 frozen tasks and the 8/4/24 split.
- `materials.json`: honeycomb constituent properties and TPMS Debye materials M2–M8.
- `geometry/tpms_target_vf_map.csv`: 243 frozen geometry mappings (not performance measurements).
- `tools/geometry.py`: honeycomb polygon profiles and TPMS geometry-parameter resolution.
- `tools/absorbbench.py`: parameter validation, raw-spectrum scoring, and per-task first-success summaries.
- `docs/`: modeling, evaluation, and agent integration instructions.
- `tests/`: synthetic correctness checks; no experimental observations.
- `checksums.json`: SHA-256 hashes for task and physical-definition files.

## Solver boundary

This is a **task-and-evaluation release**, not a bundled electromagnetic solver or the private AbsorbEvo implementation. Supply a licensed full-wave solver and a geometry/solver adapter. The reference numerical profile uses CST Studio Suite 2025; its settings and portable geometry definitions are documented. Other solvers may be used, but report solver/mesh differences and establish numerical comparability before making direct performance comparisons.

The scorer checks the supplied spectra, task identity, and required runner attestations. It cannot independently certify that a solver was actually run or converged; preserve the underlying logs and raw files for audit. Missing or blocked simulations remain unresolved, rather than receiving an invented score.

## Use and attribution

The files in this benchmark directory are available under the [MIT License](LICENSE). That license does not extend to manuscript figures or other files elsewhere in the repository. When using the benchmark, cite **AbsorbBench-36 v1.0.0**, link this repository, and record the Git commit and task hashes. Please name modified task definitions as a separate benchmark variant. No unpublished manuscript DOI is implied.
