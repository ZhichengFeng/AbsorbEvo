# Connect your agent and solver

## Minimal agent interface

Load one JSON file from `tasks/`. Pass its prompt, objective, design space, Initial parameters and five-proposal budget to the agent. Have it return a JSON object containing **exactly the active parameter names** under `design_space.variables`. Fixed geometry is handled by the solver adapter and must not be changed.

```bash
python tools/absorbbench.py check-proposal AB36-HC-D01 proposal_parameters.json
python tools/geometry.py AB36-HC-D01 --parameters proposal_parameters.json --out geometry.json
```

For Initial geometry, omit `--parameters`. For TARGET_VF TPMS tasks, the helper resolves the frozen level and geometric volume fraction. For honeycomb it exports polygon profiles and layer coordinates. It does not compute performance.

Evaluate Initial once per task. For each new proposal, validate it, run all required angles, score it, and pass only the feedback allowed by your declared agent protocol into the next round. Keep model calls, scientific opportunities and physical retries in separate counters.

## Spectrum files

Export one UTF-8 CSV per design × incidence angle with these nine columns:

```text
frequency_GHz,R_TE_co_real,R_TE_co_imag,R_TE_cross_real,R_TE_cross_imag,R_TM_co_real,R_TM_co_imag,R_TM_cross_real,R_TM_cross_imag
```

TE/TM identify the incident mode; co/cross identify the reflected mode. Coefficients must be power-normalized. The scorer requires the task's full uniform 2–18 GHz grid, finite numbers and both polarization channels. Preserve complex signs even though the coverage calculation uses squared magnitudes.

## Evaluation receipt

Generate a template using:

```bash
python tools/absorbbench.py template AB36-HC-D01 --out evaluation.json
```

The template contains:

| Field | Meaning |
|---|---|
| `task_id`, `task_sha256` | Identity and byte hash of the public task file |
| `round_index` | 0 for Initial, 1–5 for new designs |
| `parameters` | Actual active parameters used in the simulation |
| `status` | `complete`, `invalid_proposal` or `infrastructure_failure` |
| `angle_results` | One record for every prescribed angle |
| `angle_results[].spectrum_csv` | Raw complex spectrum path, relative to the receipt |
| `angle_results[].solver_log` | Nonempty actual solver log path, relative to the receipt |
| `angle_results[].checks` | Confirmed convergence, complete export, unchanged task, fresh project |

All four check flags are initially false. Set them true only after verification against the actual run. This is a portable attestation interface; the scorer cannot discover an incorrect geometry or invented solver log on its own. Archive the model/project, solver version, mesh settings, logs and spectra with your evaluation evidence.

For a blocked solve or invalid scientific proposal, use the corresponding status and a nonempty `reason`; no fabricated spectrum is needed. The former remains unresolved; the latter consumes a proposal. Check the [protocol](protocol.md) before assigning a failure category.

```bash
python tools/absorbbench.py score evaluation.json --out score.json
```

## Summarize a complete agent run

Supply scorer-generated JSON files for exactly one agent/run and split. Include the Initial receipts to compute best coverage including Initial. Avoid mixing reruns: each task × round may appear only once.

```bash
python tools/absorbbench.py summarize --split test --out summary.json task1_round1.json task1_round2.json
```

The short command above demonstrates the interface and will report an incomplete split. Pass all 120 test proposal receipts (and optionally 24 Initial receipts) for the full report. Shell wildcard expansion differs by platform; pass explicit files or invoke `summarize(paths, 'test')` from Python with a list obtained using `pathlib.Path.glob`.

The report contains a first-success round for every task, cumulative counts for rounds 1–5 and unresolved round lists. Missing success is null. An incomplete split has a null headline task-success rate. A null first-success round is not an extra iteration and must not be included as a fabricated success time in an average.

## Reproducible reporting

Record benchmark version, Git commit, task hashes, solver and model versions, agent source/prompt, seeds, access to priors or training data, feedback policy, proposal budget, retries and total costs. Freeze the agent using only development/validation tasks before testing. If you change any task condition or the endpoint coverage rule, identify your experiment as a separate variant.
